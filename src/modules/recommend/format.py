from __future__ import annotations

from src.handlers.text import COPY
from src.modules.knowledge.catalog import material_url
from src.modules.recommend.types import CatalogItem, RecommendationPlan
from src.modules.recommend.utm import with_utm


def _link(base_url: str, item: CatalogItem) -> str:
    raw = material_url(base_url, item.slug) or item.slug
    return with_utm(raw, campaign="recommend", content=item.slug)


def format_plan(plan: RecommendationPlan, *, base_url: str) -> tuple[str, ...]:
    if plan.kind == "cold":
        listing = ", ".join(f"«{title}»" for title in plan.cold_titles)
        return (COPY["recommend_cold"].format(список=listing),)

    if plan.kind == "route" and plan.route:
        lines = [
            COPY["recommend_route"].format(
                материал_1=plan.route[0].title,
                зачем_1=plan.route[0].reason or plan.route[0].benefit,
                материал_2=plan.route[1].title,
                зачем_2=plan.route[1].reason or plan.route[1].benefit,
                материал_3=plan.route[2].title,
                зачем_3=plan.route[2].reason or plan.route[2].benefit,
            )
        ]
        return tuple(lines)

    messages: list[str] = []
    if plan.free is not None:
        messages.append(
            COPY["recommend_free"].format(
                имя_материала=plan.free.title,
                причина=plan.free.reason,
                ссылка=_link(base_url, plan.free),
            )
        )
    if plan.paid is not None:
        messages.append(
            COPY["recommend_paid"].format(
                имя_материала=plan.paid.title,
                польза_в_одной_фразе=plan.paid.benefit,
                ссылка=_link(base_url, plan.paid),
            )
        )
    return tuple(messages)


def format_next_step(plan: RecommendationPlan) -> str:
    return COPY["next_step"].format(N=plan.next_step_days)
