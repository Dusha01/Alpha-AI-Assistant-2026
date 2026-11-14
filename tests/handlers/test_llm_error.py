from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

import pytest
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
        self.revisions: list[str] = []
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
            self.revisions.append(method.text)
            self._sent.append((self._message_id, method.text))
            chat_id = int(method.chat_id) if isinstance(method.chat_id, str) else method.chat_id
            return Message(
                message_id=self._message_id,
                date=datetime.now(UTC),
                chat=Chat(id=chat_id, type="private"),
                text=method.text,
            ).as_(bot)
        if isinstance(method, EditMessageText):
            self.revisions.append(method.text)
            self._sent = [
                (mid, method.text if mid == method.message_id else text) for mid, text in self._sent
            ]
            return True
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
    assert COPY["thinking_search"] not in session.texts
    assert "📚 Нашёл 1 статью, формулирую…" in session.revisions


@pytest.mark.asyncio
async def test_slow_answer_replaces_the_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.handlers.handlers._SLOW_AFTER_SECONDS", 0.05)

    class Slow:
        async def complete(self, messages: list[dict[str, str]]) -> str:
            await asyncio.sleep(0.25)
            return "Ответ готов"

    session = await _ask(_service_with(Slow()))
    assert session.texts[0].startswith("Ответ готов")
    assert COPY["thinking_search"] in session.revisions
    assert "📚 Нашёл 1 статью, формулирую…" in session.revisions
    assert COPY["thinking_slow"] in session.revisions
    assert session.texts[0] != COPY["thinking_slow"]
    found_at = session.revisions.index("📚 Нашёл 1 статью, формулирую…")
    slow_at = session.revisions.index(COPY["thinking_slow"])
    assert found_at < slow_at


@pytest.mark.asyncio
async def test_short_formulation_does_not_claim_a_delay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("src.handlers.handlers._SLOW_AFTER_SECONDS", 0.2)

    class Quick:
        async def complete(self, messages: list[dict[str, str]]) -> str:
            await asyncio.sleep(0.05)
            return "Ответ готов"

    session = await _ask(_service_with(Quick()))
    assert session.texts[0].startswith("Ответ готов")
    assert "📚 Нашёл 1 статью, формулирую…" in session.revisions
    assert COPY["thinking_slow"] not in session.revisions


@pytest.mark.asyncio
async def test_search_delay_does_not_spill_into_formulation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("src.handlers.handlers._SLOW_AFTER_SECONDS", 0.05)

    class Quick:
        async def complete(self, messages: list[dict[str, str]]) -> str:
            return "Ответ готов"

    service = _service_with(Quick())

    async def search(question: str) -> list[SearchHit]:
        await asyncio.sleep(0.12)
        return [_hit()]

    service.search = search  # type: ignore[method-assign]
    session = await _ask(service)
    slow_at = session.revisions.index(COPY["thinking_slow"])
    found_at = session.revisions.index("📚 Нашёл 1 статью, формулирую…")
    assert slow_at < found_at
    assert session.revisions.count(COPY["thinking_slow"]) == 1
    assert session.texts[0].startswith("Ответ готов")


@pytest.mark.asyncio
async def test_status_counts_found_articles_not_the_prompt_limit() -> None:
    class Boom:
        async def complete(self, messages: list[dict[str, str]]) -> str:
            raise LlmRequestError("timeout")

    service = _service_with(Boom())

    async def search(question: str) -> list[SearchHit]:
        hits = [
            SearchHit(
                title=f"Статья {index}",
                url=f"https://example/{index}",
                body="текст",
                is_paid=False,
                score=0.9,
            )
            for index in range(4)
        ]
        hits.append(
            SearchHit(
                title="Дубль первой",
                url="https://example/0",
                body="тот же материал",
                is_paid=False,
                score=0.8,
            )
        )
        return hits

    service.search = search  # type: ignore[method-assign]
    session = await _ask(service)
    assert "📚 Нашёл 4 статьи, формулирую…" in session.revisions
