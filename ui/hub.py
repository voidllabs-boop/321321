"""Main control panel (hub) — Components V2, no embeds.

In disnake 2.12, V2 components are sent via the ``components=`` parameter
on ``Messageable.send`` (or interaction responses). The library auto-sets
the ``IS_COMPONENTS_V2`` message flag when v2 components are passed.

There is no ``View`` involved; we just build a list of ``UIComponent``
objects with stable ``custom_id`` values and let cog event listeners
dispatch the clicks.
"""

from __future__ import annotations

import disnake

from ui.footer import footer_line


HUB_CREATE_BUTTON_CUSTOM_ID = "rp:hub:create_room"


def build_hub_components(*, footer_text: str) -> list[disnake.ui.Container]:
    container = disnake.ui.Container(
        disnake.ui.TextDisplay(
            "# AI Roleplay Hub\n"
            "Click the button below to spin up your own **private** roleplay channel "
            "with an Umamusume Pretty Derby character of your choice.\n\n"
            "Once inside, you'll pick:\n"
            "- your role — **Trainer** or **Fan**\n"
            "- which character the AI plays\n\n"
            "Only you and the bot will be able to see the channel."
        ),
        disnake.ui.Separator(),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Create Roleplay Room",
                style=disnake.ButtonStyle.primary,
                custom_id=HUB_CREATE_BUTTON_CUSTOM_ID,
            )
        ),
        disnake.ui.TextDisplay(footer_line(footer_text)),
    )
    return [container]
