"""
cogs/interserver.py - main cog.

Contains:
  - Slash commands: /link, /unlink, /network
  - on_message listener - intercepts messages and broadcasts them across the network
"""

import io
import logging
from typing import Optional

import aiohttp
import disnake
from disnake.ext import commands

from utils.database import Database
from utils.webhook_manager import WebhookManager

log = logging.getLogger("interserver")

# Maximum file size to forward (8 MB - standard Discord limit)
MAX_FILE_SIZE = 8 * 1024 * 1024


class InterServerCog(commands.Cog, name="InterServer"):
    """Cog for the inter-server chat network."""

    def __init__(self, bot: commands.InteractionBot):
        self.bot = bot
        self.db: Database = bot.db
        self.wh_manager = WebhookManager(bot)

    # Helpers

    async def _check_permissions(
        self, inter: disnake.ApplicationCommandInteraction
    ) -> bool:
        """
        Checks that the user is a server administrator.
        Sends an ephemeral error reply and returns False if not.
        """
        if not inter.author.guild_permissions.administrator:
            await inter.response.send_message(
                "Only administrators can manage the channel network.",
                ephemeral=True,
            )
            return False
        return True

    def _build_jump_footer(self, message: disnake.Message) -> str:
        """Returns a jump link pointing to the original message."""
        return f"\n\n[-> Jump to original]({message.jump_url})"

    # on_message listener

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        """
        Handles every new message.
        If the channel is linked to the network, broadcasts to all other linked channels.
        """
        # Ignore bots and webhooks (including our own relayed messages)
        if message.author.bot:
            return
        # Ignore DMs
        if not message.guild:
            return
        # Ignore if the channel is not linked
        if not await self.db.is_linked(message.channel.id):
            return

        # Get all other channels in the network
        targets = await self.db.get_other_channels(message.channel.id)
        if not targets:
            return  # No other channels to broadcast to

        log.info(
            "Message from %s (%s) -> broadcasting to %d channel(s).",
            message.author,
            message.guild.name,
            len(targets),
        )

        # Build sender identity
        # Username format: "John (My Server)"
        display_name = message.author.display_name or message.author.name
        username = f"{display_name} ({message.guild.name})"
        avatar_url = message.author.display_avatar.url

        # Message text + jump link
        content = message.content or ""
        content += self._build_jump_footer(message)

        # Discord's message length limit is 2000 characters
        if len(content) > 2000:
            content = content[:1996] + "..."

        # Download attachments into memory
        # Stored as (bytes, filename, is_spoiler) tuples
        files_cache: list[tuple] = []
        for att in message.attachments:
            if att.size <= MAX_FILE_SIZE:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(att.url) as resp:
                            if resp.status == 200:
                                files_cache.append(
                                    (await resp.read(), att.filename, att.is_spoiler())
                                )
                except Exception as e:
                    log.error("Failed to download attachment %s: %s", att.filename, e)

        # Broadcast to each target channel
        for target in targets:
            channel = self.bot.get_channel(target["channel_id"])
            if channel is None:
                # Bot may have left the guild or the channel was deleted
                log.warning("Channel %d is unavailable, skipping.", target["channel_id"])
                continue

            # Verify the webhook exists; recreate if it was deleted
            webhook = await self.wh_manager.ensure_webhook(
                channel, target["webhook_id"], self.db
            )
            if webhook is None:
                log.warning("Could not obtain webhook for channel %d.", channel.id)
                continue

            # Rebuild File objects for each recipient.
            # disnake.File wraps a BytesIO buffer which can only be read once,
            # so a fresh object is required for every send call.
            files: list[disnake.File] = [
                disnake.File(io.BytesIO(data), filename=fname, spoiler=spoiler)
                for data, fname, spoiler in files_cache
            ]

            await self.wh_manager.send(
                webhook.url,
                username=username,
                avatar_url=avatar_url,
                content=content,
                files=files if files else None,
            )

    # Slash commands

    @commands.slash_command(
        name="link",
        description="Link this channel to the inter-server network",
    )
    async def link(self, inter: disnake.ApplicationCommandInteraction):
        """Links the current channel to the network."""
        if not await self._check_permissions(inter):
            return

        await inter.response.defer(ephemeral=True)
        channel: disnake.TextChannel = inter.channel

        # Check if already linked
        if await self.db.is_linked(channel.id):
            await inter.edit_original_response(
                content="This channel is already linked to the network. "
                        "Use `/unlink` to remove it."
            )
            return

        # Get existing or create a new webhook
        webhook = await self.wh_manager.get_or_create(channel)
        if webhook is None:
            await inter.edit_original_response(
                content="Failed to create a webhook. "
                        "Make sure the bot has the **Manage Webhooks** permission."
            )
            return

        # Save to database
        await self.db.link_channel(
            channel_id=channel.id,
            guild_id=inter.guild.id,
            guild_name=inter.guild.name,
            webhook_id=webhook.id,
            webhook_url=webhook.url,
        )

        all_channels = await self.db.get_all_channels()
        count = len(all_channels)

        await inter.edit_original_response(
            content=(
                f"{channel.mention} has been linked to the network.\n"
                f"Total channels in network: **{count}**."
            )
        )
        log.info(
            "Channel %d (%s / %s) linked by admin %s.",
            channel.id,
            channel.name,
            inter.guild.name,
            inter.author,
        )

    @commands.slash_command(
        name="unlink",
        description="Unlink this channel from the inter-server network",
    )
    async def unlink(self, inter: disnake.ApplicationCommandInteraction):
        """Unlinks the current channel from the network and deletes its webhook."""
        if not await self._check_permissions(inter):
            return

        await inter.response.defer(ephemeral=True)
        channel: disnake.TextChannel = inter.channel

        record = await self.db.get_channel(channel.id)
        if record is None:
            await inter.edit_original_response(
                content="This channel is not linked to the network."
            )
            return

        # Delete the webhook silently if it is already gone
        try:
            webhooks = await channel.webhooks()
            for wh in webhooks:
                if wh.id == record["webhook_id"]:
                    await wh.delete(reason="InterServer: channel unlinked from network")
                    break
        except (disnake.Forbidden, disnake.HTTPException) as e:
            log.warning("Could not delete webhook during /unlink: %s", e)

        await self.db.unlink_channel(channel.id)

        await inter.edit_original_response(
            content=f"{channel.mention} has been unlinked from the network."
        )
        log.info("Channel %d unlinked by admin %s.", channel.id, inter.author)

    @commands.slash_command(
        name="network",
        description="List all channels connected to the inter-server network",
    )
    async def network(self, inter: disnake.ApplicationCommandInteraction):
        """Displays all channels currently in the network."""
        await inter.response.defer(ephemeral=True)

        channels = await self.db.get_all_channels()

        if not channels:
            await inter.edit_original_response(
                content="The network is empty. Link a channel with `/link`."
            )
            return

        # Group by guild for readability
        by_guild: dict[str, list[dict]] = {}
        for ch in channels:
            by_guild.setdefault(ch["guild_name"], []).append(ch)

        lines = [f"**Network channels** ({len(channels)} total)\n"]
        for guild_name, ch_list in sorted(by_guild.items()):
            lines.append(f"**{guild_name}**")
            for ch in ch_list:
                discord_channel = self.bot.get_channel(ch["channel_id"])
                if discord_channel:
                    lines.append(f"  - {discord_channel.mention}")
                else:
                    lines.append(f"  - `#{ch['channel_id']}` *(unavailable)*")

        text = "\n".join(lines)
        if len(text) > 2000:
            text = text[:1990] + "\n..."

        await inter.edit_original_response(content=text)


def setup(bot: commands.InteractionBot):
    bot.add_cog(InterServerCog(bot))
    log.info("InterServer cog loaded.")
