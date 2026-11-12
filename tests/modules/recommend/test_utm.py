from src.modules.recommend.utm import with_utm


def test_appends_utm_source() -> None:
    assert (
        with_utm("https://alfacourse.ru/material")
        == "https://alfacourse.ru/material?utm_source=tg_bot&utm_medium=telegram"
    )


def test_preserves_existing_query() -> None:
    url = with_utm("https://alfacourse.ru/m?utm_campaign=hack", campaign="answer")
    assert "utm_campaign=hack" in url
    assert "utm_campaign=answer" not in url
    assert "utm_source=tg_bot" in url
    assert "utm_medium=telegram" in url


def test_sets_campaign_and_slug() -> None:
    url = with_utm(
        "https://alfacourse.ru/courses/usn-income",
        campaign="answer",
        content="usn-income",
    )
    assert "utm_source=tg_bot" in url
    assert "utm_medium=telegram" in url
    assert "utm_campaign=answer" in url
    assert "utm_content=usn-income" in url
