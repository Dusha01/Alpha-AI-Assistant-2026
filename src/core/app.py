import asyncio
import contextlib
import os
from collections.abc import Awaitable, Callable

from loguru import logger

from src.core.logging import log_bot_banner, setup_logging
from src.core.proxy import log_telegram_proxy_mode
from src.core.settings import Settings

Receive = Callable[[], Awaitable[dict]]
Send = Callable[[dict], Awaitable[None]]

_poll_task: asyncio.Task[None] | None = None


async def poll(settings: Settings) -> None:
    from aiogram import Bot, Dispatcher
    from aiogram.client.session.aiohttp import AiohttpSession

    from src.handlers.errors import on_handler_error
    from src.handlers.handlers import build_router

    session = AiohttpSession(proxy=settings.telegram_proxy_url)
    bot = Bot(token=settings.telegram_bot_token, session=session)
    dispatcher = Dispatcher()
    dispatcher.include_router(build_router(settings))
    dispatcher.errors.register(on_handler_error)
    try:
        await dispatcher.start_polling(bot, handle_signals=False, close_bot_session=False)
    finally:
        await bot.session.close()


def _start_polling_if_configured() -> asyncio.Task[None] | None:
    settings = Settings()
    setup_logging(settings.log_level, debug=settings.debug)
    log_bot_banner(settings)
    if not settings.telegram_bot_token.strip():
        logger.error("TELEGRAM_BOT_TOKEN пуст. Опрос Telegram не запущен.")
        return None
    log_telegram_proxy_mode(settings.telegram_proxy_url)
    return asyncio.create_task(poll(settings))


async def _lifespan(receive: Receive, send: Send) -> None:
    global _poll_task
    while True:
        message = await receive()
        if message["type"] == "lifespan.startup":
            _poll_task = _start_polling_if_configured()
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
