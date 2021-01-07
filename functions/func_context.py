import discord
from discord.ext import commands

from functions import func_database
import bot_settings

udb = func_database.UserDatabase()
sdb = func_database.ServerDatabase()


class FullContext(commands.Context):
    def __init__(self, **attrs):
        super().__init__(**attrs)
        self.server_information = None
        self.global_information = None
        self.local_information = None

    async def get_user_information(self) -> tuple:
        """
        :return: tuple
            Global, Local
        """
        if not self.global_information or not self.local_information:
            self.global_information = await udb.get_user_information_global(self.author.id).to_list(length=1)
            self.local_information = await udb.get_user_information(self.author.id, self.guild.id).to_list(length=1)
        return self.global_information, self.local_information

    async def set_user_information(self, query, global_=True):
        if global_:
            return await udb.set_setting_global(self.author.id, query=query)
        else:
            return await udb.set_setting_local(self.author.id, server_id=self.guild.id, query=query)

    async def get_embed_color(self) -> discord.Color:
        information = await self.get_user_information()
        try:
            embed_color = information[0][0]["embed_color"]
        except KeyError or IndexError:
            embed_color = bot_settings.embed_color
        return embed_color

    async def get_server_information(self):
        if not self.server_information:
            self.server_information = await sdb.get_server_information(self.guild.id).to_list(length=1)
        return self.server_information

    async def set_server_information(self, query):
        return await sdb.set_setting(self.guild.id, query=query)
