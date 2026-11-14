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
    assert "открытие бизнеса" in reply.text
    assert "оборотные средства" in reply.text


@pytest.mark.asyncio
async def test_visa_question_does_not_call_llm() -> None:
    class Boom:
        async def complete(self, messages: list[dict[str, str]]) -> str:
            raise AssertionError(messages)

    service = _service(_settings(), Boom())  # type: ignore[arg-type]
    reply = await service.answer_from_hits(
        "Как оформить визу в Китай за запчастями?",
        [
            SearchHit(
                title="Какие налоги платят в Китае",
                url="https://example/china",
                body="налоги в Китае",
                is_paid=False,
                score=0.91,
            )
        ],
    )
    assert reply.text == COPY["not_found_visa"]
    assert reply.feedback is False


@pytest.mark.asyncio
async def test_unexpected_llm_error_returns_hitch() -> None:
    class Boom:
        async def complete(self, messages: list[dict[str, str]]) -> str:
            raise RuntimeError(messages)

    service = _service(_settings(), Boom())  # type: ignore[arg-type]

    async def retrieve(question: str) -> tuple[list[SearchHit], str | None]:
        return [
            SearchHit(
                title="Учёт на УСН",
                url="https://example/usn",
                body="Как вести учёт доходов на УСН",
                is_paid=False,
                score=0.9,
            )
        ], None

    service.retrieve = retrieve  # type: ignore[method-assign]
    reply = await service.answer_question("Как вести учёт доходов на УСН?")
    assert reply.text == COPY["error_llm"]


@pytest.mark.asyncio
async def test_fact_is_announced_before_the_answer_model() -> None:
    order: list[str] = []

    class OrderedLlm:
        async def complete(self, messages: list[dict[str, str]]) -> str:
            order.append("llm")
            return "Короткий ответ из модели."

    service = _service(_settings(), OrderedLlm())  # type: ignore[arg-type]

    async def on_sources(count: int) -> None:
        order.append(f"sources:{count}")

    async def on_fact(text: str) -> None:
        order.append(text)

    await service.answer_from_hits(
        "Как вести учёт доходов на УСН?",
        [
            SearchHit(
                title="Учёт на УСН",
                url="https://example/usn",
                body="Как вести учёт доходов на УСН",
                is_paid=False,
                score=0.9,
            )
        ],
        on_sources=on_sources,
        on_fact=on_fact,
        fact="Взносы уменьшают налог на УСН.",
    )
    assert order == [
        "sources:1",
        "💡 Кстати, у меня есть интересный факт: Взносы уменьшают налог на УСН.",
        "llm",
    ]


@pytest.mark.asyncio
async def test_not_found_does_not_announce_a_fact() -> None:
    announced: list[str] = []

    async def on_fact(text: str) -> None:
        announced.append(text)

    service = _service(_settings(), StubLlmClient())
    reply = await service.answer_from_hits(
        "Как вести учёт доходов на УСН?",
        [
            SearchHit(
                title="Чужой материал",
                url="https://example/other",
                body="совсем другая тема",
                is_paid=False,
                score=0.1,
            )
        ],
        on_fact=on_fact,
        fact="Взносы уменьшают налог на УСН.",
    )
    assert reply.text == COPY["not_found"]
    assert announced == []
