import logging
from motor.motor_asyncio import AsyncIOMotorClient

log = logging.getLogger("mongodb")

class MongoDB:
    def __init__(self, uri: str, db_name: str = "roleplay_bot"):
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[db_name]
        self.linked_channels = self.db["linked_channels"]
        self.sessions = self.db["sessions"]

    async def init(self):
        # Trigger a simple command to ensure connection is established
        try:
            await self.client.admin.command('ping')
            log.info("Successfully connected to MongoDB.")
        except Exception as e:
            log.error(f"Failed to connect to MongoDB: {e}")
            raise

    # Linked Channels (Interserver)

    async def get_channel(self, channel_id: int) -> dict | None:
        return await self.linked_channels.find_one({"_id": channel_id})

    async def get_all_channels(self) -> list[dict]:
        return await self.linked_channels.find().to_list(length=None)

    async def get_other_channels(self, exclude_channel_id: int) -> list[dict]:
        return await self.linked_channels.find({"_id": {"$ne": exclude_channel_id}}).to_list(length=None)

    async def is_linked(self, channel_id: int) -> bool:
        return await self.get_channel(channel_id) is not None

    async def link_channel(self, channel_id: int, guild_id: int, guild_name: str, webhook_id: int, webhook_url: str):
        await self.linked_channels.update_one(
            {"_id": channel_id},
            {
                "$set": {
                    "guild_id": guild_id,
                    "guild_name": guild_name,
                    "webhook_id": webhook_id,
                    "webhook_url": webhook_url
                }
            },
            upsert=True
        )

    async def unlink_channel(self, channel_id: int):
        await self.linked_channels.delete_one({"_id": channel_id})

    async def update_webhook(self, channel_id: int, webhook_id: int, webhook_url: str):
        await self.linked_channels.update_one(
            {"_id": channel_id},
            {"$set": {"webhook_id": webhook_id, "webhook_url": webhook_url}}
        )

    # Sessions (AI Roleplay)

    async def get_session(self, thread_id: int) -> dict | None:
        return await self.sessions.find_one({"_id": thread_id})

    async def save_session(self, thread_id: int, data: dict):
        await self.sessions.update_one(
            {"_id": thread_id},
            {"$set": data},
            upsert=True
        )

    async def delete_session(self, thread_id: int):
        await self.sessions.delete_one({"_id": thread_id})
