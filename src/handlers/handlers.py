# Слой контракта. Хендлеры делегируют разбор входящего сообщения и не содержат правил.

import asyncio
import contextlib
import re
import uuid

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger

from src.core.settings import Settings
from src.handlers.incoming import RESET_DIALOG_KEYS, reply_key
from src.handlers.telegram_text import split_telegram_text
from src.handlers.text import COPY, FEEDBACK_BUTTONS, START_BUTTONS, found_articles_status
from src.modules.knowledge.follow_up import queries_for_turn
from src.modules.knowledge.llm import LlmNotConfiguredError, LlmRequestError
from src.modules.knowledge.service import BotReply, KnowledgeService
from src.modules.profile.parse import mode_switch, parse_business_line
from src.modules.profile.service import ProfileService
from src.modules.recommend.service import RecommendReply, RecommendService
from src.modules.reminders.keyboards import REPEAT_BUTTONS
from src.modules.reminders.service import ReminderService

_BUTTON_ACTIONS = ("ask", "materials", "remind")
_TYPING_REFRESH_SECONDS = 4.0
_SLOW_AFTER_SECONDS = 15.0
_READING_INTENT = re.compile(
    r"(?:что(?:\s+мне)?\s+(?:почитать|посмотреть)|с чего начать)",
    re.IGNORECASE,
)


def log_handler(
    kind: str,
    chat_id: int | None,
    *,
    debug: bool,
    text: str | None = None,
) -> None:
    logger.info("handler={} chat_id={}", kind, chat_id)
    if debug and text:
        logger.debug("text={}", text[:200])


def feedback_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=label, callback_data=data)
                for label, data in FEEDBACK_BUTTONS
            ]
        ]
    )


async def deliver_recommendations(
    message: Message,
    user_id: uuid.UUID,
    recommend: RecommendService | None,
    *,
    prefer_route: bool = False,
) -> None:
    if recommend is None:
        return
    pack: RecommendReply = await recommend.recommend_for_user(user_id, prefer_route=prefer_route)
    for text in pack.messages:
        await message.answer(text)
    if pack.next_step:
        await message.answer(pack.next_step)


def start_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=action)]
        for label, action in zip(START_BUTTONS, _BUTTON_ACTIONS, strict=True)
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


class _Thinking:
    def __init__(self, placeholder: Message, stop: asyncio.Event) -> None:
        self.placeholder = placeholder
        self.stop = stop
        self.task: asyncio.Task[None] | None = None
        self.closed = False
        self._lock = asyncio.Lock()
        self._stage_started = asyncio.get_running_loop().time()
        self._slow_shown = False

    async def show(self, text: str) -> None:
        """Новая стадия. Срок «ещё пара секунд» считается заново."""
        async with self._lock:
            if self.closed:
                return
            self._stage_started = asyncio.get_running_loop().time()
            self._slow_shown = False
            try:
                await self.placeholder.edit_text(text)
            except Exception as exc:
                logger.warning("Не удалось обновить статус: {}", exc)

    def seconds_until_slow(self, now: float) -> float | None:
        if self.closed or self._slow_shown:
            return None
        return max(0.0, self._stage_started + _SLOW_AFTER_SECONDS - now)

    async def maybe_slow(self, now: float) -> None:
        async with self._lock:
            if self.closed or self._slow_shown:
                return
            if now - self._stage_started < _SLOW_AFTER_SECONDS:
                return
            self._slow_shown = True
            try:
                await self.placeholder.edit_text(COPY["thinking_slow"])
            except Exception as exc:
                logger.warning("Не удалось показать, что ответ задерживается: {}", exc)

    async def finish(self) -> None:
        self.stop.set()
        async with self._lock:
            if self.closed:
                return
            self.closed = True
        if self.task is not None and not self.task.done():
            self.task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.task

    async def replace(self, text: str) -> bool:
        """Подменяет статус ответом. Если правка не вышла, сообщение удаляется."""
        self.stop.set()
        async with self._lock:
            self.closed = True
            try:
                await self.placeholder.edit_text(text)
                edited = True
            except Exception as exc:
                logger.warning("Не удалось заменить статус ответом: {}", exc)
                edited = False
        if self.task is not None and not self.task.done():
            self.task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.task
        if edited:
            return True
        with contextlib.suppress(Exception):
            await self.placeholder.delete()
        return False


async def _watch_status(message: Message, thinking: _Thinking, stop: asyncio.Event) -> None:
    bot = message.bot
    if bot is None:
        return
    loop = asyncio.get_running_loop()
    next_typing = loop.time() + _TYPING_REFRESH_SECONDS
    while not stop.is_set():
        now = loop.time()
        deadline = next_typing
        until_slow = thinking.seconds_until_slow(now)
        if until_slow is not None:
            deadline = min(deadline, now + until_slow)
        timeout = deadline - now
        if timeout > 0:
            try:
                await asyncio.wait_for(stop.wait(), timeout=timeout)
                return
            except TimeoutError:
                pass
        if stop.is_set():
            return
        now = loop.time()
        await thinking.maybe_slow(now)
        if now >= next_typing:
            next_typing = now + _TYPING_REFRESH_SECONDS
            try:
                await bot.send_chat_action(message.chat.id, action=ChatAction.TYPING)
            except Exception:
                return


async def _begin_thinking(message: Message) -> _Thinking | None:
    if message.bot is None:
        return None
    try:
        await message.bot.send_chat_action(message.chat.id, action=ChatAction.TYPING)
        placeholder = await message.answer(COPY["thinking_search"])
    except Exception as exc:
        logger.warning("Не удалось показать, что бот печатает: {}", exc)
        return None
    stop = asyncio.Event()
    thinking = _Thinking(placeholder, stop)
    thinking.task = asyncio.create_task(_watch_status(message, thinking, stop))
    return thinking


async def deliver_knowledge(
    message: Message,
    knowledge: KnowledgeService,
    profile: ProfileService | None,
    recommend: RecommendService | None,
    user_id: uuid.UUID | None,
) -> None:
    thinking = await _begin_thinking(message)
    sent = False
    try:
        previous_question = None
        previous_material = None
        snapshot = None
        if profile is not None and user_id is not None:
            previous_question, previous_material = await profile.follow_up_context(user_id)
            snapshot = await profile.knowledge_snapshot(user_id)
        question, search_query = queries_for_turn(
            (message.text or "").strip(),
            previous_question=previous_question,
            previous_material=previous_material,
        )

        async def _note_sources(count: int) -> None:
            if thinking is not None and count > 0:
                await thinking.show(found_articles_status(count))

        reply: BotReply = await knowledge.answer_question(
            question,
            search_query=search_query,
            profile=snapshot,
            on_sources=_note_sources,
        )
        parts = split_telegram_text(reply.text)
        if thinking is not None and parts:
            if await thinking.replace(parts[0]):
                parts = parts[1:]
                sent = True
            else:
                await thinking.finish()
        for part in parts:
            await message.answer(part)
            sent = True
        if reply.material_title and profile is not None and user_id is not None:
            await profile.remember_follow_up(user_id, question, reply.material_title)
        if not reply.feedback:
            return
        if recommend is not None and user_id is not None:
            await recommend.remember_topic(user_id, question)
        await message.answer(COPY["feedback"], reply_markup=feedback_keyboard())
        if (
            profile is not None
            and user_id is not None
            and await profile.should_offer_business_prompt(user_id)
        ):
            follow = await profile.start_business_prompt(user_id)
            await message.answer(follow.text, reply_markup=follow.markup)
    except Exception as exc:
        logger.exception("Не удалось ответить на вопрос")
        if sent:
            if thinking is not None:
                await thinking.finish()
            return
        key = (
            "error_llm"
            if isinstance(exc, (LlmRequestError, LlmNotConfiguredError))
            else "error_general"
        )
        text = COPY[key]
        if thinking is not None and await thinking.replace(text):
            return
        if thinking is not None:
            await thinking.finish()
        await message.answer(text)
    finally:
        if thinking is not None:
            await thinking.finish()


def build_router(
    settings: Settings,
    knowledge: KnowledgeService | None = None,
    profile: ProfileService | None = None,
    recommend: RecommendService | None = None,
    reminders: ReminderService | None = None,
) -> Router:
    router = Router()

    @router.message(F.text)
    async def on_text(message: Message) -> None:
        key = reply_key(
            message.text,
            is_text=True,
            max_length=settings.message_max_length,
        )
        log_handler(key, message.chat.id, debug=settings.debug, text=message.text)
        user = None
        if profile is not None and message.from_user is not None:
            user = await profile.ensure_user(message.from_user.id, message.from_user.username)
            if key in RESET_DIALOG_KEYS:
                await profile.reset_dialog(user.id)
        if key == "cancel":
            await message.answer(COPY["cancel"], reply_markup=start_keyboard())
            return
        if key == "reminders" and reminders is not None and user is not None:
            reply = await reminders.list_reminders(user.id)
            await message.answer(reply.text, reply_markup=reply.markup)
            return
        if profile is not None and user is not None:
            if key == "profile":
                reply = await profile.show_profile(user.id)
                await message.answer(reply.text, reply_markup=reply.markup)
                return
            if reminders is not None and await reminders.is_in_dialog(user.id):
                reply = await reminders.handle_text(user.id, (message.text or "").strip())
                if reply is not None:
                    await message.answer(reply.text, reply_markup=reply.markup)
                    return
            if await profile.is_in_dialog(user.id):
                reply = await profile.handle_text(user, (message.text or "").strip())
                if reply is not None:
                    await message.answer(reply.text, reply_markup=reply.markup)
                    if recommend is not None and not await profile.is_in_dialog(user.id):
                        await deliver_recommendations(message, user.id, recommend)
                    return
        if (
            key == "smalltalk"
            and reminders is not None
            and profile is not None
            and message.from_user
            and reminders.is_reminder_intent((message.text or "").strip())
        ):
            user = await profile.ensure_user(message.from_user.id, message.from_user.username)
            reply = await reminders.start_quick(user.id, (message.text or "").strip())
            await message.answer(reply.text, reply_markup=reply.markup)
            return
        if key == "smalltalk" and profile is not None and user is not None:
            switched = mode_switch(message.text or "")
            if switched is not None:
                reply = await profile.remember_mode(user.id, switched)
                await message.answer(reply.text, reply_markup=reply.markup)
                return
            parsed = parse_business_line(message.text or "")
            snapshot = await profile.knowledge_snapshot(user.id)
            if parsed.sphere and parsed.stage is not None and not (snapshot.sphere or "").strip():
                reply = await profile.accept_business_line(user.id, (message.text or "").strip())
                await message.answer(reply.text, reply_markup=reply.markup)
                if recommend is not None and not await profile.is_in_dialog(user.id):
                    await deliver_recommendations(message, user.id, recommend)
                return
        if (
            key == "smalltalk"
            and recommend is not None
            and profile is not None
            and user is not None
            and _READING_INTENT.search(message.text or "")
        ):
            await deliver_recommendations(message, user.id, recommend, prefer_route=True)
            return
        if (
            key == "smalltalk"
            and knowledge is not None
            and profile is not None
            and message.from_user
            and user is not None
        ):
            await deliver_knowledge(message, knowledge, profile, recommend, user.id)
            return
        if key == "smalltalk" and knowledge is not None:
            await deliver_knowledge(message, knowledge, profile, recommend, None)
            return
        markup = start_keyboard() if key == "start" else None
        await message.answer(COPY[key], reply_markup=markup)

    @router.message()
    async def on_non_text(message: Message) -> None:
        log_handler("non_text", message.chat.id, debug=settings.debug)
        await message.answer(COPY["non_text"])

    @router.callback_query(F.data == "feedback_yes")
    async def on_feedback_yes(query: CallbackQuery) -> None:
        chat_id = query.message.chat.id if query.message is not None else None
        log_handler("feedback_yes", chat_id, debug=settings.debug)
        await query.answer("Спасибо за отзыв!")

    @router.callback_query(F.data == "feedback_no")
    async def on_feedback_no(query: CallbackQuery) -> None:
        chat_id = query.message.chat.id if query.message is not None else None
        log_handler("feedback_no", chat_id, debug=settings.debug)
        await query.answer()
        if query.message is not None:
            await query.message.answer(COPY["feedback_no"])

    @router.callback_query(F.data.startswith(("reminder_", "tax_remind:", "remind_")))
    async def on_reminder_button(query: CallbackQuery) -> None:
        if reminders is None or query.from_user is None or query.data is None:
            await query.answer()
            return
        user = await reminders.ensure_user(query.from_user.id, query.from_user.username)
        log_handler(
            "reminder_callback",
            query.message.chat.id if query.message else None,
            debug=settings.debug,
            text=query.data,
        )
        if query.data.startswith("remind_edit:"):
            from uuid import UUID

            rid = UUID(query.data.removeprefix("remind_edit:"))
            await query.answer()
            if query.message is not None:
                rows = [
                    [
                        InlineKeyboardButton(
                            text=label,
                            callback_data=f"reminder_repeat_set:{rid}:{data.split(':')[-1]}",
                        )
                    ]
                    for label, data in REPEAT_BUTTONS
                ]
                markup = InlineKeyboardMarkup(inline_keyboard=rows)
                await query.message.answer(COPY["reminder_ask_repeat"], reply_markup=markup)
            return
        reply = await reminders.handle_callback(user.id, query.data)
        await query.answer()
        if reply is not None and query.message is not None:
            await query.message.answer(reply.text, reply_markup=reply.markup)

    @router.callback_query(F.data.startswith("profile_"))
    async def on_profile_button(query: CallbackQuery) -> None:
        if profile is None or query.from_user is None or query.data is None:
            await query.answer()
            return
        user = await profile.ensure_user(query.from_user.id, query.from_user.username)
        log_handler(
            "profile_callback",
            query.message.chat.id if query.message else None,
            debug=settings.debug,
            text=query.data,
        )
        reply = await profile.handle_callback(user, query.data)
        await query.answer()
        if reply is not None and query.message is not None:
            await query.message.answer(reply.text, reply_markup=reply.markup)
            if (
                recommend is not None
                and profile is not None
                and query.data
                and (query.data.startswith("profile_mode:") or query.data == "profile_skip")
                and not await profile.is_in_dialog(user.id)
            ):
                await deliver_recommendations(query.message, user.id, recommend)
            if (
                reminders is not None
                and query.data is not None
                and query.data.startswith("profile_mode:")
            ):
                tax_follow = await reminders.continue_tax_offer(user.id)
                if tax_follow is not None and query.message is not None:
                    await query.message.answer(tax_follow.text, reply_markup=tax_follow.markup)

    @router.callback_query()
    async def on_button(query: CallbackQuery) -> None:
        chat_id = query.message.chat.id if query.message is not None else None
        log_handler("callback", chat_id, debug=settings.debug, text=query.data)
        await query.answer()
        if query.data in _BUTTON_ACTIONS and profile is not None and query.from_user is not None:
            user = await profile.ensure_user(query.from_user.id, query.from_user.username)
            await profile.reset_dialog(user.id)
        if query.data == "ask" and query.message is not None:
            await query.message.answer(COPY["smalltalk"])
            return
        if (
            query.data == "materials"
            and recommend is not None
            and profile is not None
            and query.from_user is not None
            and query.message is not None
        ):
            user = await profile.ensure_user(query.from_user.id, query.from_user.username)
            await deliver_recommendations(query.message, user.id, recommend, prefer_route=True)
        if (
            query.data == "remind"
            and reminders is not None
            and profile is not None
            and query.from_user is not None
            and query.message is not None
        ):
            user = await profile.ensure_user(query.from_user.id, query.from_user.username)
            reply = await reminders.start_custom_flow(user.id)
            await query.message.answer(reply.text, reply_markup=reply.markup)

    return router
