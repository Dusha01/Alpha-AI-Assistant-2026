from src.modules.recommend.utm import with_utm


def test_appends_utm_source() -> None:
    assert (
        with_utm("https://alfacourse.ru/material")
        == "https://alfacourse.ru/material?utm_source=tg_bot"
    )


def test_preserves_existing_query() -> None:
    url = with_utm("https://alfacourse.ru/m?utm_campaign=hack")
    assert "utm_campaign=hack" in url
    assert "utm_source=tg_bot" in url
