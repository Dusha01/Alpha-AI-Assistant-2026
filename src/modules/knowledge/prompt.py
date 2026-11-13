from __future__ import annotations

from src.modules.knowledge.text import benefit_one_liner
from src.modules.knowledge.types import SearchHit

_SYSTEM_PROMPT = (
    "Вы помощник «Альфа-Курса». Отвечайте только по приведённым фрагментам материалов. "
    "Не выдумывайте факты. Ответ — 3–4 короткие строки, обращение на «вы». "
    "Ссылку на материал добавит система отдельной строкой — в ответе ссылку не повторяйте. "
    "Платные материалы не пересказывайте: одна фраза о пользе, без текста уроков. "
    "Другие банки не называйте и не сравнивайте."
)


def build_llm_messages(question: str, hits: tuple[SearchHit, ...]) -> list[dict[str, str]]:
    rag_hits = [hit for hit in hits if hit.include_in_rag]
    fragments: list[str] = []
    for index, hit in enumerate(rag_hits, start=1):
        if hit.is_paid:
            body = benefit_one_liner(hit.body)
            fragments.append(
                f"[{index}] «{hit.title}» (платный материал)\n"
                f"Польза: {body}\n"
                f"Ссылка: {hit.url or 'нет'}"
            )
        else:
            fragments.append(
                f"[{index}] «{hit.title}»\nФрагмент: {hit.body[:1200]}\nСсылка: {hit.url or 'нет'}"
            )
    user_prompt = f"Вопрос пользователя: {question}\n\nФрагменты материалов:\n" + "\n\n".join(
        fragments
    )
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


def prompt_contains_forbidden_data(messages: list[dict[str, str]], forbidden: str) -> bool:
    joined = "\n".join(message["content"] for message in messages)
    return forbidden in joined
