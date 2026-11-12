from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

AudienceKey = Literal["newbie", "coffee_usn", "solo_marketing"]
TopicKey = Literal["usn", "marketing", "startup", "finance", "general"]


@dataclass(frozen=True, slots=True)
class CatalogItem:
    material_id: str
    title: str
    slug: str
    is_paid: bool
    benefit: str
    reason: str
    topics: frozenset[str]
    stages: frozenset[str]
    audiences: frozenset[str]
    route_order: int | None = None


@dataclass(frozen=True, slots=True)
class RecommendationPlan:
    kind: Literal["cold", "items", "route"]
    free: CatalogItem | None = None
    paid: CatalogItem | None = None
    route: tuple[CatalogItem, ...] = ()
    cold_titles: tuple[str, ...] = ()
    next_step_days: int = 3
