"""In-memory store of active roleplay sessions, keyed by channel id."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Optional

from core.characters import Character
from core.history import RollingHistory


@dataclass
class RPSession:
    channel_id: int
    user_id: int
    guild_id: int
    role: str  # "trainer" | "fan"
    character: Character
    history: RollingHistory
    user_display_name: str
    last_ai_message_id: Optional[int] = None
    # Per-channel lock so reroll/continue/incoming user messages do not race.
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class SessionStore:
    def __init__(self) -> None:
        self._by_channel: dict[int, RPSession] = {}

    def add(self, session: RPSession) -> None:
        self._by_channel[session.channel_id] = session

    def get(self, channel_id: int) -> Optional[RPSession]:
        return self._by_channel.get(channel_id)

    def remove(self, channel_id: int) -> Optional[RPSession]:
        return self._by_channel.pop(channel_id, None)

    def has_active_session_for_user(self, user_id: int) -> bool:
        return any(s.user_id == user_id for s in self._by_channel.values())

    def channels_for_user(self, user_id: int) -> list[int]:
        return [cid for cid, s in self._by_channel.items() if s.user_id == user_id]

    def __contains__(self, channel_id: object) -> bool:
        return channel_id in self._by_channel
