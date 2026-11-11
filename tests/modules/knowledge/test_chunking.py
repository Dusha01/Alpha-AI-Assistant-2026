from src.modules.knowledge.chunking import split_text_windows


def test_split_single_short_text() -> None:
    assert split_text_windows("короткий", window=800) == ["короткий"]


def test_split_long_text_into_windows() -> None:
    text = "а" * 2000
    chunks = split_text_windows(text, window=800, overlap=0)
    assert len(chunks) == 3
    assert all(len(chunk) <= 800 for chunk in chunks)


def test_split_empty_text_returns_empty_list() -> None:
    assert split_text_windows("   ", window=800) == []
