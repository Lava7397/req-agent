"""LLM client with fallback support."""

from __future__ import annotations
import json
import os
import time
import httpx
from typing import Type, TypeVar
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

# Fallback models ordered by reliability
FALLBACK_MODELS = [
    "openrouter/meta-llama/llama-3.1-8b-instruct",
    "openrouter/qwen/qwen3-coder",
    "openrouter/meta-llama/llama-3.3-70b-instruct",
]


class LLMClient:
    """LLM client with direct HTTP fallback (bypasses litellm 403 issues)."""

    def __init__(self, model: str | None = None, temperature: float = 0.3):
        self.model = model or os.getenv("DEFAULT_MODEL", "openrouter/meta-llama/llama-3.1-8b-instruct")
        self.temperature = temperature
        self.api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        self.base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    def _call_openai_compat(self, messages: list[dict], model: str) -> str:
        """Direct HTTP call to OpenAI-compatible API (avoids litellm 403 issue)."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        # OpenRouter specific headers
        if "openrouter" in model:
            headers["HTTP-Referer"] = "https://github.com/Lava7397/req-agent"
            model = model.replace("openrouter/", "")

        payload = {
            "model": model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": 4096,
        }

        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    def _call_with_fallback(self, messages: list[dict]) -> str:
        """Try primary model, then fallback models on failure."""
        models_to_try = [self.model] + [m for m in FALLBACK_MODELS if m != self.model]

        last_error = None
        for model in models_to_try:
            for attempt in range(3):
                try:
                    return self._call_openai_compat(messages, model)
                except httpx.HTTPStatusError as e:
                    last_error = e
                    status = e.response.status_code
                    if status in (403, 429, 500, 502, 503):
                        time.sleep(2 ** attempt)
                        continue
                    # Other errors: try next model
                    break
                except Exception as e:
                    last_error = e
                    time.sleep(2 ** attempt)
                    continue

        raise Exception(f"All models failed. Last error: {last_error}")

    def _clean_json(self, text: str) -> str:
        """Clean common JSON issues from LLM output."""
        import re
        # Fix invalid \uXXXX escapes (incomplete unicode)
        text = re.sub(r'\\u[0-9a-fA-F]{0,3}(?![0-9a-fA-F])', '', text)
        # Fix trailing commas
        text = re.sub(r',\s*([\]}])', r'\1', text)
        # Fix single quotes used as strings (naive but helps)
        # text = text.replace("'", '"')
        return text

    def complete(
        self,
        system: str,
        user: str,
        response_format: Type[T] | None = None,
        max_retries: int = 2,
    ) -> str | T:
        """Call LLM and optionally parse into Pydantic model."""
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                content = self._call_with_fallback(messages)

                # Strip markdown code fences
                if content.startswith("```"):
                    lines = content.split("\n")
                    content = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

                if response_format:
                    content = self._clean_json(content)
                    data = json.loads(content)
                    return response_format.model_validate(data)
                return content

            except (json.JSONDecodeError, ValidationError) as e:
                last_error = e
                if attempt < max_retries:
                    messages.append({"role": "assistant", "content": content if 'content' in dir() else ""})
                    messages.append({"role": "user", "content": f"JSON parse error: {e}. Return valid JSON only, no unicode escapes."})
                    continue

        raise ValueError(f"Failed after {max_retries + 1} attempts: {last_error}")
