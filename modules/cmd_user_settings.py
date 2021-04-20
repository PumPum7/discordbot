import discord
from discord.ext import commands

import random
from typing import Union

from functions import func_database, func_msg_gen, func_prefix

import bot_settings


class UserSettings(commands.Cog, name="User Settings"):
    def __init__(self, bot):
        self.bot = bot
        self.udb = func_database.UserDatabase()
        self.msg = func_msg_gen.MessageGenerator()
        self.prefix = func_prefix.Prefix()

    @commands.group(name="set", invoke_without_command=True)
    async def cmd_group_set(self, ctx):
        """Get your current user settings"""
        user_information = await ctx.get_user_information()
        try:
            user_information = user_information[0]
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

    @commands.cooldown(1, 5, commands.BucketType.user)
    @cmd_group_set.command(name="prefix")
    async def cmd_set_prefix(self, ctx, new_prefix: str = None):
        """Change the bots prefix."""
        if not new_prefix:
            prefix_ = await ctx.get_user_information()
            try:
                prefix_ = prefix_[0].get("prefix", None)
            except IndexError:
                prefix_ = None
            msg = f"Your current prefix: `{prefix_}`" if prefix_ else "No prefix currently set."
        else:
            await self.prefix.set_prefix_user(ctx.author.id, new_prefix)
            msg = f"Successfully set `{new_prefix}` as your prefix."
        embed = discord.Embed(title="Prefix Menu", description=msg)
        return await self.msg.message_sender(ctx, embed)

    @commands.cooldown(1, 60, commands.BucketType.user)
    @cmd_group_set.command(name="color", aliases=["colour"])
    async def cmd_set_embed_color(self, ctx, color: Union[discord.Color, str] = None) -> discord.Message:
        """Set the default embed color. Setting it as default will reset the setting"""
        if color is None:
            information = await ctx.get_user_information()
            try:
                embed_color = information[0].get("embed_color", None)
                msg = f"Current color {discord.Color(embed_color)}."
            except KeyError or IndexError:
                embed_color = None
                msg = "Not set"
        else:
            if color == "default":
                embed_color = discord.Color(bot_settings.embed_color)
                msg = f"Successfully set to the default color {bot_settings.embed_color}"
            elif color == "random":
                embed_color = discord.Color(random.randint(0, 16777215))
                msg = f"Successfully set to the randomly generated color {embed_color}!"
            else:
                embed_color = color
                msg = f"Successfully set the color to {color}!"
            await ctx.set_user_information(query={"$set": {"embed_color": embed_color.value}}, global_=True)
        embed = discord.Embed(
            title="Color Menu", description=msg, color=embed_color or bot_settings.embed_color
        )
        return await self.msg.message_sender(ctx, embed)


def setup(bot):
    bot.add_cog(UserSettings(bot))
