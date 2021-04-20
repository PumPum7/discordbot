from discord.ext import tasks

import aioredis

from functions import func_database

import bot_settings

CACHE = None


class Prefix:
    def __init__(self):
        global CACHE
        self.udb = func_database.UserDatabase()
        self.sdb = func_database.ServerDatabase()
        self.cache = CACHE

    async def create_cache(self):
        self.cache = await aioredis.create_redis_pool(bot_settings.redis_settings["url"], db=1)
        await self.cache.expire("server_prefix", 360)
        await self.cache.expire("user_prefix", 360)
        return

    @tasks.loop(seconds=361)
    async def set_expire(self):
        await self.cache.expire("server_prefix", 360)
        await self.cache.expire("user_prefix", 360)

    async def get_prefix(self, user_id, server_id) -> list:
        # create cache
        if not self.cache:
            await self.create_cache()
        prefix = [*bot_settings.prefix]
        # handle server prefix
        server_prefix = await self.cache.hget("server_prefix", server_id, encoding="utf-8")
        if server_prefix is None:
            server_prefix = await self.sdb.get_server_information(server_id).distinct("prefix")
            server_prefix = server_prefix[0] if server_prefix else 0
            await self.cache.hset("server_prefix", server_id, server_prefix)
        if server_prefix != 0:
            prefix.append(server_prefix)
        # handle user prefix
        user_prefix = await self.cache.hget("user_prefix", server_id, encoding="utf-8")
        if user_prefix is None:
            user_prefix = await self.udb.get_user_information_global(user_id).distinct("prefix")
            user_prefix = user_prefix[0] if user_prefix else 0
            await self.cache.hset("user_prefix", user_id, user_prefix)
        if user_prefix != 0:
            prefix.append(user_prefix)
        return prefix

    async def set_prefix_user(self, user_id: int, prefix: str):
        # create the cache
        if not self.cache:
            await self.create_cache()
        # set it in the cache
        await self.cache.hset("user_prefix", user_id, prefix)
        await self.udb.set_setting_global(
            user_id=user_id,
            query={"$set": {"prefix": prefix}}
        )
        return

    async def set_prefix_server(self, server_id: int, prefix: str):
        # create the cache
        if not self.cache:
            await self.create_cache()
        # set it in the cache
        await self.cache.hset("user_prefix", server_id, prefix)
        # set it in the database
        await self.sdb.set_setting(
            server_id=server_id,
            query={"$set": {"prefix": prefix}}
        )
        return
