from typing import Union
import discord
from discord.ext import commands

from functions import func_database, func_msg_gen


class UserSettings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.udb = func_database.UserDatabase()
        self.msg = func_msg_gen.MessageGenerator()

    @commands.group(name="set", invoke_without_command=True)
    async def cmd_group_set(self, ctx):
        """Get your current user settings"""
        user_information = await self.udb.get_user_information_global(ctx.author.id).to_list(length=1)
        try:
            user_information = user_information[0]
            # deletes user id and object id
            del user_information['_id']
            del user_information['user_id']
            del user_information["balance"]
        except IndexError:
            return await ctx.send_help(self.cmd_group_set)
        embed = discord.Embed(
            title=f"{ctx.author.name}'s settings:"
        )
        embed.set_footer(text=f"For more information use {ctx.prefix}help {ctx.command}")
        paginator = self.msg.paginator_handler(ctx, embed, user_information)
        await paginator.start_paginator()

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
        prefix = await self.udb.edit_prefix(ctx.author.id, new_prefix, action)
        return prefix, msg

    @cmd_group_set.command(name="prefix")
    async def cmd_set_prefix(self, ctx, action=None, new_prefix: str = None):
        """Change the bots prefix. Action can be either add or remove"""
        prefix_ = await self.udb.get_user_information_global(ctx.author.id).distinct("prefix")
        # Check if there are already 10 prefixes added
        if len(prefix_) > 10:
            message = "You can only add up to 10 custom prefixes. Please remove one " \
                      "of your prefixes before adding new ones!"
        # check if its already registered
        elif new_prefix in prefix_:
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
            value=", ".join(prefix_)
        )
        await self.msg.message_sender(ctx, embed)


def setup(bot):
    bot.add_cog(UserSettings(bot))
