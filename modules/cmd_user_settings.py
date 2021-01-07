import random
from typing import Union

import discord
from discord.ext import commands

import bot_settings
from functions import func_database, func_msg_gen


class UserSettings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.udb = func_database.UserDatabase()
        self.msg = func_msg_gen.MessageGenerator()

    @commands.group(name="set", invoke_without_command=True)
    async def cmd_group_set(self, ctx):
        """Get your current user settings"""
        user_information = await ctx.get_user_information()
        try:
            user_information = user_information[0][0]
            # deletes user id and object id
            del user_information['_id']
            del user_information['user_id']
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

    @commands.cooldown(1, 5, commands.BucketType.user)
    @cmd_group_set.command(name="prefix")
    async def cmd_set_prefix(self, ctx, action=None, new_prefix: str = None):
        """Change the bots prefix. Action can be either add or remove"""
        # prefix_ = await self.udb.get_user_information_global(ctx.author.id).distinct("prefix")
        prefix_ = await ctx.get_user_information()
        try:
            prefix_ = prefix_[0][0]["prefix"]
        except KeyError or IndexError:
            prefix_ = []
        # Check if there are already 10 prefixes added
        if len(prefix_) > 10:
            message = "You can only add up to 10 custom prefixes. Please remove one " \
                      "of your prefixes before adding new ones!"
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

    @commands.cooldown(1, 60, commands.BucketType.user)
    @cmd_group_set.command(name="color", aliases=["colour"])
    async def cmd_set_embed_color(self, ctx, color: Union[discord.Color, str] = None) -> discord.Message:
        """Set the default embed color. Setting it as default will reset the setting"""
        if color is None:
            information = await ctx.get_user_information()
            try:
                embed_color = information[0][0]["embed_color"]
                msg = f"Current color {discord.Color(embed_color)}."
            except KeyError or IndexError:
                embed_color = None
                msg = "Not set"
        else:
            if color == "default":
                embed_color = bot_settings.embed_color
                msg = f"Successfully set to the default color {bot_settings.embed_color}"
            elif color == "random":
                embed_color = discord.Color(random.randint(0, 16777215))
                msg = f"Successfully set to the randomly generated color {embed_color}!"
            else:
                embed_color = color
                msg = f"Successfully set the color to {color}!"
            await ctx.set_user_information(query={"$set": {"embed_color": str(embed_color)}}, global_=True)
        embed = discord.Embed(
            title="Color Menu", description=msg, color=embed_color or bot_settings.embed_color
        )
        return await self.msg.message_sender(ctx, embed)


def setup(bot):
    bot.add_cog(UserSettings(bot))
