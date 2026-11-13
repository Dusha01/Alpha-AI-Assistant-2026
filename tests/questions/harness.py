from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from itertools import count
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.methods import (
    AnswerCallbackQuery,
    DeleteMessage,
    SendChatAction,
    SendMessage,
    TelegramMethod,
)
from aiogram.methods.base import TelegramType
from aiogram.types import CallbackQuery, Chat, Message, Sticker, Update, User
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.settings import Settings
from src.data.models import TaxDeadline
from src.data.models.enums import BusinessStage, TaxMode
from src.data.repositories.profiles import ProfileRepository
from src.handlers.errors import on_handler_error
from src.handlers.handlers import build_router
from src.modules.knowledge.embedder import Embedder, LazySentenceTransformerEmbedder
from src.modules.knowledge.llm import LlmClient, OpenAICompatibleLlm
from src.modules.knowledge.service import KnowledgeService
from src.modules.profile.service import ProfileService
from src.modules.recommend.service import RecommendService
from src.modules.reminders.service import ReminderService

_TELEGRAM_IDS = count(920_000_001)
_TOKEN = "123456789:AAH-question-test"
_EMBEDDER: Embedder | None = None


class CountingLlm:
    def __init__(self, inner: LlmClient) -> None:
        self.inner = inner
        self.calls = 0
        self.last_messages: list[dict[str, str]] | None = None

    async def complete(self, messages: list[dict[str, str]]) -> str:
        self.calls += 1
        self.last_messages = messages
        return await self.inner.complete(messages)


def shared_embedder(model_name: str) -> Embedder:
    global _EMBEDDER
    if _EMBEDDER is None:
        _EMBEDDER = LazySentenceTransformerEmbedder(model_name)
    return _EMBEDDER


@dataclass(frozen=True, slots=True)
class OutgoingMessage:
    text: str
    buttons: tuple[tuple[str, str], ...]


@dataclass
class Turn:
    messages: list[OutgoingMessage] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(item.text for item in self.messages)


class RecordingSession(BaseSession):
    def __init__(self) -> None:
        super().__init__()
        self._events: list[OutgoingMessage] = []
        self._ids: list[int] = []
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
            buttons: list[tuple[str, str]] = []
            markup = method.reply_markup
            if markup is not None and hasattr(markup, "inline_keyboard"):
                for row in markup.inline_keyboard:
                    for button in row:
                        buttons.append((button.text, button.callback_data or ""))
            self._message_id += 1
            self._events.append(OutgoingMessage(method.text, tuple(buttons)))
            self._ids.append(self._message_id)
            chat_id = int(method.chat_id) if isinstance(method.chat_id, str) else method.chat_id
            return Message(
                message_id=self._message_id,
                date=datetime.now(UTC),
                chat=Chat(id=chat_id, type="private"),
                text=method.text,
            ).as_(bot)
        if isinstance(method, SendChatAction):
            return True
        if isinstance(method, DeleteMessage):
            self._drop(method.message_id)
            return True
        if isinstance(method, AnswerCallbackQuery):
            return True
        raise AssertionError(f"unexpected method {type(method).__name__}")

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
        return Turn(messages=list(fresh))


def question_settings(base: Settings) -> Settings:
    return Settings(
        _env_file=None,  # type: ignore[arg-type]
        telegram_bot_token=_TOKEN,
        message_max_length=base.message_max_length,
        platform_base_url=base.platform_base_url or "https://example.alfacourse.local",
        reminder_timezone=base.reminder_timezone,
        debug=False,
        database_url="postgresql+asyncpg://questions/unused",
        embedding_model=base.embedding_model,
        rag_top_k=base.rag_top_k,
        rag_score_threshold=base.rag_score_threshold,
        rag_related_score_threshold=base.rag_related_score_threshold,
        rag_clarify_score_gap=base.rag_clarify_score_gap,
        llm_base_url=base.llm_base_url,
        llm_api_key=base.llm_api_key,
        llm_model=base.llm_model,
        llm_fallback_model=base.llm_fallback_model,
        llm_timeout_seconds=base.llm_timeout_seconds,
    )


class QuestionDialog:
    def __init__(self, *, session_factory: Any, db: AsyncSession, settings: Settings) -> None:
        self.telegram_id = next(_TELEGRAM_IDS)
        self.db = db
        self.settings = settings
        self.session_factory = session_factory
        self.recording = RecordingSession()
        self.bot = Bot(token=_TOKEN, session=self.recording)
        self.llm = CountingLlm(
            OpenAICompatibleLlm(
                base_url=settings.llm_base_url,
                api_key=settings.llm_api_key,
                model=settings.llm_model,
                fallback_model=settings.llm_fallback_model,
                timeout_seconds=settings.llm_timeout_seconds,
            )
        )
        self.knowledge = KnowledgeService(
            settings=settings,
            session_factory=session_factory,
            embedder=shared_embedder(settings.embedding_model),
            llm=self.llm,
        )
        self.profile = ProfileService(session_factory)
        self.recommend = RecommendService(settings=settings, session_factory=session_factory)
        self.reminders = ReminderService(settings=settings, session_factory=session_factory)
        self.dispatcher = Dispatcher()
        self.dispatcher.include_router(
            build_router(
                settings,
                self.knowledge,
                self.profile,
                self.recommend,
                self.reminders,
            )
        )
        self.dispatcher.errors.register(on_handler_error)
        self._update_id = count(1)
        self._incoming_id = count(1)
        self._callback_id = count(1)

    def llm_ready(self) -> bool:
        return bool(
            self.settings.llm_api_key.strip()
            and self.settings.llm_base_url.strip()
            and self.settings.llm_model.strip()
        )

    def _user(self) -> User:
        return User(id=self.telegram_id, is_bot=False, first_name="Вопрос", username="questions")

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
        update = Update(update_id=next(self._update_id), message=self._incoming(text=text))
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
            update_id=next(self._update_id),
            message=self._incoming(text=None, sticker=sticker),
        )
        await self.dispatcher.feed_update(self.bot, self._bind(update))
        return self.recording.drain()

    async def press(self, data: str) -> Turn:
        query = CallbackQuery(
            id=str(next(self._callback_id)),
            from_user=self._user(),
            chat_instance="questions",
            data=data,
            message=self._incoming(text="кнопка"),
        )
        update = Update(update_id=next(self._update_id), callback_query=query)
        await self.dispatcher.feed_update(self.bot, self._bind(update))
        return self.recording.drain()

    async def prepare(self, hero: str) -> None:
        if hero in {"ivan", "any", "empty"}:
            await self.profile.ensure_user(self.telegram_id, "questions")
            return
        user = await self.profile.ensure_user(self.telegram_id, "questions")
        values: dict[str, object] = {}
        if hero == "ivan_plan":
            values = {"stage": BusinessStage.PLANNING}
        elif hero == "anna":
            values = {
                "sphere": "кофейня",
                "stage": BusinessStage.LT_YEAR,
                "mode": TaxMode.USN,
            }
        elif hero == "alexander":
            values = {
                "sphere": "магазин автозапчастей",
                "stage": BusinessStage.GT_YEAR,
                "mode": TaxMode.USN,
            }
        elif hero == "alexander_patent":
            values = {
                "sphere": "магазин автозапчастей",
                "stage": BusinessStage.GT_YEAR,
                "mode": TaxMode.PATENT,
            }
        elif hero == "ivan_npd":
            values = {"sphere": "услуги", "stage": BusinessStage.PLANNING, "mode": TaxMode.NPD}
        if values:
            async with self.session_factory() as session:
                await ProfileRepository(session).upsert(user.id, **values)
                await session.commit()

    async def add_usn_deadline(self) -> None:
        self.db.add(
            TaxDeadline(
                mode=TaxMode.USN,
                what_to_pay="авансовый платёж по УСН за тест",
                due_date=datetime(2026, 12, 20, tzinfo=UTC).date(),
                lead_days=14,
                source_note="тестовый справочник",
                material_title="Налоговый шаблон",
                material_slug="tax-template",
            )
        )
        await self.db.commit()
