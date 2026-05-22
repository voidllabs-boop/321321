"""AI Roleplay Discord bot entrypoint.

Run with: ``python bot.py``

Requires environment variables:
    DISCORD_TOKEN, GROQ_API_KEY  (see .env.example).
"""

from __future__ import annotations

import logging
import sys

import disnake
from disnake.ext import commands

from config import Settings, load_settings
from core.groq_client import GroqClient
from core.sessions import SessionStore
from utils.mongodb import MongoDB
from keep_alive import keep_alive


logger = logging.getLogger("ai_roleplay")

MONGO_URI = "mongodb+srv://voidllabs_db_user:YmDFoyPYeHZ63ITO@cluster0.hlyrfcl.mongodb.net/?appName=Cluster0"

class RoleplayBot(commands.InteractionBot):
    def __init__(self, *, settings: Settings) -> None:
        intents = disnake.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        intents.webhooks = True

        kwargs: dict[str, object] = {"intents": intents}
        if settings.dev_guild_ids:
            kwargs["test_guilds"] = settings.dev_guild_ids
        super().__init__(**kwargs)  # type: ignore[arg-type]

        self.settings = settings
        self.sessions = SessionStore() # Still using in-memory store for active sessions/locks
        self.groq = GroqClient(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            timeout_seconds=settings.groq_timeout_seconds,
        )
        self.db = MongoDB(MONGO_URI)

    async def on_ready(self) -> None:
        if self.user is None:
            return
        await self.db.init()
        logger.info("Logged in as %s (id=%s).", self.user, self.user.id)
        logger.info("Using Groq model: %s", self.settings.groq_model)

    async def on_slash_command_error(
        self, inter: disnake.ApplicationCommandInteraction, error: Exception
    ) -> None:
        logger.exception("Slash command error: %s", error)
        if not inter.response.is_done():
            await inter.response.send_message(
                "An error occurred while processing the command.", ephemeral=True
            )

    async def on_interaction_error(
        self, inter: disnake.Interaction, error: Exception
    ) -> None:
        logger.exception("Interaction error: %s", error)
        # For non-slash command interactions (like buttons)
        if not inter.response.is_done():
            try:
                await inter.response.send_message(
                    "Something went wrong. Please try again.", ephemeral=True
                )
            except disnake.HTTPException:
                pass

    async def close(self) -> None:
        try:
            await self.groq.aclose()
        finally:
            await super().close()


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    # disnake is noisy at DEBUG; keep it at INFO.
    logging.getLogger("disnake").setLevel(logging.INFO)


def main() -> None:
    _configure_logging()
    try:
        settings = load_settings()
    except RuntimeError as exc:
        logger.error("%s", exc)
        sys.exit(1)

    keep_alive()
    bot = RoleplayBot(settings=settings)
    bot.load_extension("cogs.setup_rp")
    bot.load_extension("cogs.roleplay")
    bot.load_extension("cogs.interserver")
    bot.load_extension("cogs.translate")

    try:
        bot.run(settings.discord_token)
    except disnake.LoginFailure:
        logger.error("Invalid DISCORD_TOKEN — check your .env file.")
        sys.exit(2)
    except disnake.PrivilegedIntentsRequired:
        logger.error(
            "This bot requires the SERVER MEMBERS and MESSAGE CONTENT privileged intents. "
            "Enable them at https://discord.com/developers/applications under your bot's "
            "'Bot' tab → Privileged Gateway Intents."
        )
        sys.exit(3)


if __name__ == "__main__":
    main()
