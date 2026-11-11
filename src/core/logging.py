import logging
import sys
from urllib.parse import urlsplit, urlunsplit

from loguru import logger

_LEVELS = frozenset({"TRACE", "DEBUG", "INFO", "SUCCESS", "WARNING", "ERROR", "CRITICAL"})
_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level:<8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)
_INTERCEPTED = (
    "aiogram",
    "aiogram.event",
    "aiogram.dispatcher",
    "aiohttp",
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
    "gunicorn",
    "gunicorn.error",
    "gunicorn.access",
    "sqlalchemy",
    "sqlalchemy.engine",
    "sqlalchemy.pool",
    "alembic",
)


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = logging.currentframe(), 0
        while frame is not None and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging(level: str, *, debug: bool = False) -> None:
    normalized = "DEBUG" if debug else level.upper()
    if normalized not in _LEVELS:
        normalized = "INFO"
    logger.remove()
    logger.add(
        sys.stderr,
        level=normalized,
        format=_FORMAT,
        colorize=True,
        enqueue=True,
        backtrace=debug,
        diagnose=debug,
    )
    intercept = InterceptHandler()
    logging.root.handlers = [intercept]
    logging.root.setLevel(normalized)
    for name in _INTERCEPTED:
        named = logging.getLogger(name)
        named.handlers = [intercept]
        named.propagate = False
        if debug and name.startswith("sqlalchemy"):
            named.setLevel(logging.DEBUG if name != "sqlalchemy.engine" else logging.INFO)
        else:
            named.setLevel(logging.DEBUG if debug else getattr(logging, normalized))


def mask_database_url(url: str) -> str:
    if not url:
        return "не задан"
    parsed = urlsplit(url)
    if not parsed.password:
        return url
    netloc = parsed.netloc.replace(f":{parsed.password}@", ":***@", 1)
    return urlunsplit(parsed._replace(netloc=netloc))


def log_bot_banner(settings: object) -> None:
    from src.core.version import __version__

    token = str(getattr(settings, "telegram_bot_token", "")).strip()
    debug = bool(getattr(settings, "debug", False))
    logger.info("Альфа-Курс бот {}", __version__)
    logger.info(
        "env={} debug={} level={} api={}:{}",
        getattr(settings, "app_env", ""),
        debug,
        "DEBUG" if debug else getattr(settings, "log_level", "INFO"),
        getattr(settings, "api_host", ""),
        getattr(settings, "api_port", ""),
    )
    database_url = getattr(
        settings,
        "database_url_resolved",
        getattr(settings, "database_url", ""),
    )
    logger.info("database={}", mask_database_url(str(database_url)))
    logger.info("telegram token={}", "задан" if token else "не задан")
    logger.info("handlers: start, help, unknown_command, smalltalk, non_text, callback")
