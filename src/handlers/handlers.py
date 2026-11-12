# Слой контракта. Хендлеры делегируют разбор входящего сообщения и не содержат правил.

import uuid

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger

from src.core.settings import Settings
from src.handlers.incoming import reply_key
from src.handlers.text import COPY, FEEDBACK_BUTTONS, START_BUTTONS
from src.modules.knowledge.service import BotReply, KnowledgeService
from src.modules.profile.service import ProfileService
from src.modules.recommend.service import RecommendReply, RecommendService

_BUTTON_ACTIONS = ("ask", "materials", "remind")


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


def build_router(
    settings: Settings,
    knowledge: KnowledgeService | None = None,
    profile: ProfileService | None = None,
    recommend: RecommendService | None = None,
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
        if profile is not None and message.from_user is not None:
            user = await profile.ensure_user(message.from_user.id, message.from_user.username)
            if key == "profile":
                reply = await profile.show_profile(user.id)
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
            and knowledge is not None
            and profile is not None
            and message.from_user
        ):
            user = await profile.ensure_user(message.from_user.id, message.from_user.username)
            question = (message.text or "").strip()
            reply: BotReply = await knowledge.answer_question(question)
            await message.answer(reply.text)
            if reply.feedback:
                if recommend is not None:
                    await recommend.remember_topic(user.id, question)
                await message.answer(COPY["feedback"], reply_markup=feedback_keyboard())
                if await profile.should_offer_business_prompt(user.id):
                    follow = await profile.start_business_prompt(user.id)
                    await message.answer(follow.text, reply_markup=follow.markup)
            return
        if key == "smalltalk" and knowledge is not None:
            question = (message.text or "").strip()
            reply = await knowledge.answer_question(question)
            await message.answer(reply.text)
            if reply.feedback:
                await message.answer(COPY["feedback"], reply_markup=feedback_keyboard())
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

    @router.callback_query()
    async def on_button(query: CallbackQuery) -> None:
        chat_id = query.message.chat.id if query.message is not None else None
        log_handler("callback", chat_id, debug=settings.debug, text=query.data)
        await query.answer()
        if (
            query.data == "materials"
            and recommend is not None
            and profile is not None
            and query.from_user is not None
            and query.message is not None
        ):
            user = await profile.ensure_user(query.from_user.id, query.from_user.username)
            await deliver_recommendations(query.message, user.id, recommend, prefer_route=True)
        if query.data == "remind" and query.message is not None:
            await query.message.answer(
                "Напишите, о чём напомнить — например: «Напомни в пятницу продолжить курс»."
            )

    return router
