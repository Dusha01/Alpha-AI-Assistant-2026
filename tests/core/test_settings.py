import pytest
from pydantic import ValidationError

from src.core.settings import Settings


def test_empty_token_does_not_fail_import(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setenv("TELEGRAM_PROXY_URL", "")
    settings = Settings(_env_file=None)
    assert settings.telegram_bot_token == ""
    assert settings.telegram_proxy_url is None


def test_invalid_proxy_url_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setenv("TELEGRAM_PROXY_URL", "ftp://proxy.example")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_http_and_empty_proxy_markers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("TELEGRAM_PROXY_URL", "http://user:secret@proxy:8080")
    settings = Settings(_env_file=None)
    assert settings.telegram_proxy_url == "http://user:secret@proxy:8080"

    monkeypatch.setenv("TELEGRAM_PROXY_URL", "off")
    assert Settings(_env_file=None).telegram_proxy_url is None
