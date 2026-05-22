"""Roleplay engine cog: handles in-channel chat, Reroll, and Continue."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import disnake
from disnake.ext import commands

from core.groq_client import GroqError
from core.prompts import CONTINUE_NUDGE
from core.sessions import RPSession
from ui.rp_message import (
    CONTINUE_BUTTON_ID,
    REROLL_BUTTON_ID,
    STOP_BUTTON_ID,
    build_rp_message_components,
)

if TYPE_CHECKING:
    from bot import RoleplayBot

logger = logging.getLogger(__name__)


MAX_USER_INPUT_CHARS = 4000


class RoleplayCog(commands.Cog):
    def __init__(self, bot: "RoleplayBot") -> None:
        self.bot = bot

    # ---- Free-form user messages ------------------------------------------

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message) -> None:
        if message.author.bot:
            return
        if message.guild is None:
            return
        session = self.bot.sessions.get(message.channel.id)
        if session is None:
            return
        if message.author.id != session.user_id:
            return
        if not message.content or not message.content.strip():
            return

        content = message.content.strip()
        if len(content) > MAX_USER_INPUT_CHARS:
            content = content[:MAX_USER_INPUT_CHARS] + " …[truncated]"

        async with session.lock:
            session.history.add_user(content)
            channel = message.channel
            if not isinstance(channel, disnake.TextChannel):
                return
            await self._disable_previous_buttons(session, channel)
            await self._generate_and_post(session, channel)

    # ---- Reroll / Continue -------------------------------------------------

    @commands.Cog.listener()
    async def on_message_interaction(self, inter: disnake.MessageInteraction) -> None:
        cid = inter.component.custom_id
        if cid not in (REROLL_BUTTON_ID, CONTINUE_BUTTON_ID, STOP_BUTTON_ID):
            return

        session = self.bot.sessions.get(inter.channel_id)
        if session is None:
            await inter.response.send_message(
                "This channel has no active roleplay session.", ephemeral=True
            )
            return
        if inter.user.id != session.user_id:
            await inter.response.send_message(
                "Only the owner of this room can use these buttons.", ephemeral=True
            )
            return

        try:
            if cid == REROLL_BUTTON_ID:
                await self._handle_reroll(inter, session)
            elif cid == CONTINUE_BUTTON_ID:
                await self._handle_continue(inter, session)
            elif cid == STOP_BUTTON_ID:
                await self._handle_stop(inter, session)
        except Exception:
            logger.exception("Error during interaction handling for %s", cid)
            if not inter.response.is_done():
                await inter.response.send_message(
                    "An internal error occurred. Please try again later.", ephemeral=True
                )

    async def _handle_reroll(
        self, inter: disnake.MessageInteraction, session: RPSession
    ) -> None:
        try:
            await inter.response.defer()
        except disnake.HTTPException:
            logger.warning("Could not defer interaction (reroll)")
            return

        async with session.lock:
            session.history.pop_last_assistant()

            channel = inter.channel
            if not isinstance(channel, disnake.TextChannel):
                return

            try:
                await inter.message.delete()
            except (disnake.NotFound, disnake.Forbidden):
                await self._strip_buttons_on_message(inter.message)

            session.last_ai_message_id = None
            await self._generate_and_post(session, channel)

    async def _handle_continue(
        self, inter: disnake.MessageInteraction, session: RPSession
    ) -> None:
        try:
            await inter.response.defer()
        except disnake.HTTPException:
            logger.warning("Could not defer interaction (continue)")
            return

        async with session.lock:
            channel = inter.channel
            if not isinstance(channel, disnake.TextChannel):
                return

            await self._disable_previous_buttons(session, channel)
            session.history.add_user(
                CONTINUE_NUDGE.format(character_name=session.character.name)
            )
            await self._generate_and_post(session, channel)

    async def _handle_stop(
        self, inter: disnake.MessageInteraction, session: RPSession
    ) -> None:
        try:
            await inter.response.defer()
        except disnake.HTTPException:
            logger.warning("Could not defer interaction (stop)")

        async with session.lock:
            self.bot.sessions.remove(session.channel_id)
            await self._strip_buttons_on_message(inter.message)
            await inter.followup.send(
                "**Session stopped.** The bot will no longer respond in this channel.",
                ephemeral=True,
            )

    # ---- Helpers ----------------------------------------------------------

    async def _disable_previous_buttons(
        self, session: RPSession, channel: disnake.TextChannel
    ) -> None:
        """Disable Reroll/Continue on the previous AI message so only the newest
        reply carries the action affordances."""
        if session.last_ai_message_id is None:
            return
        try:
            prev = await channel.fetch_message(session.last_ai_message_id)
        except (disnake.NotFound, disnake.Forbidden, disnake.HTTPException):
            session.last_ai_message_id = None
            return

        await self._strip_buttons_on_message(prev)

    async def _strip_buttons_on_message(self, message: disnake.Message) -> None:
        """Re-render a sent V2 message with the buttons disabled.

        We recover the body text from the message's component tree and rebuild
        the layout with ``disabled=True``. If the body cannot be recovered we
        skip silently rather than wiping the message.
        """
        body = _extract_body_text(message)
        if body is None:
            return
        try:
            await message.edit(
                components=build_rp_message_components(
                    body_text=body,
                    footer_text=self.bot.settings.footer_text,
                    disabled=True,
                ),
            )
        except disnake.HTTPException:
            logger.debug("Could not disable previous RP message buttons", exc_info=True)

    async def _generate_and_post(
        self, session: RPSession, channel: disnake.TextChannel
    ) -> None:
        try:
            async with channel.typing():
                ai_text = await self.bot.groq.generate(session.history.messages())
        except GroqError as exc:
            logger.warning("Groq error during generation: %s", exc)
            await self._post_error(channel, str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected error during Groq generation")
            await self._post_error(channel, f"Unexpected error: {exc}")
            return

        session.history.add_assistant(ai_text)

        msg = await channel.send(
            components=build_rp_message_components(
                body_text=ai_text, footer_text=self.bot.settings.footer_text
            ),
        )
        session.last_ai_message_id = msg.id

    async def _post_error(self, channel: disnake.TextChannel, detail: str) -> None:
        text = "## The scene stalled.\n" f"{detail}\n\n" "Hit **Reroll** to try again."
        await channel.send(
            components=build_rp_message_components(
                body_text=text, footer_text=self.bot.settings.footer_text
            ),
        )


def _extract_body_text(message: disnake.Message) -> str | None:
    """Best-effort: walk a V2 message's component tree to recover its body text.

    Returns the first text-display content that is not the small-print footer
    line (which starts with ``-# `` markdown).
    """
    components = getattr(message, "components", None) or []
    for component in components:
        text = _find_first_body_text(component)
        if text:
            return text
    return None


def _find_first_body_text(component: object) -> str | None:
    content = getattr(component, "content", None)
    if isinstance(content, str) and content.strip() and not content.lstrip().startswith("-# "):
        return content

    children = getattr(component, "children", None) or getattr(component, "components", None)
    if children:
        for child in children:
            found = _find_first_body_text(child)
            if found:
                return found
    return None


def setup(bot: "RoleplayBot") -> None:
    bot.add_cog(RoleplayCog(bot))
