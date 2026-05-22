"""
utils/webhook_manager.py - webhook creation, validation, and recreation.

A webhook is a URL that lets the bot post messages into a channel
under any username and avatar. The bot creates one webhook per linked channel.
"""

import logging
from typing import Optional

import aiohttp
import disnake

log = logging.getLogger("webhook_manager")

# The name the bot uses when creating webhooks (visible in channel settings)
WEBHOOK_NAME = "InterServer Bridge"


class WebhookManager:
    """Manages the lifecycle of Discord webhooks."""

    def __init__(self, bot: disnake.Client):
        self.bot = bot

    async def get_or_create(
        self, channel: disnake.TextChannel
    ) -> Optional[disnake.Webhook]:
        """
        Returns an existing bot-owned webhook in the channel, or creates one.
        Returns None if the bot lacks the Manage Webhooks permission.
        """
        try:
            webhooks = await channel.webhooks()
        except disnake.Forbidden:
            log.warning("No permission to list webhooks in channel %d.", channel.id)
            return None

        # Look for a webhook with our name that was created by this bot
        for wh in webhooks:
            if wh.name == WEBHOOK_NAME and wh.user and wh.user.id == self.bot.user.id:
                return wh

        # Not found - create a new one
        return await self.create(channel)

    async def create(
        self, channel: disnake.TextChannel
    ) -> Optional[disnake.Webhook]:
        """Creates a new webhook in the given channel."""
        try:
            webhook = await channel.create_webhook(
                name=WEBHOOK_NAME,
                reason="InterServer Bridge - automatic webhook creation",
            )
            log.info("Created webhook in channel %d (%s).", channel.id, channel.name)
            return webhook
        except disnake.Forbidden:
            log.warning("No permission to create webhook in channel %d.", channel.id)
            return None
        except disnake.HTTPException as e:
            log.error("Failed to create webhook in channel %d: %s", channel.id, e)
            return None

    async def ensure_webhook(
        self, channel: disnake.TextChannel, stored_webhook_id: int, db
    ) -> Optional[disnake.Webhook]:
        """
        Verifies that the stored webhook ID still exists in the channel.
        If it was deleted, recreates it and updates the database.
        """
        try:
            webhooks = await channel.webhooks()
        except disnake.Forbidden:
            return None

        # Look up by ID
        for wh in webhooks:
            if wh.id == stored_webhook_id:
                return wh

        # Webhook was deleted - recreate it
        log.warning(
            "Webhook %d not found in channel %d, recreating.",
            stored_webhook_id,
            channel.id,
        )
        webhook = await self.create(channel)
        if webhook:
            await db.update_webhook(channel.id, webhook.id, webhook.url)
        return webhook

    async def send(
        self,
        webhook_url: str,
        *,
        username: str,
        avatar_url: Optional[str],
        content: str = "",
        files: list[disnake.File] = None,
        embeds: list[disnake.Embed] = None,
    ) -> Optional[dict]:
        """
        Sends a message through a webhook by URL.
        Returns the sent message object or None on failure.
        """
        # Trim username to Discord's 80-character limit
        username = username[:80]

        async with aiohttp.ClientSession() as session:
            wh = disnake.Webhook.from_url(webhook_url, session=session)

            try:
                msg = await wh.send(
                    content=content or disnake.utils.MISSING,
                    username=username,
                    avatar_url=avatar_url or disnake.utils.MISSING,
                    files=files or disnake.utils.MISSING,
                    embeds=embeds or disnake.utils.MISSING,
                    wait=True,  # wait for response to get the message ID
                )
                return msg
            except disnake.NotFound:
                log.warning("Webhook not found when sending: %s", webhook_url)
                return None
            except disnake.HTTPException as e:
                log.error("Failed to send via webhook: %s", e)
                return None
