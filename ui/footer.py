"""Shared helpers for the required plain-text footer."""

from __future__ import annotations

import disnake


def footer_line(text: str) -> str:
    # Discord subtext markdown so the footer renders smaller without being an embed.
    return f"-# {text}"


def footer_text_display(text: str) -> disnake.ui.TextDisplay:
    return disnake.ui.TextDisplay(footer_line(text))
