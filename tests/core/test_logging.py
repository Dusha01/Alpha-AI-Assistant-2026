import logging

from loguru import logger

from src.core.logging import setup_logging


def test_stdlib_records_go_through_loguru(capsys) -> None:
    setup_logging("INFO")
    logging.getLogger("aiogram").info("stdlib-marker")
    logger.complete()
    captured = capsys.readouterr()
    assert "stdlib-marker" in captured.err


def test_debug_flag_shows_debug_records(capsys) -> None:
    setup_logging("INFO", debug=True)
    logger.debug("visible-debug")
    logger.complete()
    assert "visible-debug" in capsys.readouterr().err


def test_banner_hides_token_and_database_password(capsys) -> None:
    from types import SimpleNamespace

    from src.core.logging import log_bot_banner

    setup_logging("INFO")
    log_bot_banner(
        SimpleNamespace(
            app_env="dev",
            debug=True,
            log_level="INFO",
            api_host="0.0.0.0",
            api_port=8000,
            database_url="postgresql+asyncpg://alfa:secret@postgres:5432/alfa_course",
            telegram_bot_token="123:secret-token",
        )
    )
    logger.complete()
    text = capsys.readouterr().err
    assert "Альфа-Курс бот" in text
    assert "handler" in text or "handlers: start" in text
    assert "secret" not in text
    assert "123:secret-token" not in text


def test_start_handler_is_logged(capsys) -> None:
    from src.handlers.handlers import log_handler

    setup_logging("INFO", debug=True)
    log_handler("start", 42, debug=True, text="/start")
    logger.complete()
    text = capsys.readouterr().err
    assert "handler=start" in text
    assert "chat_id=42" in text
    assert "/start" in text


def test_unknown_level_falls_back_to_info(capsys) -> None:
    setup_logging("nope")
    logger.debug("hidden-debug")
    logger.info("visible-info")
    logger.complete()
    captured = capsys.readouterr()
    assert "hidden-debug" not in captured.err
    assert "visible-info" in captured.err
