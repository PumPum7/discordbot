from typing import Union

import discord
from discord.ext import commands

from functions import func_database, func_msg_gen


class ServerSettings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sdb = func_database.ServerDatabase()
        self.msg = func_msg_gen.MessageGenerator()

    @commands.group(name="serversetting", aliases=["sset"], invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def cmd_server_settings(self, ctx):
        server_information = await self.sdb.get_server_information(ctx.guild.id).to_list(length=1)
        try:
            server_information = server_information[0]
            # deletes server id and object id
            del server_information['_id']
            del server_information['server_id']
        except IndexError:
            return await ctx.send_help(self.cmd_server_settings)
        embed = discord.Embed(
            title="Server settings:"
        )
        embed.set_footer(text=f"For more information use {ctx.prefix}help {ctx.command}")
        paginator = self.msg.paginator_handler(ctx=ctx, base_embed=embed, items=server_information)
        return await paginator.start_paginator()

    @cmd_server_settings.command(name="prefix")
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def cmd_set_server_prefix(self, ctx, action=None, new_prefix=None):
        prefix_ = await self.sdb.get_server_information(ctx.guild.id).distinct("prefix")
        # Check if there are already 10 prefixes added
        if len(prefix_) > 10:
            message = "You can only add up to 10 custom prefixes. Please remove one " \
                      "of the prefixes before adding new ones!"
        # check if its already registered
        elif new_prefix in prefix_ and action == "add":
            message = f"`{new_prefix}` is already registered as prefix."
        # no action specified
        elif not new_prefix or not action:
            message = f"To change your prefix add `add` or `remove`.\n" \
                      f"For more information use `{ctx.prefix}help set prefix`."
        # adds or removes a prefix
        else:
            prefix = await self.prefix_handler(action, new_prefix, ctx)
            if not prefix:
                raise commands.MissingRequiredArgument(ctx.command)
            prefix_ = prefix[0]["prefix"]
            message = prefix[1]
        embed = discord.Embed(title="Prefix Menu", description=message)
        embed.add_field(
            name="Your current prefixes:",
            value=", ".join(prefix_) or "No custom prefixes are currently set"
        )
        await self.msg.message_sender(ctx, embed)

    async def prefix_handler(self, action, new_prefix, ctx) -> Union[bool, tuple]:
        action = action.lower()
        if action == "add":
            action = True
            msg = f"Successfully added `{new_prefix}` to your prefixes!"
        elif action == "remove":
            action = False
            msg = f"Successfully removed `{new_prefix}` from your prefixes!"
        else:
            return False
        prefix = await self.sdb.edit_prefix(ctx.guild.id, new_prefix, action)
        return prefix, msg


def setup(bot):
    bot.add_cog(ServerSettings(bot))
