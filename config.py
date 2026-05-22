"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


def _parse_int_list(raw: str) -> list[int]:
    out: list[int] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            out.append(int(chunk))
        except ValueError:
            continue
    return out


def _parse_optional_int(raw: Optional[str]) -> Optional[int]:
    if not raw:
        return None
    raw = raw.strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


@dataclass(frozen=True)
class Settings:
    discord_token: str
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"
    dev_guild_ids: list[int] = field(default_factory=list)
    rp_category_id: Optional[int] = None
    groq_timeout_seconds: float = 60.0

    # Memory limits (rolling FIFO window of conversation turns)
    standard_memory_limit: int = 50
    booster_memory_limit: int = 200

    # Footer required by spec
    footer_text: str = "Made by United Servers of Sovereign Republics"


def load_settings() -> Settings:
    token = os.environ.get("DISCORD_TOKEN", "").strip()
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not token:
        raise RuntimeError("DISCORD_TOKEN is not set. Copy .env.example to .env and fill it in.")
    if not groq_key:
        raise RuntimeError("GROQ_API_KEY is not set. Copy .env.example to .env and fill it in.")

    timeout_raw = os.environ.get("GROQ_TIMEOUT_SECONDS", "60").strip() or "60"
    try:
        timeout = float(timeout_raw)
    except ValueError:
        timeout = 60.0

    return Settings(
        discord_token=token,
        groq_api_key=groq_key,
        groq_model=os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
        or "llama-3.3-70b-versatile",
        dev_guild_ids=_parse_int_list(os.environ.get("DEV_GUILD_IDS", "")),
        rp_category_id=_parse_optional_int(os.environ.get("RP_CATEGORY_ID")),
        groq_timeout_seconds=timeout,
    )
