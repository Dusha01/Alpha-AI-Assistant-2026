from __future__ import annotations

import uuid

from src.data.models import Profile
from src.data.models.enums import BusinessStage, TaxMode
from src.handlers.text import COPY
from src.modules.recommend.format import format_next_step, format_plan
from src.modules.recommend.rules import (
    TEST_CATALOG,
    first_recommended_title,
    plan_recommendations,
)


def test_empty_profile_is_cold() -> None:
    plan = plan_recommendations(None)
    assert plan.kind == "cold"
    messages = format_plan(plan, base_url="https://example.test")
    assert len(messages) == 1
    listing = ", ".join(f"«{t}»" for t in plan.cold_titles)
    assert messages[0] == COPY["recommend_cold"].format(список=listing)


def test_three_profiles_get_distinct_first_materials() -> None:
    newbie = Profile(
        user_id=uuid.uuid4(),
        stage=BusinessStage.PLANNING,
    )
    coffee = Profile(
        user_id=uuid.uuid4(),
        sphere="Кофейня",
        stage=BusinessStage.LT_YEAR,
        mode=TaxMode.USN,
    )
    marketing = Profile(
        user_id=uuid.uuid4(),
        sphere="Соло-маркетинг",
        stage=BusinessStage.GT_YEAR,
    )

    titles = {
        first_recommended_title(
            plan_recommendations(newbie, topic="startup", catalog=TEST_CATALOG)
        ),
        first_recommended_title(plan_recommendations(coffee, topic="usn", catalog=TEST_CATALOG)),
        first_recommended_title(
            plan_recommendations(marketing, topic="marketing", catalog=TEST_CATALOG)
        ),
    }
    assert titles == {
        "Азы финансовой грамотности",
        "Шаблон учёта доходов на УСН",
        "Маркетинг для соло-предпринимателя",
    }


def test_paid_recommendation_one_benefit_and_no_lesson_body() -> None:
    profile = Profile(
        user_id=uuid.uuid4(),
        sphere="Кофейня",
        stage=BusinessStage.LT_YEAR,
        mode=TaxMode.USN,
    )
    plan = plan_recommendations(profile, topic="usn", catalog=TEST_CATALOG)
    messages = format_plan(plan, base_url="https://example.test")
    paid = next(m for m in messages if "Если хотите разобраться глубже" in m)
    assert plan.paid is not None
    assert plan.paid.benefit in paid
    assert "HtmlContent" not in paid
    assert paid.count("https://") == 1


def test_next_step_is_single_prompt() -> None:
    profile = Profile(
        user_id=uuid.uuid4(),
        sphere="Кофейня",
        stage=BusinessStage.LT_YEAR,
        mode=TaxMode.USN,
    )
    plan = plan_recommendations(profile, topic="usn", catalog=TEST_CATALOG)
    step = format_next_step(plan)
    assert step == COPY["next_step"].format(N=3)


def test_links_include_utm() -> None:
    profile = Profile(
        user_id=uuid.uuid4(),
        sphere="Кофейня",
        stage=BusinessStage.LT_YEAR,
        mode=TaxMode.USN,
    )
    plan = plan_recommendations(profile, topic="usn", catalog=TEST_CATALOG)
    text = "\n".join(format_plan(plan, base_url="https://example.test"))
    assert "utm_source=tg_bot" in text
