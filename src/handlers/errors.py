from aiogram.types import ErrorEvent
from loguru import logger

from src.handlers.text import COPY


def handler_failure_key() -> str:
    return "error_general"


async def on_handler_error(event: ErrorEvent) -> bool:
    logger.opt(exception=event.exception).error("Ошибка обработчика")
    message = event.update.message
    if message is None and event.update.callback_query is not None:
        maybe_message = event.update.callback_query.message
        if maybe_message is not None and hasattr(maybe_message, "answer"):
            message = maybe_message
    if message is not None:
        try:
            await message.answer(COPY[handler_failure_key()])
        except Exception:
            logger.exception("Не удалось отправить сообщение об ошибке")
    return True
