"""LiteLLM wrapper for multi-provider support."""

from __future__ import annotations
import json
import os
import time
from typing import Type, TypeVar
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv

load_dotenv()

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """Thin wrapper around litellm for structured JSON output."""

    def __init__(self, model: str | None = None, temperature: float = 0.3):
        import litellm
        self.litellm = litellm
        self.model = model or os.getenv("DEFAULT_MODEL", "gpt-4o")
        self.temperature = temperature
        litellm.suppress_debug_info = True

    def _call(self, messages: list[dict], max_retries: int = 3) -> str:
        """Call LLM with retry on transient errors."""
        last_error = None
        for attempt in range(max_retries):
            try:
                response = self.litellm.completion(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=4096,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                last_error = e
                error_str = str(e)
                # Retry on transient errors (403, 429, 500, timeout)
                if any(code in error_str for code in ["403", "429", "500", "timeout", "Timeout"]):
                    wait = 2 ** attempt
                    time.sleep(wait)
                    continue
                raise
        raise last_error

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
                content = self._call(messages, max_retries=3)

                # Strip markdown code fences if present
                if content.startswith("```"):
                    lines = content.split("\n")
                    content = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

                if response_format:
                    data = json.loads(content)
                    return response_format.model_validate(data)
                return content

            except (json.JSONDecodeError, ValidationError) as e:
                last_error = e
                if attempt < max_retries:
                    messages.append({"role": "assistant", "content": content if 'content' in dir() else ""})
                    messages.append({
                        "role": "user",
                        "content": f"Error: {e}. Please fix and return valid JSON only."
                    })
                    continue

        raise ValueError(f"Failed after {max_retries + 1} attempts: {last_error}")

    def complete_raw(self, messages: list[dict], **kwargs) -> str:
        """Raw completion without JSON parsing."""
        return self._call(messages)
