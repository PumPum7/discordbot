import datetime
import motor.motor_asyncio
from pymongo import ReturnDocument, ASCENDING, DESCENDING

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
        self.local_db = self.db.MemberServerInformation
        self.collection = self.db.User

    def get_user_information(self, user_id: int, server_id: int):
        information = self.local_db.find({"user_id": user_id, "server_id": server_id})
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
        return await self.local_db.find_one_and_update(
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

    async def user_sort_exp(self, server_id: int, setting: str, user_amount: int):
        result = self.local_db.find({
            "server_id": server_id,
            setting: {"$gte": user_amount}
        }).sort(setting, ASCENDING).hint([("exp_amount", ASCENDING)])
        return await result.to_list(None)

    async def user_sort_exp_leaderboard(self, server_id: int, setting: str):
        result = self.local_db.find({
            "server_id": server_id
        }).sort(setting, DESCENDING).hint([("exp_amount", ASCENDING)])
        return await result.to_list(None)

    async def user_add_item(self, user_id: int, server_id: int, item: dict):
        return await self.set_setting_local(
            user_id=user_id,
            server_id=server_id,
            query={"$addToSet": {"items": {
                "item_id": item["item_id"],
                "name": item["name"],
                "usage": 0,
                "amount": 1
            }}}
        )

    async def user_add_owned_item(self, user_id: int, server_id: int, item_id: str):
        result = await self.local_db.find_one_and_update(
            {"user_id": user_id, "server_id": server_id},
            {"$inc": {"items.$[item].amount": 1}},
            array_filters=[{"item.item_id": item_id}],
            upsert=True,
            return_document=ReturnDocument.AFTER
        )
        return result

    async def user_use_item(self, user_id: int, server_id: int, item_id: str):
        result = await self.local_db.find_one_and_update(
            {"user_id": user_id, "server_id": server_id},
            {"$inc": {f"items.$[item].usage": 1, "items.$[item].amount": -1}},
            array_filters=[{"item.item_id": item_id}],
            upsert=True,
            return_document=ReturnDocument.AFTER
        )
        return result

    async def remove_item(self, user_id: int, server_id: int, item_id: str):
        return await self.set_setting_local(
            user_id=user_id,
            server_id=server_id,
            query={"$pull": {"items": {"item_id": item_id}}}
        )

    async def get_item(self, user_id: int, server_id: int, item_id: str):
        result = await self.local_db.find_one(
            {"user_id": user_id, "server_id": server_id, "items": {"$elemMatch": {"item_id": item_id}}}
        )
        return result

    async def search_items(self, user_id: int, server_id: int, search: str):
        result = self.local_db.find(
            {"user_id": user_id, "server_id": server_id, "$text": {"$search": search}}
        )
        return result


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

    async def edit_role_settings(self, server_id: int, action: str, setting: str, role_id: int,
                                 third_value: int = None, third_value_settings: str = None):
        """Add a role setting"""
        query = "$addToSet" if action == "add" else "$pull"
        if action == "edit":
            # Needed for an update since it requires more things to be true
            return await self.collection.find_one_and_update(
                {"server_id": server_id, f"{setting}.role_id": role_id},
                {"$set": {f"{setting}.$.{third_value_settings}": third_value}},
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
        return await self.set_setting(
            server_id=server_id,
            query={query: {setting: {"role_id": role_id,
                                     "required": third_value} if third_value else {"role_id": role_id}}}
        )


class ItemDatabase(Database):
    def __init__(self):
        super(ItemDatabase, self).__init__()
        self.item_db = self.db.ServerItems

    async def get_items(self, server_id: int):
        return self.item_db.find(
            {"server_id": server_id},
            projection={"_id": False}
        )

    async def search_items(self, server_id: int, search: str):
        return self.item_db.find(
            {"server_id": server_id, "$text": {"$search": search}},
            projection={"_id": False}
        )

    async def get_item(self, server_id: int, item_id: str):
        return await self.item_db.find_one(
            filter={"server_id": server_id, "item_id": item_id}
        )

    async def get_shop_items(self, server_id: int):
        return self.item_db.find(
            {"server_id": server_id, "available": "true"}
        )

    async def search_shop_items(self, server_id: int, search: str):
        return self.item_db.find(
            {"server_id": server_id, "$text": {"$search": search}, "available": "true"},
            projection={"_id": False}
        )

    async def create_item(self, item: dict):
        result = await self.item_db.insert_one(
            item
        )
        return result

    async def edit_item(self, server_id: int, item_id: str, item: dict):
        result = await self.item_db.find_one_and_update(
            {"server_id": server_id, "item_id": item_id},
            {"$set": item},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return result

    async def delete_item(self, server_id: int, item_id: str):
        result = await self.item_db.delete_one(
            {"server_id": server_id, "item_id": item_id}
        )
        return result

    async def remove_stock(self, server_id: int, item_id: str):
        result = await self.item_db.find_one_and_update(
            {"server_id": server_id, "item_id": item_id},
            {"$inc": {"store.stock": -1}},
            return_document=ReturnDocument.AFTER,
            upsert=False
        )
        return result


# test
async def main():
    db = UserDatabase()
    res = await db.user_sort_exp(server_id=330300161895038987, setting="exp_amount", user_amount=0)
    print(res)


if __name__ == '__main__':
    import asyncio
    import bot_settings

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
