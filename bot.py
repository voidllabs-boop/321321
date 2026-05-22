"""
bot.py - entry point for the inter-server bot.
Loads config, initializes the database, and registers cogs.
"""

import os
import asyncio
import logging

import disnake
from disnake.ext import commands

from utils.database import Database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("bot")

# Store your token in an environment variable: export DISCORD_TOKEN="your_token"
TOKEN = os.getenv("DISCORD_TOKEN", "MTUwNzMzODI1MjI1ODkwNjI1Mg.G8-Tj8.l-_aC_BqYt-bKw3fc1NMH6qgP89N1J3B-TIDG4")


def create_bot() -> commands.InteractionBot:
    """Creates and configures the bot instance."""
    intents = disnake.Intents.default()
    intents.message_content = True  # required to read message text
    intents.guilds = True
    intents.webhooks = True

    bot = commands.InteractionBot(
        intents=intents,
        # Register slash commands globally across all servers
        test_guilds=None,
    )

    # Attach the database to the bot so cogs can access it
    bot.db = Database("interserver.db")

    return bot


async def main():
    bot = create_bot()

    # Initialize database tables before starting
    await bot.db.init()

    # Load cogs
    bot.load_extension("cogs.interserver")
    log.info("Cogs loaded.")

    await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
