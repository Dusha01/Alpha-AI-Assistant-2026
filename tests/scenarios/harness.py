from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from itertools import count
from typing import Any
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.methods import (
    AnswerCallbackQuery,
    DeleteMessage,
    EditMessageText,
    SendChatAction,
    SendMessage,
    TelegramMethod,
)
from aiogram.methods.base import TelegramType
from aiogram.types import CallbackQuery, Chat, Message, Sticker, Update, User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.settings import Settings
from src.data.models import Reminder, TaxDeadline
from src.data.models import User as DbUser
from src.data.models.enums import TaxMode
from src.data.repositories.dialog_states import DialogStateRepository
from src.data.repositories.profiles import ProfileRepository
from src.data.repositories.reminders import ReminderRepository
from src.data.repositories.users import UserRepository
from src.handlers.errors import on_handler_error
from src.handlers.handlers import build_router
from src.handlers.text import COPY
from src.modules.knowledge.service import BotReply
from src.modules.profile.service import ProfileService
from src.modules.recommend.service import RecommendService
from src.modules.reminders.poller import _tick
from src.modules.reminders.service import ReminderService

_TELEGRAM_IDS = count(910_000_001)
_TOKEN = "123456789:AAH-scenario-test"
_TZ = ZoneInfo("Asia/Vladivostok")
NEUTRAL_QUESTION = "Добрый день"


class ScriptedKnowledge:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []
        self.default = BotReply(COPY["not_found"])
        self._replies: dict[str, BotReply] = {}
        self.fail: set[str] = set()

    def reply(self, question: str, result: BotReply) -> None:
        self._replies[question] = result

    async def answer_question(
        self,
        question: str,
        *,
        search_query: str | None = None,
        profile: object | None = None,
        on_sources: object | None = None,
    ) -> BotReply:
        self.calls.append((question, search_query))
        if question in self.fail:
            raise RuntimeError(question)
        return self._replies.get(question, self.default)


@dataclass(frozen=True, slots=True)
class OutgoingMessage:
    text: str
    buttons: tuple[tuple[str, str], ...]


@dataclass
class Turn:
    messages: list[OutgoingMessage] = field(default_factory=list)
    alerts: list[str | None] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(item.text for item in self.messages)

    def callbacks(self) -> tuple[str, ...]:
        return tuple(data for item in self.messages for _, data in item.buttons)


class RecordingSession(BaseSession):
    def __init__(self) -> None:
        super().__init__()
        self.fail_sends = 0
        self._events: list[tuple[str, OutgoingMessage | str | None]] = []
        self._ids: list[int | None] = []
        self._cursor = 0
        self._message_id = 1000

    async def close(self) -> None:
        return None

    async def stream_content(self, *args: Any, **kwargs: Any) -> Any:
        if False:
            yield b""

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[TelegramType],
        timeout: int | None = None,
    ) -> TelegramType:
        if isinstance(method, SendMessage):
            if self.fail_sends:
                self.fail_sends -= 1
                raise RuntimeError("telegram down")
            buttons: list[tuple[str, str]] = []
            markup = method.reply_markup
            if markup is not None and hasattr(markup, "inline_keyboard"):
                for row in markup.inline_keyboard:
                    for button in row:
                        buttons.append((button.text, button.callback_data or ""))
            outgoing = OutgoingMessage(method.text, tuple(buttons))
            self._message_id += 1
            self._events.append(("message", outgoing))
            self._ids.append(self._message_id)
            chat_id = int(method.chat_id) if isinstance(method.chat_id, str) else method.chat_id
            return Message(
                message_id=self._message_id,
                date=datetime.now(UTC),
                chat=Chat(id=chat_id, type="private"),
                text=method.text,
            ).as_(bot)
        if isinstance(method, EditMessageText):
            self._replace(method.message_id, method.text)
            return True
        if isinstance(method, SendChatAction):
            return True
        if isinstance(method, DeleteMessage):
            self._drop(method.message_id)
            return True
        if isinstance(method, AnswerCallbackQuery):
            self._events.append(("alert", method.text))
            self._ids.append(None)
            return True
        raise AssertionError(f"unexpected method {type(method).__name__}")

    def _replace(self, message_id: int, text: str) -> None:
        try:
            index = self._ids.index(message_id)
        except ValueError:
            return
        kind, payload = self._events[index]
        if kind == "message" and isinstance(payload, OutgoingMessage):
            self._events[index] = ("message", OutgoingMessage(text, payload.buttons))

    def _drop(self, message_id: int) -> None:
        try:
            index = self._ids.index(message_id)
        except ValueError:
            return
        del self._events[index]
        del self._ids[index]
        if index < self._cursor:
            self._cursor -= 1

    def drain(self) -> Turn:
        fresh = self._events[self._cursor :]
        self._cursor = len(self._events)
        turn = Turn()
        for kind, payload in fresh:
            if kind == "message":
                assert isinstance(payload, OutgoingMessage)
                turn.messages.append(payload)
            else:
                turn.alerts.append(payload if isinstance(payload, str) or payload is None else None)
        return turn


def scenario_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "telegram_bot_token": _TOKEN,
        "message_max_length": 1000,
        "platform_base_url": "https://example.alfacourse.local",
        "reminder_timezone": "Asia/Vladivostok",
        "debug": False,
        "database_url": "postgresql+asyncpg://scenario/unused",
        "database_url_host": "",
    }
    values.update(overrides)
    return Settings(**values)


class Dialog:
    def __init__(
        self,
        *,
        telegram_id: int,
        session_factory: Any,
        db: AsyncSession,
        settings: Settings,
        knowledge: ScriptedKnowledge,
        username: str | None = "scenario",
    ) -> None:
        self.telegram_id = telegram_id
        self.username = username
        self.db = db
        self.knowledge = knowledge
        self.session_factory = session_factory
        self.settings = settings
        self.recording = RecordingSession()
        self.bot = Bot(token=_TOKEN, session=self.recording)
        self.profile = ProfileService(session_factory)
        self.recommend = RecommendService(settings=settings, session_factory=session_factory)
        self.reminders = ReminderService(settings=settings, session_factory=session_factory)
        self.dispatcher = Dispatcher()
        self.dispatcher.include_router(
            build_router(
                settings,
                knowledge,  # type: ignore[arg-type]
                self.profile,
                self.recommend,
                self.reminders,
            )
        )
        self.dispatcher.errors.register(on_handler_error)
        self._update_id = count(1)
        self._incoming_id = count(1)
        self._callback_id = count(1)

    def _next_update(self) -> int:
        return next(self._update_id)

    def _user(self) -> User:
        return User(
            id=self.telegram_id,
            is_bot=False,
            first_name="Scenario",
            username=self.username,
        )

    def _incoming(self, *, text: str | None, sticker: Sticker | None = None) -> Message:
        return Message(
            message_id=next(self._incoming_id),
            date=datetime.now(UTC),
            chat=Chat(id=self.telegram_id, type="private"),
            from_user=self._user(),
            text=text,
            sticker=sticker,
        )

    def _bind(self, update: Update) -> Update:
        update.as_(self.bot)
        if update.message is not None:
            update.message.as_(self.bot)
        query = update.callback_query
        if query is not None:
            query.as_(self.bot)
            message = query.message
            if message is not None and hasattr(message, "as_"):
                message.as_(self.bot)
        return update

    async def say(self, text: str) -> Turn:
        update = Update(update_id=self._next_update(), message=self._incoming(text=text))
        await self.dispatcher.feed_update(self.bot, self._bind(update))
        return self.recording.drain()

    async def send_sticker(self) -> Turn:
        sticker = Sticker(
            file_id="sticker-file",
            file_unique_id="sticker-unique",
            type="regular",
            width=64,
            height=64,
            is_animated=False,
            is_video=False,
        )
        update = Update(
            update_id=self._next_update(),
            message=self._incoming(text=None, sticker=sticker),
        )
        await self.dispatcher.feed_update(self.bot, self._bind(update))
        return self.recording.drain()

    async def press(
        self,
        data: str,
        *,
        with_message: bool = True,
        with_user: bool = True,
    ) -> Turn:
        message = self._incoming(text="кнопка") if with_message else None
        if with_user:
            query = CallbackQuery(
                id=str(next(self._callback_id)),
                from_user=self._user(),
                chat_instance="scenario",
                data=data,
                message=message,
            )
            update = Update(update_id=self._next_update(), callback_query=query)
        else:
            query = CallbackQuery.model_construct(
                id=str(next(self._callback_id)),
                from_user=None,
                chat_instance="scenario",
                data=data,
                message=message,
            )
            update = Update.model_construct(
                update_id=self._next_update(),
                callback_query=query,
            )
        await self.dispatcher.feed_update(self.bot, self._bind(update))
        return self.recording.drain()

    async def db_user(self) -> DbUser | None:
        return await UserRepository(self.db).get_by_telegram_id(self.telegram_id)

    async def require_user(self) -> DbUser:
        user = await self.db_user()
        assert user is not None
        return user

    async def dialog_state(self) -> str | None:
        user = await self.db_user()
        if user is None:
            return None
        row = await DialogStateRepository(self.db).get_by_user_id(user.id)
        if row is None:
            return None
        await self.db.refresh(row)
        return row.state

    async def payload(self) -> dict[str, object]:
        user = await self.require_user()
        row = await DialogStateRepository(self.db).get_by_user_id(user.id)
        assert row is not None
        await self.db.refresh(row)
        return dict(row.payload)

    async def profile_row(self):
        user = await self.require_user()
        profile = await ProfileRepository(self.db).get_by_user_id(user.id)
        if profile is not None:
            await self.db.refresh(profile)
        return profile

    async def reminder(self, reminder_id: object) -> Reminder:
        row = await ReminderRepository(self.db).get_by_id(reminder_id)  # type: ignore[arg-type]
        assert row is not None
        await self.db.refresh(row)
        return row

    async def reminder_rows(self, *, include_done: bool = False) -> list[Reminder]:
        user = await self.require_user()
        if include_done:
            result = await self.db.scalars(select(Reminder).where(Reminder.user_id == user.id))
            rows = list(result)
        else:
            rows = await ReminderRepository(self.db).list_for_user(user.id)
        for row in rows:
            await self.db.refresh(row)
        return rows

    async def add_tax_deadline(
        self,
        *,
        mode: TaxMode = TaxMode.USN,
        what: str = "авансовый платёж по УСН за тест",
        due: datetime | None = None,
        lead_days: int = 14,
        title: str = "Налоговый шаблон",
        slug: str = "tax-template",
    ) -> TaxDeadline:
        due_date = (due or datetime(2026, 12, 20, tzinfo=UTC)).date()
        row = TaxDeadline(
            mode=mode,
            what_to_pay=what,
            due_date=due_date,
            lead_days=lead_days,
            source_note="тестовый справочник",
            material_title=title,
            material_slug=slug,
        )
        self.db.add(row)
        await self.db.commit()
        return row

    async def tick(self) -> Turn:
        await _tick(self.bot, self.session_factory, self.reminders)
        return self.recording.drain()


def open_dialog(
    *,
    session_factory: Any,
    db: AsyncSession,
    telegram_id: int | None = None,
    settings: Settings | None = None,
    knowledge: ScriptedKnowledge | None = None,
    max_length: int | None = None,
    username: str | None = "scenario",
) -> Dialog:
    if settings is None:
        overrides: dict[str, Any] = {}
        if max_length is not None:
            overrides["message_max_length"] = max_length
        settings = scenario_settings(**overrides)
    elif max_length is not None:
        settings = scenario_settings(message_max_length=max_length)
    return Dialog(
        telegram_id=telegram_id if telegram_id is not None else next(_TELEGRAM_IDS),
        session_factory=session_factory,
        db=db,
        settings=settings,
        knowledge=knowledge or ScriptedKnowledge(),
        username=username,
    )


def freeze_poller(monkeypatch: Any, moment: datetime) -> None:
    class _Clock:
        @staticmethod
        def now(tz: Any = None) -> datetime:
            return moment

    monkeypatch.setattr("src.modules.reminders.poller.datetime", _Clock)


def local_when(moment: datetime) -> datetime:
    return moment.astimezone(_TZ)


async def begin_profile(dialog: Dialog, question: str = NEUTRAL_QUESTION) -> Turn:
    dialog.knowledge.reply(
        question,
        BotReply("На связи.", feedback=True, material_title="Старт"),
    )
    return await dialog.say(question)


async def finish_profile(
    dialog: Dialog,
    business: str,
    mode_callback: str,
    *,
    question: str = NEUTRAL_QUESTION,
) -> Turn:
    await begin_profile(dialog, question)
    await dialog.say(business)
    return await dialog.press(mode_callback)


async def complete_custom(
    dialog: Dialog,
    about: str,
    when: str,
    repeat: str = "reminder_repeat:once",
) -> Turn:
    await dialog.press("remind")
    await dialog.say(about)
    await dialog.say(when)
    await dialog.press(repeat)
    return await dialog.press("reminder_confirm:yes")


def shift(moment: datetime, **kwargs: float) -> datetime:
    return moment + timedelta(**kwargs)


def iter_buttons(turn: Turn) -> Iterator[tuple[str, str]]:
    for item in turn.messages:
        yield from item.buttons
