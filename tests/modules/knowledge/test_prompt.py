from src.modules.knowledge.prompt import build_llm_messages, prompt_contains_forbidden_data
from src.modules.knowledge.types import SearchHit


def test_prompt_excludes_chunks_not_in_rag() -> None:
    messages = build_llm_messages(
        "Как получить кредит?",
        (
            SearchHit(
                title="Разрешённый",
                url="https://example/ok",
                body="основной текст",
                is_paid=False,
                score=0.7,
                include_in_rag=True,
            ),
            SearchHit(
                title="Скрытый",
                url="https://example/hidden",
                body="секретный текст",
                is_paid=False,
                score=0.69,
                include_in_rag=False,
            ),
        ),
    )
    joined = "\n".join(message["content"] for message in messages)
    assert "Разрешённый" in joined
    assert "Скрытый" not in joined
    assert "секретный текст" not in joined


def test_prompt_does_not_include_telegram_id() -> None:
    messages = build_llm_messages(
        "Как вести учёт доходов на УСН?",
        (
            SearchHit(
                title="Учёт на УСН",
                url="https://example/usn",
                body="фрагмент",
                is_paid=False,
                score=0.8,
            ),
        ),
    )
    assert not prompt_contains_forbidden_data(messages, "123456789")
    assert "без текста уроков" in messages[0]["content"]
    assert "Другие банки не называйте" in messages[0]["content"]
