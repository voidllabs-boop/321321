"""Components V2 layout for every AI roleplay reply: Reroll + Continue."""

from __future__ import annotations

import disnake

from ui.footer import footer_line


REROLL_BUTTON_ID = "rp:msg:reroll"
CONTINUE_BUTTON_ID = "rp:msg:continue"
STOP_BUTTON_ID = "rp:msg:stop"


def build_rp_message_components(
    *,
    body_text: str,
    footer_text: str,
    disabled: bool = False,
) -> list[disnake.ui.Container]:
    container = disnake.ui.Container(
        disnake.ui.TextDisplay(body_text),
        disnake.ui.Separator(),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Reroll",
                style=disnake.ButtonStyle.secondary,
                custom_id=REROLL_BUTTON_ID,
                disabled=disabled,
            ),
            disnake.ui.Button(
                label="Continue",
                style=disnake.ButtonStyle.primary,
                custom_id=CONTINUE_BUTTON_ID,
                disabled=disabled,
            ),
            disnake.ui.Button(
                label="Stop",
                style=disnake.ButtonStyle.danger,
                custom_id=STOP_BUTTON_ID,
                disabled=disabled,
            ),
        ),
        disnake.ui.TextDisplay(footer_line(footer_text)),
    )
    return [container]
