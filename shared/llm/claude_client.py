import json
import re
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from shared.config import settings
from shared.logger import logger


class LLMClient:
    """Unified LLM client — supports Anthropic Claude and any OpenAI-compatible API (Groq, Ollama, etc.)."""

    def __init__(self) -> None:
        self._backend = settings.LLM_BACKEND  # "claude" | "openai_compat"
        self.fast_model = settings.CLAUDE_MODEL_FAST
        self.smart_model = settings.CLAUDE_MODEL_SMART

    def _get_anthropic(self):
        from anthropic import AsyncAnthropic
        return AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    def _get_openai(self):
        from openai import AsyncOpenAI
        return AsyncOpenAI(
            api_key=settings.OPENAI_COMPAT_API_KEY,
            base_url=settings.OPENAI_COMPAT_BASE_URL,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=20))
    async def complete(
        self,
        system: str,
        user: str,
        model: str | None = None,
        max_tokens: int = 1024,
        cache_system: bool = True,
    ) -> str:
        if self._backend == "claude":
            return await self._complete_claude(system, user, model, max_tokens, cache_system)
        return await self._complete_openai_compat(system, user, model, max_tokens)

    async def _complete_claude(self, system: str, user: str, model: str | None, max_tokens: int, cache_system: bool) -> str:
        model = model or self.fast_model
        system_block: list[dict[str, Any]] = [{"type": "text", "text": system}]
        if cache_system:
            system_block[0]["cache_control"] = {"type": "ephemeral"}
        client = self._get_anthropic()
        resp = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_block,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(b.text for b in resp.content if hasattr(b, "text")).strip()

    async def _complete_openai_compat(self, system: str, user: str, model: str | None, max_tokens: int) -> str:
        model = model or settings.OPENAI_COMPAT_MODEL
        client = self._get_openai()
        resp = await client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return (resp.choices[0].message.content or "").strip()

    async def complete_json(
        self,
        system: str,
        user: str,
        model: str | None = None,
        max_tokens: int = 1024,
    ) -> dict[str, Any]:
        raw = await self.complete(
            system=system + "\n\nRespond ONLY with valid JSON. No prose, no markdown fences.",
            user=user,
            model=model,
            max_tokens=max_tokens,
        )
        return _parse_json(raw)


def _parse_json(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", raw, re.DOTALL)
    if fence:
        raw = fence.group(1)
    else:
        m = re.search(r"(\{.*\}|\[.*\])", raw, re.DOTALL)
        if m:
            raw = m.group(1)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try to repair truncated JSON by closing unclosed brackets
        try:
            repaired = raw.rstrip().rstrip(",")
            # Strip trailing commas before closing brackets (e.g. [...,] or {...,})
            repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
            repaired += "]" * max(0, repaired.count("[") - repaired.count("]"))
            repaired += "}" * max(0, repaired.count("{") - repaired.count("}"))
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass
        # LLM put unescaped quotes inside string values — replace curly quotes as fallback
        try:
            fixed = re.sub(r'(?<=: ")([^"]*)"([^"]*)"([^"]*?)(?=")', r'\1«\2»\3', raw)
            return json.loads(fixed)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM JSON: {} | raw: {!r}", e, raw[:500])
            raise


# Global singleton
ClaudeClient = LLMClient  # backwards-compat alias
claude = LLMClient()
