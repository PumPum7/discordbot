import datetime
import motor.motor_asyncio
from pymongo import ReturnDocument

import bot_settings

DEFAULTS = (bot_settings.database_password[1], bot_settings.database_username[1], bot_settings.database_default)

UDB = None


class Database:
    def __init__(self, password=DEFAULTS[0], username=DEFAULTS[1], dbname=DEFAULTS[2]):
        global UDB
        link = bot_settings.database_url[1].format(username, password)
        if not UDB:
            UDB = motor.motor_asyncio.AsyncIOMotorClient(link)
        self.client = UDB
        self.db = self.client[dbname]


class UserDatabase(Database):
    def __init__(self):
        super(UserDatabase, self).__init__()
        self.economy_db = self.db.MemberServerInformation
        self.collection = self.db.User

    def get_user_information(self, user_id: int, server_id: int):
        information = self.economy_db.find({"user_id": user_id, "server_id": server_id})
        return information

    def get_user_information_global(self, user_id: int):
        information = self.collection.find({"user_id": user_id})
        return information

    async def set_setting_global(self, user_id: int, query: dict):
        return await self.collection.find_one_and_update(
            {"user_id": user_id},
            query,
            upsert=True,
            return_document=ReturnDocument.AFTER
        )

    async def set_setting_local(self, user_id: int, server_id: int, query: dict):
        return await self.economy_db.find_one_and_update(
            {"user_id": user_id, "server_id": server_id},
            query,
            upsert=True,
            return_document=ReturnDocument.AFTER
        )

    async def edit_money(self, user_id: int, server_id: int, amount: int):
        return await self.set_setting_local(
            user_id=user_id,
            server_id=server_id,
            query={"$inc": {"balance": int(amount)}}
        )

    async def claim_daily(self, author_user_id: int, user_id: int, server_id: int, amount: int):
        await self.set_setting_local(
            user_id=author_user_id,
            server_id=server_id,
            query={"$set": {"claimed_daily": datetime.datetime.utcnow()}}
        )
        return await self.edit_money(
            user_id=user_id,
            server_id=server_id,
            amount=amount
        )


class ServerDatabase(Database):
    def __init__(self):
        super(ServerDatabase, self).__init__()
        self.collection = self.db.Server

    def get_server_information(self, server_id: int):
        information = self.collection.find({"server_id": server_id})
        return information

    async def set_setting(self, server_id: int, query: dict):
        return await self.collection.find_one_and_update(
            {"server_id": server_id},
            query,
            upsert=True,
            return_document=ReturnDocument.AFTER
        )

    async def edit_prefix(self, server_id: int, prefix: str, action: bool):
        """Edit server prefix"""
        query = "$addToSet" if action else "$pull"
        return await self.set_setting(
            server_id=server_id,
            query={query: {"prefix": prefix}}
        )


# test
if __name__ == '__main__':
    import asyncio
    import bot_settings

    loop = asyncio.get_event_loop()
    db = UserDatabase()
