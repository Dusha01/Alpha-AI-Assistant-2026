import pytest

from src.core.settings import Settings
from src.handlers.text import COPY
from src.modules.knowledge.llm import StubLlmClient
from src.modules.knowledge.service import KnowledgeService
from src.modules.knowledge.types import SearchHit


def _settings(**overrides: object) -> Settings:
    base = {
        "_env_file": None,
        "llm_api_key": "secret",
        "llm_base_url": "https://llm.example",
        "llm_model": "test",
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def _service(settings: Settings, llm: StubLlmClient) -> KnowledgeService:
    class _Factory:
        async def __aenter__(self) -> None:
            return None

        async def __aexit__(self, *args: object) -> None:
            return None

    def session_factory() -> _Factory:
        return _Factory()  # type: ignore[return-value]

    class _Embedder:
        def embed_passages(self, texts: list[str]) -> list[list[float]]:
            return [[0.1] * 384 for _ in texts]

        def embed_query(self, text: str) -> list[float]:
            return [0.1] * 384

    return KnowledgeService(
        settings=settings,
        session_factory=session_factory,  # type: ignore[arg-type]
        embedder=_Embedder(),
        llm=llm,
    )


@pytest.mark.asyncio
async def test_empty_llm_key_returns_error_llm() -> None:
    service = _service(_settings(llm_api_key=""), StubLlmClient())
    reply = await service.answer_from_hits(
        "вопрос про материал",
        [
            SearchHit(
                title="Материал",
                url="https://example",
                body="текст вопроса по материалу",
                is_paid=False,
                score=0.9,
            )
        ],
    )
    assert reply.text == COPY["error_llm"]


@pytest.mark.asyncio
async def test_answer_appends_source_and_feedback_flag() -> None:
    llm = StubLlmClient("Короткий ответ из модели.")
    service = _service(_settings(), llm)
    reply = await service.answer_from_hits(
        "Как вести учёт доходов на УСН?",
        [
            SearchHit(
                title="Учёт на УСН",
                url="https://example/usn",
                body="Как вести учёт доходов на УСН",
                is_paid=False,
                score=0.82,
            )
        ],
    )
    assert reply.feedback is True
    assert reply.material_title == "Учёт на УСН"
    assert "Короткий ответ из модели." in reply.text
    assert "Подробнее в материале «Учёт на УСН»" in reply.text
    assert "utm_campaign=answer" in reply.text
    assert "utm_content=usn" in reply.text
    assert llm.last_messages is not None
    prompt = "\n".join(item["content"] for item in llm.last_messages)
    assert "Как вести учёт доходов на УСН?" in prompt
    assert "utm_campaign" not in prompt


@pytest.mark.asyncio
async def test_credit_question_triggers_clarify_copy() -> None:
    service = _service(_settings(), StubLlmClient())
    reply = await service.answer_from_hits(
        "как получить кредит?",
        [
            SearchHit(
                title="Кредит для ИП",
                url="https://example/credit",
                body="как получить кредит для ИП",
                is_paid=False,
                score=0.62,
            ),
            SearchHit(
                title="Ипотека для бизнеса",
                url="https://example/mortgage",
                body="ипотека для бизнеса",
                is_paid=False,
                score=0.59,
            ),
        ],
    )
    assert "Кредит для ИП" in reply.text
    assert "Ипотека для бизнеса" in reply.text
