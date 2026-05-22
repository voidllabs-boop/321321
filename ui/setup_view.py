"""Per-channel setup panel: role + character selection with pagination.

State is stored externally (in the ``SetupRPCog``). This module is pure
view construction — it converts a ``SetupState`` snapshot into a list of
Components V2 ``Container``\\s.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import disnake

from core.characters import CHARACTERS_BY_KEY, chunk_characters, total_pages
from core.prompts import ROLE_FAN, ROLE_TRAINER
from ui.footer import footer_line


SETUP_ROLE_SELECT_ID = "rp:setup:role"
SETUP_CHAR_SELECT_ID = "rp:setup:char"
SETUP_PREV_PAGE_ID = "rp:setup:prev_page"
SETUP_NEXT_PAGE_ID = "rp:setup:next_page"
SETUP_START_ID = "rp:setup:start"


@dataclass
class SetupState:
    owner_id: int
    channel_id: int
    page: int = 0
    role: Optional[str] = None
    character_key: Optional[str] = None
    locked: bool = False
    # Set by the cog once the setup message has been posted, so it can edit it.
    message_id: Optional[int] = None


def _role_options(current: Optional[str]) -> list[disnake.SelectOption]:
    return [
        disnake.SelectOption(
            label="Trainer",
            value=ROLE_TRAINER,
            description="You are the character's Trainer at Tracen Academy.",
            default=current == ROLE_TRAINER,
        ),
        disnake.SelectOption(
            label="Fan",
            value=ROLE_FAN,
            description="You are a fan meeting the character in person.",
            default=current == ROLE_FAN,
        ),
    ]


def _character_options(page: int, current: Optional[str]) -> list[disnake.SelectOption]:
    pages = chunk_characters(per_page=25)
    page = max(0, min(page, len(pages) - 1))
    items = pages[page]
    options: list[disnake.SelectOption] = []
    for c in items:
        description = c.profile if len(c.profile) <= 90 else c.profile[:89] + "…"
        options.append(
            disnake.SelectOption(
                label=c.name,
                value=c.key,
                description=description,
                default=c.key == current,
            )
        )
    return options


def build_setup_components(
    state: SetupState,
    *,
    footer_text: str,
) -> list[disnake.ui.Container]:
    pages = chunk_characters(per_page=25)
    page = max(0, min(state.page, len(pages) - 1))
    page_count = total_pages(per_page=25)

    role_label = state.role.capitalize() if state.role else "*not chosen*"
    if state.character_key and state.character_key in CHARACTERS_BY_KEY:
        char_label = CHARACTERS_BY_KEY[state.character_key].name
    else:
        char_label = "*not chosen*"

    ready = bool(state.role and state.character_key)
    locked = state.locked

    header = disnake.ui.TextDisplay(
        "# Roleplay Setup\n"
        "Pick your **role** and the **character** the AI will play. "
        "Hit **Start Roleplay** when you're ready.\n\n"
        f"**Role:** {role_label}\n"
        f"**Character:** {char_label}\n"
        f"**Character page:** {page + 1} / {page_count}"
    )

    role_select = disnake.ui.StringSelect(
        custom_id=SETUP_ROLE_SELECT_ID,
        placeholder="Choose your role…",
        min_values=1,
        max_values=1,
        options=_role_options(state.role),
        disabled=locked,
    )
    char_select = disnake.ui.StringSelect(
        custom_id=SETUP_CHAR_SELECT_ID,
        placeholder=f"Pick a character — page {page + 1}/{page_count}",
        min_values=1,
        max_values=1,
        options=_character_options(page, state.character_key),
        disabled=locked,
    )

    prev_btn = disnake.ui.Button(
        label="◀ Page",
        style=disnake.ButtonStyle.secondary,
        custom_id=SETUP_PREV_PAGE_ID,
        disabled=locked or page == 0,
    )
    next_btn = disnake.ui.Button(
        label="Page ▶",
        style=disnake.ButtonStyle.secondary,
        custom_id=SETUP_NEXT_PAGE_ID,
        disabled=locked or page >= page_count - 1,
    )
    start_btn = disnake.ui.Button(
        label="Start Roleplay",
        style=disnake.ButtonStyle.success,
        custom_id=SETUP_START_ID,
        disabled=locked or not ready,
    )

    container = disnake.ui.Container(
        header,
        disnake.ui.Separator(),
        disnake.ui.ActionRow(role_select),
        disnake.ui.ActionRow(char_select),
        disnake.ui.Separator(),
        disnake.ui.ActionRow(prev_btn, next_btn, start_btn),
        disnake.ui.TextDisplay(footer_line(footer_text)),
    )
    return [container]


SETUP_CUSTOM_IDS = frozenset(
    {
        SETUP_ROLE_SELECT_ID,
        SETUP_CHAR_SELECT_ID,
        SETUP_PREV_PAGE_ID,
        SETUP_NEXT_PAGE_ID,
        SETUP_START_ID,
    }
)
