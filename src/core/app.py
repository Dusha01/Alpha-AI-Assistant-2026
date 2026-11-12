import asyncio
import contextlib
import os
from collections.abc import Awaitable, Callable

from loguru import logger

from src.core.logging import log_bot_banner, setup_logging
from src.core.proxy import log_telegram_proxy_mode
from src.core.settings import Settings
from src.data.migrate import run_migrations

Receive = Callable[[], Awaitable[dict]]
Send = Callable[[dict], Awaitable[None]]

_poll_task: asyncio.Task[None] | None = None


async def poll(settings: Settings) -> None:
    from aiogram import Bot, Dispatcher
    from aiogram.client.session.aiohttp import AiohttpSession

    from src.data.database import create_engine, create_session_factory
    from src.handlers.errors import on_handler_error
    from src.handlers.handlers import build_router
    from src.modules.knowledge.embedder import LazySentenceTransformerEmbedder
    from src.modules.knowledge.llm import OpenAICompatibleLlm
    from src.modules.knowledge.service import KnowledgeService
    from src.modules.profile.service import ProfileService
    from src.modules.recommend.service import RecommendService

    session = AiohttpSession(proxy=settings.telegram_proxy_url)
    bot = Bot(token=settings.telegram_bot_token, session=session)
    dispatcher = Dispatcher()
    engine = create_engine(settings.database_url_resolved)
    session_factory = create_session_factory(engine)
    knowledge = KnowledgeService(
        settings=settings,
        session_factory=session_factory,
        embedder=LazySentenceTransformerEmbedder(settings.embedding_model),
        llm=OpenAICompatibleLlm(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            fallback_model=settings.llm_fallback_model,
            timeout_seconds=settings.llm_timeout_seconds,
        ),
    )
    profiles = ProfileService(session_factory=session_factory)
    recommend = RecommendService(settings=settings, session_factory=session_factory)
    dispatcher.include_router(build_router(settings, knowledge, profiles, recommend))
    dispatcher.errors.register(on_handler_error)
    try:
        await dispatcher.start_polling(bot, handle_signals=False, close_bot_session=False)
    finally:
        await bot.session.close()
        await engine.dispose()


def _start_polling_if_configured(settings: Settings) -> asyncio.Task[None] | None:
    if not settings.telegram_bot_token.strip():
        logger.error("TELEGRAM_BOT_TOKEN пуст. Опрос Telegram не запущен.")
        return None
    log_telegram_proxy_mode(settings.telegram_proxy_url)
    return asyncio.create_task(poll(settings))


async def _lifespan(receive: Receive, send: Send) -> None:
    global _poll_task
    settings = Settings()
    setup_logging(settings.log_level, debug=settings.debug)
    log_bot_banner(settings)
    while True:
        message = await receive()
        if message["type"] == "lifespan.startup":
            try:
                await asyncio.to_thread(run_migrations, settings.database_url_resolved)
            except Exception as exc:
                logger.exception("Не удалось применить миграции")
                await send({"type": "lifespan.startup.failed", "message": str(exc)})
                return
            _poll_task = _start_polling_if_configured(settings)
            await send({"type": "lifespan.startup.complete"})
        elif message["type"] == "lifespan.shutdown":
            if _poll_task is not None:
                _poll_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await _poll_task
                _poll_task = None
            await send({"type": "lifespan.shutdown.complete"})
            return


async def app(scope: dict, receive: Receive, send: Send) -> None:
    if scope["type"] == "lifespan":
        await _lifespan(receive, send)
        return
    if scope["type"] == "http" and scope.get("path") == "/health":
        body = b"ok"
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/plain; charset=utf-8")],
            }
        )
        await send({"type": "http.response.body", "body": body})
        return
    await send({"type": "http.response.start", "status": 404, "headers": []})
    await send({"type": "http.response.body", "body": b""})


def main() -> None:
    os.execvp(
        "gunicorn",
        ["gunicorn", "-c", "src/core/gunicorn.conf.py", "src.core.app:app"],
    )


if __name__ == "__main__":
    main()
