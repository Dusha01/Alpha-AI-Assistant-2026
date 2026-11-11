from src.modules.knowledge.service import _should_append_source


def test_skips_duplicate_source_line() -> None:
    llm = "Короткий ответ.\n\nПодробнее в материале «Переход на УСН»: https://example/one"
    assert _should_append_source(llm, "Переход на УСН", "https://example/one") is False


def test_appends_when_source_missing() -> None:
    assert _should_append_source("Только текст ответа.", "Материал", "https://example/two") is True
