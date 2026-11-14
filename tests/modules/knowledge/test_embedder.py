from src.modules.knowledge.embedder import LazySentenceTransformerEmbedder


def test_warmup_loads_the_model_once_and_encodes(monkeypatch) -> None:
    created: list[str] = []

    class FakeEmbedder:
        def __init__(self, model_name: str) -> None:
            created.append(model_name)
            self.queries: list[str] = []

        def embed_query(self, text: str) -> list[float]:
            self.queries.append(text)
            return [0.0]

        def embed_passages(self, texts: list[str]) -> list[list[float]]:
            return [[0.0] for _ in texts]

    monkeypatch.setattr(
        "src.modules.knowledge.embedder.SentenceTransformerEmbedder",
        FakeEmbedder,
    )
    embedder = LazySentenceTransformerEmbedder("test-model")
    embedder.warmup()
    embedder.warmup()

    assert created == ["test-model"]
    assert embedder._inner is not None
    assert embedder._inner.queries == ["прогрев", "прогрев"]
