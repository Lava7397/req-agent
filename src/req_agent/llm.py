"""LiteLLM wrapper for multi-provider support."""

from __future__ import annotations
import json
import os
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
        # Suppress litellm verbose output
        litellm.suppress_debug_info = True

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
                response = self.litellm.completion(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=4096,
                )
                content = response.choices[0].message.content.strip()

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
                    # Add error context for retry
                    messages.append({"role": "assistant", "content": content if 'content' in dir() else ""})
                    messages.append({
                        "role": "user",
                        "content": f"Error: {e}. Please fix and return valid JSON only."
                    })
                    continue

        raise ValueError(f"Failed after {max_retries + 1} attempts: {last_error}")

    def complete_raw(self, messages: list[dict], **kwargs) -> str:
        """Raw completion without JSON parsing."""
        response = self.litellm.completion(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=4096,
            **kwargs,
        )
        return response.choices[0].message.content.strip()
