"""Thin async wrapper around the official Groq SDK."""

from __future__ import annotations

import asyncio
import logging
from typing import Sequence

from groq import AsyncGroq
from groq import APIConnectionError, APIError, APIStatusError, APITimeoutError

logger = logging.getLogger(__name__)


class GroqError(Exception):
    """Raised when a Groq generation cannot be completed."""


class GroqClient:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float = 60.0,
    ) -> None:
        self._client = AsyncGroq(api_key=api_key, timeout=timeout_seconds)
        self._model = model
        self._timeout = timeout_seconds

    @property
    def model(self) -> str:
        return self._model

    async def aclose(self) -> None:
        try:
            await self._client.close()
        except Exception:  # noqa: BLE001
            logger.exception("Failed to close Groq client cleanly")

    async def generate(
        self,
        messages: Sequence[dict[str, str]],
        *,
        temperature: float = 0.85,
        top_p: float = 0.95,
        max_tokens: int = 1024,
    ) -> str:
        """Call Groq chat completions and return the assistant text.

        Wraps the most common Groq SDK errors into a single ``GroqError`` so the
        Discord side does not need to know SDK internals.
        """
        try:
            response = await asyncio.wait_for(
                self._client.chat.completions.create(
                    model=self._model,
                    messages=list(messages),
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                ),
                timeout=self._timeout + 5.0,
            )
        except asyncio.TimeoutError as exc:
            raise GroqError("Groq request timed out. Please try again.") from exc
        except APITimeoutError as exc:
            raise GroqError("Groq request timed out. Please try again.") from exc
        except APIConnectionError as exc:
            raise GroqError("Could not reach Groq. Check connectivity and try again.") from exc
        except APIStatusError as exc:
            raise GroqError(
                f"Groq returned an error ({exc.status_code}). Please try again later."
            ) from exc
        except APIError as exc:
            raise GroqError(f"Groq API error: {exc}") from exc

        try:
            choice = response.choices[0]
            content = choice.message.content or ""
        except (AttributeError, IndexError) as exc:
            raise GroqError("Groq returned an unexpected payload.") from exc

        content = content.strip()
        if not content:
            raise GroqError("Groq returned an empty response.")
        return content
