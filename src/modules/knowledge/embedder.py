from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Embedder(Protocol):
    def embed_passages(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class FixedLengthEmbedder:
    def __init__(self, dimensions: int = 384, fill: float = 0.01) -> None:
        self.dimensions = dimensions
        self.fill = fill

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return [[self.fill] * self.dimensions for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [self.fill] * self.dimensions


class LazySentenceTransformerEmbedder:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._inner: SentenceTransformerEmbedder | None = None

    def _get(self) -> SentenceTransformerEmbedder:
        if self._inner is None:
            self._inner = SentenceTransformerEmbedder(self.model_name)
        return self._inner

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return self._get().embed_passages(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._get().embed_query(text)

    def warmup(self) -> None:
        self.embed_query("прогрев")


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        prefixed = [f"passage: {text}" for text in texts]
        vectors = self.model.encode(
            prefixed,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [vector.tolist() for vector in vectors]

    def embed_query(self, text: str) -> list[float]:
        prefixed = f"query: {text}"
        vector = self.model.encode(
            prefixed,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vector.tolist()
