"""Rolling FIFO conversation history with separate caps for boosters."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Iterable, Literal


Role = Literal["system", "user", "assistant"]


@dataclass
class HistoryMessage:
    role: Role
    content: str


class RollingHistory:
    """Fixed-capacity FIFO history.

    The ``system`` message is stored separately from the rolling deque so it is
    never evicted. ``maxlen`` bounds only the user/assistant turns.
    """

    def __init__(self, *, system_prompt: str, maxlen: int) -> None:
        if maxlen < 2:
            raise ValueError("history maxlen must be at least 2")
        self._system = HistoryMessage(role="system", content=system_prompt)
        self._buf: Deque[HistoryMessage] = deque(maxlen=maxlen)

    @property
    def maxlen(self) -> int:
        assert self._buf.maxlen is not None
        return self._buf.maxlen

    def set_maxlen(self, new_maxlen: int) -> None:
        """Resize the rolling window, preserving the most recent messages."""
        if new_maxlen < 2:
            raise ValueError("history maxlen must be at least 2")
        new_buf: Deque[HistoryMessage] = deque(self._buf, maxlen=new_maxlen)
        self._buf = new_buf

    def add_user(self, content: str) -> None:
        self._buf.append(HistoryMessage(role="user", content=content))

    def add_assistant(self, content: str) -> None:
        self._buf.append(HistoryMessage(role="assistant", content=content))

    def pop_last_assistant(self) -> HistoryMessage | None:
        """Remove and return the most recent assistant message, if any.

        Used by the Reroll button — we strip the last AI reply before
        regenerating so the new response does not echo it.
        """
        if not self._buf:
            return None
        if self._buf[-1].role != "assistant":
            return None
        return self._buf.pop()

    def messages(self) -> list[dict[str, str]]:
        """Return Groq-compatible chat messages including the system prompt."""
        out: list[dict[str, str]] = [{"role": self._system.role, "content": self._system.content}]
        for m in self._buf:
            out.append({"role": m.role, "content": m.content})
        return out

    def replace_system(self, content: str) -> None:
        self._system = HistoryMessage(role="system", content=content)

    def __len__(self) -> int:
        return len(self._buf)

    def __iter__(self) -> Iterable[HistoryMessage]:
        return iter(self._buf)
