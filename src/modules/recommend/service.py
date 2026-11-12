from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.settings import Settings
from src.data.models import Profile
from src.data.repositories.dialog_states import DialogStateRepository
from src.data.repositories.profiles import ProfileRepository
from src.modules.recommend.format import format_next_step, format_plan
from src.modules.recommend.rules import (
    TEST_CATALOG,
    infer_topic_from_text,
    plan_recommendations,
)
from src.modules.recommend.types import TopicKey

_TOPIC_PAYLOAD_KEY = "last_topic"


@dataclass(frozen=True, slots=True)
class RecommendReply:
    messages: tuple[str, ...]
    next_step: str | None = None


class RecommendService:
    def __init__(
        self,
        *,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory

    async def remember_topic(self, user_id: uuid.UUID, topic_source: str) -> None:
        topic = infer_topic_from_text(topic_source)
        async with self.session_factory() as session:
            repo = DialogStateRepository(session)
            row = await repo.get_or_create(user_id)
            payload = dict(row.payload)
            payload[_TOPIC_PAYLOAD_KEY] = topic
            await repo.set_state(user_id, row.state, payload=payload)
            await session.commit()

    async def recommend_for_user(
        self,
        user_id: uuid.UUID,
        *,
        prefer_route: bool = False,
        topic_override: TopicKey | None = None,
    ) -> RecommendReply:
        async with self.session_factory() as session:
            profile = await ProfileRepository(session).get_by_user_id(user_id)
            dialog = await DialogStateRepository(session).get_by_user_id(user_id)
            topic: TopicKey = "general"
            if topic_override is not None:
                topic = topic_override
            elif dialog is not None:
                raw = dialog.payload.get(_TOPIC_PAYLOAD_KEY)
                if isinstance(raw, str) and raw in (
                    "usn",
                    "marketing",
                    "startup",
                    "finance",
                    "general",
                ):
                    topic = raw  # type: ignore[assignment]

        plan = plan_recommendations(
            profile,
            topic=topic,
            catalog=TEST_CATALOG,
            prefer_route=prefer_route,
        )
        base = self.settings.platform_base_url or "https://example.alfacourse.local"
        messages = format_plan(plan, base_url=base)
        next_step = None if plan.kind == "cold" else format_next_step(plan)
        return RecommendReply(messages=messages, next_step=next_step)

    def recommend_for_profile(
        self,
        profile: Profile | None,
        *,
        topic: TopicKey = "general",
        prefer_route: bool = False,
    ) -> RecommendReply:
        plan = plan_recommendations(
            profile,
            topic=topic,
            catalog=TEST_CATALOG,
            prefer_route=prefer_route,
        )
        base = self.settings.platform_base_url or "https://example.alfacourse.local"
        messages = format_plan(plan, base_url=base)
        next_step = None if plan.kind == "cold" else format_next_step(plan)
        return RecommendReply(messages=messages, next_step=next_step)
