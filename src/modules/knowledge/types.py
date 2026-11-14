from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FactHit:
    body: str
    score: float


@dataclass(frozen=True, slots=True)
class SearchHit:
    title: str
    url: str | None
    body: str
    is_paid: bool
    score: float
    include_in_rag: bool = True


@dataclass(frozen=True, slots=True)
class ChunkDraft:
    material_type: str
    material_id: uuid.UUID
    chunk_index: int
    title: str
    url: str | None
    is_paid: bool
    body: str
    include_in_rag: bool
