from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import httpx


@runtime_checkable
class LlmClient(Protocol):
    async def complete(self, messages: list[dict[str, str]]) -> str: ...


class OpenAICompatibleLlm:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        fallback_model: str = "",
        timeout_seconds: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.fallback_model = fallback_model
        self.timeout_seconds = timeout_seconds

    async def complete(self, messages: list[dict[str, str]]) -> str:
        if not self.api_key.strip():
            raise LlmNotConfiguredError("LLM_API_KEY пуст")
        if not self.base_url.strip():
            raise LlmNotConfiguredError("LLM_BASE_URL пуст")
        if not self.model.strip():
            raise LlmNotConfiguredError("LLM_MODEL пуст")

        try:
            return await self._request(self.model, messages)
        except LlmRequestError:
            if self.fallback_model.strip() and self.fallback_model != self.model:
                return await self._request(self.fallback_model, messages)
            raise

    async def _request(self, model: str, messages: list[dict[str, str]]) -> str:
        url = f"{self.base_url}/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise LlmRequestError(str(exc)) from exc
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LlmRequestError("Некорректный ответ LLM") from exc
        if not isinstance(content, str) or not content.strip():
            raise LlmRequestError("Пустой ответ LLM")
        return content.strip()


class StubLlmClient:
    def __init__(self, reply: str = "Короткий ответ по материалам.") -> None:
        self.reply = reply
        self.last_messages: list[dict[str, str]] | None = None

    async def complete(self, messages: list[dict[str, str]]) -> str:
        self.last_messages = messages
        return self.reply


class LlmNotConfiguredError(Exception):
    pass


class LlmRequestError(Exception):
    pass
