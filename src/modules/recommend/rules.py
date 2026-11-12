from __future__ import annotations

from src.data.models import Profile
from src.data.models.enums import BusinessStage, TaxMode
from src.modules.profile.labels import is_profile_empty
from src.modules.recommend.types import AudienceKey, CatalogItem, RecommendationPlan, TopicKey

_ALL_STAGES = frozenset({"planning", "lt_year", "gt_year"})

NEWBIE_ROUTE_IDS = ("fin-gram", "biz-plan-free", "first-checklist")
COFFEE_ROUTE_IDS = ("usn-income-template", "coffee-unit-economy", "usn-course-paid")
MARKETING_ROUTE_IDS = ("marketing-basics", "content-plan-free", "marketing-course-paid")

TEST_CATALOG: tuple[CatalogItem, ...] = (
    CatalogItem(
        material_id="fin-gram",
        title="Азы финансовой грамотности",
        slug="azy-finansovoj-gramotnosti",
        is_paid=False,
        benefit="разобраться с деньгами в бизнесе с нуля",
        reason="вы только планируете запуск — начните с базы по финансам",
        topics=frozenset({"startup", "finance", "general"}),
        stages=frozenset({"planning"}),
        audiences=frozenset({"newbie"}),
        route_order=1,
    ),
    CatalogItem(
        material_id="biz-plan-free",
        title="Как составить бизнес-план",
        slug="biznes-plan",
        is_paid=False,
        benefit="собрать план без лишней теории",
        reason="поможет структурировать идею перед стартом",
        topics=frozenset({"startup", "general"}),
        stages=frozenset({"planning"}),
        audiences=frozenset({"newbie"}),
        route_order=2,
    ),
    CatalogItem(
        material_id="first-checklist",
        title="Чек-лист первых шагов предпринимателя",
        slug="first-steps",
        is_paid=False,
        benefit="не забыть регистрацию и обязательные шаги",
        reason="закрепит порядок действий на старте",
        topics=frozenset({"startup", "general"}),
        stages=frozenset({"planning"}),
        audiences=frozenset({"newbie"}),
        route_order=3,
    ),
    CatalogItem(
        material_id="usn-income-template",
        title="Шаблон учёта доходов на УСН",
        slug="usn-income-template",
        is_paid=False,
        benefit="вести учёт доходов самостоятельно на первом году",
        reason="у вас кофейня на УСН — шаблон под ваш режим и стадию",
        topics=frozenset({"usn", "finance"}),
        stages=frozenset({"lt_year", "gt_year"}),
        audiences=frozenset({"coffee_usn"}),
        route_order=1,
    ),
    CatalogItem(
        material_id="coffee-unit-economy",
        title="Юнит-экономика кофейни",
        slug="unit-coffee",
        is_paid=False,
        benefit="понять маржу и точку безубыточности",
        reason="релевантно для кофейни меньше года",
        topics=frozenset({"finance", "general"}),
        stages=frozenset({"lt_year"}),
        audiences=frozenset({"coffee_usn"}),
        route_order=2,
    ),
    CatalogItem(
        material_id="usn-course-paid",
        title="Курс «УСН без ошибок»",
        slug="usn-course",
        is_paid=True,
        benefit="разобрать типовые ошибки учёта и отчётности",
        reason="",
        topics=frozenset({"usn"}),
        stages=_ALL_STAGES,
        audiences=frozenset({"coffee_usn"}),
        route_order=3,
    ),
    CatalogItem(
        material_id="marketing-basics",
        title="Маркетинг для соло-предпринимателя",
        slug="marketing-solo",
        is_paid=False,
        benefit="системно выстроить продвижение без отдела",
        reason="вы хотите освоить маркетинг — начните с основ",
        topics=frozenset({"marketing"}),
        stages=_ALL_STAGES,
        audiences=frozenset({"solo_marketing"}),
        route_order=1,
    ),
    CatalogItem(
        material_id="content-plan-free",
        title="Контент-план на месяц",
        slug="content-plan",
        is_paid=False,
        benefit="вести соцсети по понятному плану",
        reason="следующий шаг после основ маркетинга",
        topics=frozenset({"marketing"}),
        stages=_ALL_STAGES,
        audiences=frozenset({"solo_marketing"}),
        route_order=2,
    ),
    CatalogItem(
        material_id="marketing-course-paid",
        title="Курс «Продвижение на практике»",
        slug="marketing-paid",
        is_paid=True,
        benefit="отработать каналы привлечения на реальных кейсах",
        reason="",
        topics=frozenset({"marketing"}),
        stages=_ALL_STAGES,
        audiences=frozenset({"solo_marketing"}),
        route_order=3,
    ),
)

_COLD_START = (
    "Азы финансовой грамотности",
    "Как составить бизнес-план",
    "Чек-лист первых шагов предпринимателя",
)


def infer_topic_from_text(text: str) -> TopicKey:
    lowered = text.lower()
    if any(k in lowered for k in ("усн", "налог", "учёт", "учет", "доход")):
        return "usn"
    if any(k in lowered for k in ("маркетинг", "реклам", "продвижен", "контент", "smm")):
        return "marketing"
    if any(k in lowered for k in ("старт", "запуск", "открыть", "регистрац")):
        return "startup"
    if any(k in lowered for k in ("финанс", "деньг", "кредит", "бюджет")):
        return "finance"
    return "general"


def detect_audience(profile: Profile) -> AudienceKey | None:
    if is_profile_empty(profile):
        return None
    sphere = (profile.sphere or "").lower()
    if profile.mode == TaxMode.USN and any(w in sphere for w in ("кофе", "кофейн", "coffee")):
        return "coffee_usn"
    if profile.stage == BusinessStage.PLANNING and (not sphere or profile.sphere is None):
        return "newbie"
    if any(w in sphere for w in ("маркетинг", "smm", "продвижен", "контент")):
        return "solo_marketing"
    if profile.stage == BusinessStage.PLANNING:
        return "newbie"
    return None


def _stage_key(profile: Profile) -> str:
    if profile.stage is None:
        return "planning"
    return profile.stage.value


def _by_id(catalog: tuple[CatalogItem, ...]) -> dict[str, CatalogItem]:
    return {item.material_id: item for item in catalog}


def _route_for_audience(
    catalog: tuple[CatalogItem, ...], audience: AudienceKey
) -> tuple[CatalogItem, ...]:
    ids = {
        "newbie": NEWBIE_ROUTE_IDS,
        "coffee_usn": COFFEE_ROUTE_IDS,
        "solo_marketing": MARKETING_ROUTE_IDS,
    }[audience]
    items = _by_id(catalog)
    return tuple(items[mid] for mid in ids)


def _pick_free(
    catalog: tuple[CatalogItem, ...],
    *,
    topic: TopicKey,
    stage: str,
    audience: AudienceKey | None,
) -> CatalogItem | None:
    candidates: list[tuple[int, CatalogItem]] = []
    for item in catalog:
        if item.is_paid:
            continue
        if topic not in item.topics and "general" not in item.topics:
            continue
        if stage not in item.stages and item.stages != _ALL_STAGES:
            continue
        if audience and audience in item.audiences:
            candidates.append((2, item))
        else:
            candidates.append((1, item))
    if not candidates:
        return None
    candidates.sort(key=lambda pair: (-pair[0], pair[1].route_order or 99))
    return candidates[0][1]


def _pick_paid(
    catalog: tuple[CatalogItem, ...],
    *,
    topic: TopicKey,
    audience: AudienceKey | None,
    exclude_id: str | None,
) -> CatalogItem | None:
    for item in catalog:
        if not item.is_paid:
            continue
        if item.material_id == exclude_id:
            continue
        if topic not in item.topics:
            continue
        if audience and audience not in item.audiences:
            continue
        return item
    for item in catalog:
        if item.is_paid and item.material_id != exclude_id:
            if audience is None or audience in item.audiences:
                return item
    return None


def plan_recommendations(
    profile: Profile | None,
    *,
    topic: TopicKey = "general",
    catalog: tuple[CatalogItem, ...] = TEST_CATALOG,
    prefer_route: bool = False,
) -> RecommendationPlan:
    if profile is None or is_profile_empty(profile):
        return RecommendationPlan(kind="cold", cold_titles=_COLD_START)

    audience = detect_audience(profile)
    stage = _stage_key(profile)

    if prefer_route and audience is not None:
        route = _route_for_audience(catalog, audience)
        return RecommendationPlan(kind="route", route=route)

    free = _pick_free(catalog, topic=topic, stage=stage, audience=audience)
    paid_topic = topic
    if topic == "general" and audience == "coffee_usn":
        paid_topic = "usn"
    elif topic == "general" and audience == "solo_marketing":
        paid_topic = "marketing"
    elif topic == "general":
        paid_topic = "startup"
    paid = _pick_paid(
        catalog,
        topic=paid_topic,
        audience=audience,
        exclude_id=free.material_id if free else None,
    )

    if audience is not None and free is None and paid is None:
        route = _route_for_audience(catalog, audience)
        return RecommendationPlan(kind="route", route=route)

    return RecommendationPlan(kind="items", free=free, paid=paid)


def first_recommended_title(plan: RecommendationPlan) -> str | None:
    if plan.kind == "cold":
        return plan.cold_titles[0] if plan.cold_titles else None
    if plan.kind == "route" and plan.route:
        return plan.route[0].title
    if plan.free is not None:
        return plan.free.title
    if plan.paid is not None:
        return plan.paid.title
    return None
