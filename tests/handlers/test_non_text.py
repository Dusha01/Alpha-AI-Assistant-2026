from datetime import UTC, datetime
from typing import Any

import pytest
from aiogram import Bot, Dispatcher
from aiogram.client.session.base import BaseSession
from aiogram.methods import SendMessage, TelegramMethod
from aiogram.methods.base import TelegramType
from aiogram.types import Chat, Message, PhotoSize, Sticker, Update, User, Voice

from src.core.settings import Settings
from src.handlers.errors import on_handler_error
from src.handlers.handlers import build_router
from src.handlers.text import COPY

_TOKEN = "123456789:AAH-scenario-test"


class _RecordingSession(BaseSession):
    def __init__(self) -> None:
        super().__init__()
        self.texts: list[str] = []

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
            self.texts.append(method.text)
            return Message(
                message_id=len(self.texts) + 1,
                date=datetime.now(UTC),
                chat=Chat(id=501, type="private"),
                text=method.text,
            ).as_(bot)
        raise AssertionError(type(method).__name__)


def _message(**extra: object) -> Message:
    return Message(
        message_id=1,
        date=datetime.now(UTC),
        chat=Chat(id=501, type="private"),
        from_user=User(id=501, is_bot=False, first_name="Тест"),
        **extra,  # type: ignore[arg-type]
    )


async def _feed(message: Message, *, max_length: int = 1000) -> list[str]:
    session = _RecordingSession()
    bot = Bot(token=_TOKEN, session=session)
    dispatcher = Dispatcher()
    dispatcher.include_router(
        build_router(Settings(_env_file=None, message_max_length=max_length))  # type: ignore[arg-type]
    )
    dispatcher.errors.register(on_handler_error)
    update = Update(update_id=1, message=message)
    update.as_(bot)
    message.as_(bot)
    await dispatcher.feed_update(bot, update)
    return session.texts


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "message",
    [
        _message(
            sticker=Sticker(
                file_id="sticker",
                file_unique_id="sticker-1",
                type="regular",
                width=64,
                height=64,
                is_animated=False,
                is_video=False,
            )
        ),
        _message(voice=Voice(file_id="voice", file_unique_id="voice-1", duration=2)),
        _message(
            photo=[
                PhotoSize(file_id="photo", file_unique_id="photo-1", width=10, height=10),
            ]
        ),
    ],
)
async def test_media_gets_a_text_reply(message: Message) -> None:
    assert await _feed(message) == [COPY["non_text"]]


@pytest.mark.asyncio
async def test_long_text_is_rejected_without_a_search() -> None:
    assert await _feed(_message(text="я" * 21), max_length=20) == [COPY["too_long"]]
