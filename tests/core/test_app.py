import pytest

from src.core.app import app, poll
from src.core.settings import Settings
from src.modules.knowledge.embedder import LazySentenceTransformerEmbedder


@pytest.mark.asyncio
async def test_health() -> None:
    sent: list[dict] = []

    async def receive() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict) -> None:
        sent.append(message)

    await app({"type": "http", "path": "/health"}, receive, send)
    assert sent[0]["status"] == 200
    assert sent[1]["body"] == b"ok"


@pytest.mark.asyncio
async def test_lifespan_without_token_does_not_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setenv("TELEGRAM_PROXY_URL", "")
    monkeypatch.setattr("src.core.app.run_migrations", lambda database_url: None)
    messages = [
        {"type": "lifespan.startup"},
        {"type": "lifespan.shutdown"},
    ]

    async def receive() -> dict:
        return messages.pop(0)

    sent: list[dict] = []

    async def send(message: dict) -> None:
        sent.append(message)

    await app({"type": "lifespan"}, receive, send)
    assert [item["type"] for item in sent] == [
        "lifespan.startup.complete",
        "lifespan.shutdown.complete",
    ]


@pytest.mark.asyncio
async def test_polling_leaves_signals_to_the_server(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    class Session:
        def __init__(self, proxy: str | None = None) -> None:
            self.proxy = proxy

        async def close(self) -> None:
            captured["closed"] = True

    class Bot:
        def __init__(self, token: str, session: Session) -> None:
            self.token = token
            self.session = session

    class Errors:
        def register(self, handler: object) -> None:
            captured["error_handler"] = handler

    class Dispatcher:
        def __init__(self) -> None:
            self.errors = Errors()

        def include_router(self, router: object) -> None:
            captured["router"] = router

        async def start_polling(self, bot: Bot, **kwargs: object) -> None:
            captured["bot"] = bot
            captured["kwargs"] = kwargs

    monkeypatch.setattr("aiogram.Bot", Bot)
    monkeypatch.setattr("aiogram.Dispatcher", Dispatcher)
    monkeypatch.setattr("aiogram.client.session.aiohttp.AiohttpSession", Session)
    warmed: list[str] = []

    def warmup(self: LazySentenceTransformerEmbedder) -> None:
        warmed.append(self.model_name)

    monkeypatch.setattr(
        "src.modules.knowledge.embedder.LazySentenceTransformerEmbedder.warmup",
        warmup,
    )

    class _Engine:
        async def dispose(self) -> None:
            captured["engine_disposed"] = True

    class _Factory:
        async def __aenter__(self) -> None:
            return None

        async def __aexit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr("src.data.database.create_engine", lambda database_url: _Engine())
    monkeypatch.setattr(
        "src.data.database.create_session_factory",
        lambda engine: lambda: _Factory(),
    )

    settings = Settings(
        _env_file=None,
        telegram_bot_token="123:test",
        telegram_proxy_url=None,
        database_url="postgresql+asyncpg://alfa:pass@localhost/alfa_course",
    )
    await poll(settings)

    assert captured["kwargs"]["handle_signals"] is False
    assert warmed == [settings.embedding_model]
