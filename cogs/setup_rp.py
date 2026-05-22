"""`/setup_rp` slash command + private channel creation + setup flow."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import disnake
from disnake.ext import commands

from core.characters import CHARACTERS_BY_KEY, total_pages
from core.history import RollingHistory
from core.prompts import build_session_prompt
from core.sessions import RPSession
from ui.hub import HUB_CREATE_BUTTON_CUSTOM_ID, build_hub_components
from ui.rp_message import build_rp_message_components
from ui.setup_view import (
    SETUP_CHAR_SELECT_ID,
    SETUP_CUSTOM_IDS,
    SETUP_NEXT_PAGE_ID,
    SETUP_PREV_PAGE_ID,
    SETUP_ROLE_SELECT_ID,
    SETUP_START_ID,
    SetupState,
    build_setup_components,
)

if TYPE_CHECKING:
    from bot import RoleplayBot

logger = logging.getLogger(__name__)


class SetupRPCog(commands.Cog):
    def __init__(self, bot: "RoleplayBot") -> None:
        self.bot = bot
        # channel_id -> SetupState while the user is choosing role/character.
        self._setups: dict[int, SetupState] = {}

    # ---- /setup_rp ----------------------------------------------------------

    @commands.slash_command(
        name="setup_rp",
        description="Post the AI Roleplay hub panel in this channel.",
        default_member_permissions=disnake.Permissions(manage_channels=True),
        contexts=disnake.InteractionContextTypes(guild=True),
    )
    async def setup_rp(self, inter: disnake.GuildCommandInteraction) -> None:
        if inter.guild is None:
            await inter.response.send_message(
                "This command can only be used inside a server.", ephemeral=True
            )
            return

        await inter.response.send_message(
            components=build_hub_components(footer_text=self.bot.settings.footer_text),
        )

    # ---- Unified interaction listener --------------------------------------

    @commands.Cog.listener()
    async def on_message_interaction(self, inter: disnake.MessageInteraction) -> None:
        cid = inter.component.custom_id
        if cid == HUB_CREATE_BUTTON_CUSTOM_ID:
            await self._handle_create_room(inter)
            return
        if cid in SETUP_CUSTOM_IDS:
            await self._handle_setup_interaction(inter)
            return

    # ---- Hub button -> create private channel ------------------------------

    async def _handle_create_room(self, inter: disnake.MessageInteraction) -> None:
        if inter.guild is None or not isinstance(inter.user, disnake.Member):
            await inter.response.send_message(
                "Roleplay rooms can only be created from inside a server.", ephemeral=True
            )
            return

        try:
            await inter.response.defer(ephemeral=True)
        except disnake.HTTPException:
            return

        existing = self.bot.sessions.channels_for_user(inter.user.id)
        if existing:
            mentions = ", ".join(f"<#{cid}>" for cid in existing)
            await inter.followup.send(
                f"You already have an active roleplay room: {mentions}. "
                "Close it before opening a new one.",
                ephemeral=True,
            )
            return

        try:
            channel = await self._create_private_channel(inter.guild, inter.user)
        except disnake.Forbidden:
            await inter.followup.send(
                "I'm missing **Manage Channels** permission, so I can't create a "
                "private room. Ask a server admin to grant it.",
                ephemeral=True,
            )
            return
        except disnake.HTTPException as exc:
            logger.exception("Failed to create private RP channel")
            await inter.followup.send(
                f"Discord refused to create the channel: `{exc}`.",
                ephemeral=True,
            )
            return

        state = SetupState(owner_id=inter.user.id, channel_id=channel.id)
        self._setups[channel.id] = state

        msg = await channel.send(
            components=build_setup_components(state, footer_text=self.bot.settings.footer_text),
        )
        state.message_id = msg.id

        await inter.followup.send(
            f"Your private roleplay channel is ready: {channel.mention}.",
            ephemeral=True,
        )

    async def _create_private_channel(
        self, guild: disnake.Guild, member: disnake.Member
    ) -> disnake.TextChannel:
        assert guild.me is not None
        overwrites: dict[disnake.abc.Snowflake, disnake.PermissionOverwrite] = {
            guild.default_role: disnake.PermissionOverwrite(view_channel=False),
            guild.me: disnake.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True,
                manage_channels=True,
                embed_links=False,
            ),
            member: disnake.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
            ),
        }

        category: disnake.CategoryChannel | None = None
        if self.bot.settings.rp_category_id is not None:
            maybe_cat = guild.get_channel(self.bot.settings.rp_category_id)
            if isinstance(maybe_cat, disnake.CategoryChannel):
                category = maybe_cat

        safe_name = "".join(c for c in member.display_name.lower() if c.isalnum() or c in "-_")
        if not safe_name:
            safe_name = "trainer"
        channel_name = f"rp-{safe_name}"[:90]

        return await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"Private AI roleplay for {member.display_name}.",
            reason=f"AI Roleplay room requested by {member} ({member.id})",
        )

    # ---- Setup component interactions --------------------------------------

    async def _handle_setup_interaction(self, inter: disnake.MessageInteraction) -> None:
        state = self._setups.get(inter.channel_id)
        if state is None:
            await inter.response.send_message(
                "This setup panel has expired. Run **/setup_rp** again or click the hub button.",
                ephemeral=True,
            )
            return

        # Acknowledge the interaction immediately to prevent 3s timeout (10062 Unknown Interaction)
        if not inter.response.is_done():
            if inter.component.custom_id == SETUP_START_ID:
                await inter.response.defer(ephemeral=True)
            else:
                await inter.response.defer()

        if state.locked:
            await inter.followup.send(
                "Setup is already complete for this channel.", ephemeral=True
            )
            return
        if inter.user.id != state.owner_id:
            await inter.followup.send(
                "This setup belongs to someone else.", ephemeral=True
            )
            return

        cid = inter.component.custom_id

        if cid == SETUP_ROLE_SELECT_ID:
            values = inter.values or []
            if values:
                state.role = values[0]
            await self._rerender_setup(inter, state)
            return

        if cid == SETUP_CHAR_SELECT_ID:
            values = inter.values or []
            if values:
                state.character_key = values[0]
            await self._rerender_setup(inter, state)
            return

        if cid == SETUP_PREV_PAGE_ID:
            if state.page > 0:
                state.page -= 1
            await self._rerender_setup(inter, state)
            return

        if cid == SETUP_NEXT_PAGE_ID:
            if state.page < total_pages(per_page=25) - 1:
                state.page += 1
            await self._rerender_setup(inter, state)
            return

        if cid == SETUP_START_ID:
            await self._start_session(inter, state)
            return

    async def _rerender_setup(
        self, inter: disnake.MessageInteraction, state: SetupState
    ) -> None:
        try:
            await inter.edit_original_response(
                components=build_setup_components(
                    state, footer_text=self.bot.settings.footer_text
                ),
            )
        except disnake.HTTPException:
            logger.exception("Failed to edit setup message")

    async def _start_session(
        self, inter: disnake.MessageInteraction, state: SetupState
    ) -> None:
        if not state.role or not state.character_key:
            await inter.followup.send(
                "Pick both a role and a character first.", ephemeral=True
            )
            return

        character = CHARACTERS_BY_KEY.get(state.character_key)
        if character is None:
            await inter.followup.send(
                "Couldn't find that character — please rerun setup.", ephemeral=True
            )
            return

        if not isinstance(inter.user, disnake.Member) or inter.guild is None:
            await inter.followup.send(
                "Setup must be completed from inside the server.", ephemeral=True
            )
            return

        # Lock the setup panel and clear it from the in-progress map.
        state.locked = True
        try:
            await inter.edit_original_response(
                components=build_setup_components(
                    state, footer_text=self.bot.settings.footer_text
                ),
            )
        except disnake.HTTPException:
            logger.exception("Failed to lock setup panel")
        self._setups.pop(state.channel_id, None)

        member: disnake.Member = inter.user
        is_booster = member.premium_since is not None
        maxlen = (
            self.bot.settings.booster_memory_limit
            if is_booster
            else self.bot.settings.standard_memory_limit
        )

        prompts = build_session_prompt(
            character=character,
            role=state.role,
            user_display_name=member.display_name,
        )
        history = RollingHistory(system_prompt=prompts.system, maxlen=maxlen)
        history.add_user(prompts.opening_user_seed)

        session = RPSession(
            channel_id=state.channel_id,
            user_id=member.id,
            guild_id=inter.guild.id,
            role=state.role,
            character=character,
            history=history,
            user_display_name=member.display_name,
        )
        self.bot.sessions.add(session)

        channel = inter.channel
        if not isinstance(channel, disnake.TextChannel):
            return

        await inter.followup.send(
            (
                f"Setup complete — you are the **{state.role.capitalize()}**, "
                f"the AI plays **{character.name}**. "
                f"Memory window: {maxlen} messages "
                f"({'booster' if is_booster else 'standard'})."
            ),
            ephemeral=True,
        )

        try:
            async with channel.typing():
                ai_text = await self.bot.groq.generate(history.messages())
        except Exception as exc:  # noqa: BLE001
            logger.exception("Initial Groq generation failed")
            await channel.send(
                components=build_rp_message_components(
                    body_text=(
                        f"## The scene refuses to start...\n"
                        f"`{exc}`\n\n"
                        f"Hit **Reroll** to try again."
                    ),
                    footer_text=self.bot.settings.footer_text,
                ),
            )
            return

        history.add_assistant(ai_text)

        msg = await channel.send(
            components=build_rp_message_components(
                body_text=ai_text, footer_text=self.bot.settings.footer_text
            ),
        )
        session.last_ai_message_id = msg.id

        await channel.send(
            content=(
                "-# Type freely — every message you send is treated as your character's "
                "speech or actions. Use **Reroll** to regenerate the latest reply, or "
                "**Continue** to keep the scene moving."
            ),
        )


def setup(bot: "RoleplayBot") -> None:
    bot.add_cog(SetupRPCog(bot))
