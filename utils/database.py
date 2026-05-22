"""
utils/database.py - async SQLite wrapper using aiosqlite.

Stores the linked_channels table:
  channel_id  - Discord channel ID
  guild_id    - Discord guild ID
  guild_name  - guild name (cached, updated on /link)
  webhook_id  - webhook ID (used to verify the webhook still exists)
  webhook_url - full webhook URL (used for sending messages)
"""

import aiosqlite
import logging

log = logging.getLogger("database")


class Database:
    def __init__(self, path: str):
        self.path = path

    async def init(self):
        """Creates tables if they do not exist yet."""
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS linked_channels (
                    channel_id   INTEGER PRIMARY KEY,
                    guild_id     INTEGER NOT NULL,
                    guild_name   TEXT    NOT NULL,
                    webhook_id   INTEGER NOT NULL,
                    webhook_url  TEXT    NOT NULL
                )
            """)
            await db.commit()
        log.info("Database initialized: %s", self.path)

    # Read

    async def get_channel(self, channel_id: int) -> dict | None:
        """Returns the channel record or None if not found."""
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM linked_channels WHERE channel_id = ?",
                (channel_id,),
            ) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def get_all_channels(self) -> list[dict]:
        """Returns all linked channels."""
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM linked_channels ORDER BY guild_name"
            ) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def get_other_channels(self, exclude_channel_id: int) -> list[dict]:
        """Returns all channels except the given one (used for broadcasting)."""
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM linked_channels WHERE channel_id != ?",
                (exclude_channel_id,),
            ) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def is_linked(self, channel_id: int) -> bool:
        return await self.get_channel(channel_id) is not None

    # Write

    async def link_channel(
        self,
        channel_id: int,
        guild_id: int,
        guild_name: str,
        webhook_id: int,
        webhook_url: str,
    ):
        """Inserts or updates a channel record."""
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO linked_channels
                    (channel_id, guild_id, guild_name, webhook_id, webhook_url)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(channel_id) DO UPDATE SET
                    guild_id    = excluded.guild_id,
                    guild_name  = excluded.guild_name,
                    webhook_id  = excluded.webhook_id,
                    webhook_url = excluded.webhook_url
                """,
                (channel_id, guild_id, guild_name, webhook_id, webhook_url),
            )
            await db.commit()
        log.info("Channel %d linked to network (guild: %s).", channel_id, guild_name)

    async def unlink_channel(self, channel_id: int):
        """Removes a channel from the network."""
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "DELETE FROM linked_channels WHERE channel_id = ?",
                (channel_id,),
            )
            await db.commit()
        log.info("Channel %d unlinked from network.", channel_id)

    async def update_webhook(
        self, channel_id: int, webhook_id: int, webhook_url: str
    ):
        """Updates webhook data after it has been recreated."""
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                UPDATE linked_channels
                SET webhook_id = ?, webhook_url = ?
                WHERE channel_id = ?
                """,
                (webhook_id, webhook_url, channel_id),
            )
            await db.commit()
        log.info("Webhook for channel %d updated.", channel_id)
