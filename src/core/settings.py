from urllib.parse import urlsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.proxy import normalize_proxy_url

_PROXY_SCHEMES = frozenset({"http", "https", "socks4", "socks5", "socks5h"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env.dev",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    telegram_bot_token: str = ""
    telegram_proxy_url: str | None = None
    database_url: str = ""
    database_url_host: str = ""
    app_env: str = "dev"
    debug: bool = False
    log_level: str = "INFO"
    message_max_length: int = 1000
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    @field_validator("telegram_proxy_url", mode="before")
    @classmethod
    def validate_proxy_url(cls, value: object) -> str | None:
        if value is None:
            return None
        normalized = normalize_proxy_url(str(value))
        if normalized is None:
            return None
        parsed = urlsplit(normalized)
        if parsed.scheme.lower() not in _PROXY_SCHEMES or not parsed.hostname:
            raise ValueError("TELEGRAM_PROXY_URL must be an http(s) or socks URL")
        return normalized

    @property
    def database_url_resolved(self) -> str:
        return self.database_url_host or self.database_url
