import uuid

from src.data.models.chunk import Chunk
from src.data.models.fact import Fact
from src.modules.knowledge.embedder import FixedLengthEmbedder
from src.modules.knowledge.facts import (
    MaterialText,
    chosen_fact,
    fact_from_llm,
    fill_facts_from_materials,
    materials_from_chunks,
)


def test_fact_below_threshold_is_dropped() -> None:
    assert chosen_fact("Взносы уменьшают налог.", 0.44, threshold=0.45) is None
    assert chosen_fact("Взносы уменьшают налог.", 0.45, threshold=0.45) == (
        "Взносы уменьшают налог."
    )
    assert chosen_fact(None, 0.9, threshold=0.45) is None


def test_empty_llm_reply_is_not_a_fact() -> None:
    assert fact_from_llm("нет") is None
    assert fact_from_llm("  Нет. ") is None
    assert fact_from_llm("") is None


def test_llm_sentence_is_kept() -> None:
    assert fact_from_llm("«Взносы уменьшают налог на УСН.»") == "Взносы уменьшают налог на УСН."


def test_materials_are_grouped_by_source() -> None:
    material_id = uuid.uuid4()
    rows = [
        _chunk(material_id, 1, "вторая часть"),
        _chunk(material_id, 0, "первая часть"),
    ]
    materials = materials_from_chunks(rows)
    assert len(materials) == 1
    assert materials[0].body == "первая часть\nвторая часть"
    assert materials[0].title == "УСН"


class _MemoryFacts:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, uuid.UUID], Fact] = {}

    async def delete_for_material(self, material_type: str, material_id: uuid.UUID) -> int:
        self.rows.pop((material_type, material_id), None)
        return 1

    async def replace_for_material(self, fact: Fact) -> None:
        self.rows[(fact.material_type, fact.material_id)] = fact


class _ScriptLlm:
    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)

    async def complete(self, messages: list[dict[str, str]]) -> str:
        return self.replies.pop(0)


async def test_empty_extraction_writes_nothing_and_rerun_does_not_duplicate() -> None:
    material_id = uuid.uuid4()
    material = MaterialText(
        material_type="article",
        material_id=material_id,
        title="УСН",
        url="https://example/usn",
        body="Страховые взносы уменьшают налог на УСН.",
    )
    store = _MemoryFacts()
    embedder = FixedLengthEmbedder()

    empty = await fill_facts_from_materials(
        [material],
        llm=_ScriptLlm(["нет"]),
        embedder=embedder,
        repository=store,
    )
    assert empty == {"written": 0, "skipped": 1, "failed": 0}
    assert store.rows == {}

    phrase = "Страховые взносы уменьшают налог на УСН."
    await fill_facts_from_materials(
        [material],
        llm=_ScriptLlm([phrase]),
        embedder=embedder,
        repository=store,
    )
    await fill_facts_from_materials(
        [material],
        llm=_ScriptLlm(["Повторная формулировка того же факта."]),
        embedder=embedder,
        repository=store,
    )
    assert len(store.rows) == 1
    stored = store.rows[("article", material_id)]
    assert stored.body == "Повторная формулировка того же факта."
    assert stored.embedding == [0.01] * 384


def _chunk(material_id: uuid.UUID, index: int, body: str) -> Chunk:
    return Chunk(
        material_type="article",
        material_id=material_id,
        chunk_index=index,
        title="УСН",
        url="https://example/usn",
        is_paid=False,
        body=body,
        include_in_rag=True,
        embedding=[0.1] * 384,
    )
