from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_EMPTY_PROXY_VALUES = frozenset({"none", "null", "-", "off", "false"})


def normalize_proxy_url(proxy_url: str | None) -> str | None:
    raw = (proxy_url or "").strip()
    if not raw:
        return None
    if raw.lower() in _EMPTY_PROXY_VALUES:
        return None
    return raw


def mask_proxy_url(url: str) -> str:
    if "@" not in url:
        return url
    scheme, _, rest = url.partition("://")
    creds, _, host = rest.rpartition("@")
    if ":" in creds:
        user = creds.split(":", 1)[0]
        return f"{scheme}://{user}:***@{host}"
    return f"{scheme}://***@{host}"


def log_telegram_proxy_mode(proxy_url: str | None) -> None:
    normalized = normalize_proxy_url(proxy_url)
    if normalized is None:
        logger.info("Telegram API: прямое подключение (без прокси)")
        return

    low = normalized.lower()
    if low.startswith(("socks5://", "socks5h://", "socks4://")):
        logger.info("Telegram API: SOCKS-прокси %s", mask_proxy_url(normalized))
    else:
        logger.info("Telegram API: HTTP(S)-прокси %s", mask_proxy_url(normalized))


def build_telegram_httpx_client_kwargs(
    proxy_url: str | None,
    *,
    timeout: float,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"timeout": timeout}
    normalized = normalize_proxy_url(proxy_url)
    if normalized is not None:
        kwargs["proxy"] = normalized
    return kwargs
