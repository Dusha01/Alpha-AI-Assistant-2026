from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
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
from aiogram.types import Chat, Message, Update, User
from tests.modules.knowledge.test_service import _service, _settings

from src.core.settings import Settings
from src.handlers.errors import on_handler_error
from src.handlers.handlers import build_router
from src.handlers.text import COPY
from src.modules.knowledge.llm import LlmRequestError
from src.modules.knowledge.service import KnowledgeService
from src.modules.knowledge.types import SearchHit

_TOKEN = "123456789:AAH-scenario-test"


class _RecordingSession(BaseSession):
    def __init__(self) -> None:
        super().__init__()
        self._sent: list[tuple[int, str]] = []
        self.actions: list[str] = []
        self._message_id = 1

    @property
    def texts(self) -> list[str]:
        return [text for _, text in self._sent]

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
            self._message_id += 1
            self._sent.append((self._message_id, method.text))
            chat_id = int(method.chat_id) if isinstance(method.chat_id, str) else method.chat_id
            return Message(
                message_id=self._message_id,
                date=datetime.now(UTC),
                chat=Chat(id=chat_id, type="private"),
                text=method.text,
            ).as_(bot)
        if isinstance(method, SendChatAction):
            self.actions.append(method.action)
            return True
        if isinstance(method, DeleteMessage):
            self._sent = [item for item in self._sent if item[0] != method.message_id]
            return True
        if isinstance(method, AnswerCallbackQuery):
            return True
        raise AssertionError(type(method).__name__)


def _hit() -> SearchHit:
    return SearchHit(
        title="Учёт на УСН",
        url="https://example/usn",
        body="Как вести учёт доходов на УСН",
        is_paid=False,
        score=0.9,
    )


def _service_with(llm: object) -> KnowledgeService:
    service = _service(_settings(), llm)  # type: ignore[arg-type]

    async def search(question: str) -> list[SearchHit]:
        return [_hit()]

    service.search = search  # type: ignore[method-assign]
    return service


async def _ask(service: KnowledgeService) -> _RecordingSession:
    session = _RecordingSession()
    bot = Bot(token=_TOKEN, session=session)
    dispatcher = Dispatcher()
    dispatcher.include_router(build_router(Settings(_env_file=None), service))  # type: ignore[arg-type]
    dispatcher.errors.register(on_handler_error)
    message = Message(
        message_id=1,
        date=datetime.now(UTC),
        chat=Chat(id=501, type="private"),
        from_user=User(id=501, is_bot=False, first_name="Тест"),
        text="Как вести учёт доходов на УСН?",
    )
    update = Update(update_id=1, message=message)
    update.as_(bot)
    message.as_(bot)
    await dispatcher.feed_update(bot, update)
    return session


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [LlmRequestError("timeout"), RuntimeError("boom")],
)
async def test_model_failure_sends_only_the_hitch(error: Exception) -> None:
    class Boom:
        async def complete(self, messages: list[dict[str, str]]) -> str:
            raise error

    session = await _ask(_service_with(Boom()))
    assert session.texts == [COPY["error_llm"]]
    assert session.actions == ["typing"]
    assert COPY["thinking"] not in session.texts
