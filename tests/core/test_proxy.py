import pytest

from src.core.proxy import mask_proxy_url, normalize_proxy_url


@pytest.mark.parametrize(
    "value",
    ["", "   ", None, "none", "NONE", "off", "null", "-", "false"],
)
def test_normalize_proxy_url_treats_empty_markers_as_direct(value: str | None) -> None:
    assert normalize_proxy_url(value) is None


def test_normalize_proxy_url_keeps_real_proxy() -> None:
    assert normalize_proxy_url("  socks5://user:secret@127.0.0.1:1080 ") == (
        "socks5://user:secret@127.0.0.1:1080"
    )


def test_mask_proxy_url_hides_password() -> None:
    assert mask_proxy_url("http://user:secret@proxy.local:8080") == (
        "http://user:***@proxy.local:8080"
    )


def test_mask_proxy_url_hides_token_without_password_separator() -> None:
    assert mask_proxy_url("http://token@proxy.local:8080") == "http://***@proxy.local:8080"


def test_mask_proxy_url_leaves_url_without_credentials() -> None:
    assert mask_proxy_url("http://proxy.local:8080") == "http://proxy.local:8080"
