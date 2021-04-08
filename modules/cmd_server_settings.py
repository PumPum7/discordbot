import discord
from discord.ext import commands

import asyncio

from functions import func_database, func_msg_gen, func_prefix, func_setting_helpers

import bot_settings


class ServerSettings(commands.Cog, name="Server Settings"):
    def __init__(self, bot):
        self.bot = bot
        self.sdb = func_database.ServerDatabase()
        self.msg = func_msg_gen.MessageGenerator()
        self.prefix = func_prefix.Prefix()
        self.helper = func_setting_helpers.SettingHelper(bot)

    @commands.group(name="serversetting", aliases=["sset"], invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def cmd_server_settings(self, ctx):
        """See the server settings"""
        server_information = await ctx.get_server_information()
        try:
            # deletes server id and object id
            del server_information['_id']
            del server_information['server_id']
        except KeyError:
            return await ctx.send_help(self.cmd_server_settings)
        embed = discord.Embed(
            title="Server settings:"
        )
        embed.set_footer(text=f"For more information use {ctx.prefix}help {ctx.command}")
        embed.colour = await ctx.get_embed_color()
        paginator = self.msg.paginator_handler(ctx=ctx, base_embed=embed, items=server_information)
        return await paginator.start_paginator()

    @cmd_server_settings.command(name="prefix")
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def cmd_set_server_prefix(self, ctx, new_prefix: str = None):
        """Change the bots prefix."""
        if not new_prefix:
            prefix_ = await ctx.get_server_information()
            try:
                prefix_ = prefix_[0].get("prefix", None)
            except IndexError:
                prefix_ = None
            msg = f"The servers current prefix: `{prefix_}`" if prefix_ else "No prefix currently set."
        else:
            await self.prefix.set_prefix_server(ctx.guild.id, new_prefix)
            msg = f"Successfully set `{new_prefix}` as new server prefix."
        embed = discord.Embed(title="Prefix Menu", description=msg)
        return await self.msg.message_sender(ctx, embed)

    @cmd_server_settings.command(name="exp", aliases=["level"])
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def cmd_set_server_exp(self, ctx):
        """Enable the level system or change settings."""
        server_information = await ctx.get_server_information()
        embed = discord.Embed(
            title="Server Experience Settings"
        )
        embed.set_footer(
            text="Reply with the numbers next to the settings to change them."
        )
        items = {
            "Exp enabled": server_information.get("exp_enabled", "Disabled")
        }
        if server_information.get('exp_enabled', False):
            del server_information["exp_enabled"]
            settings = bot_settings.default_exp
            settings.update(server_information)
            guild_roles = ctx.guild.roles
            items, embed = self.helper.setting_formatter(settings, "exp", embed, guild_roles, items,
                                                         bot_settings.default_exp)
        check_message = {
            "exp_amount": "Allowed range: 5 to 500",
            "exp_cooldown": "Allowed range: 60 to 1800 seconds",
            "exp_level_roles": "You can use the ID, mention or name of a role.\n"
                               "`add` to add a role, `remove` to remove a role, `edit` to edit the "
                               "settings of an already added role.\nUsage: `add <role> <exp amount>`",
            "exp_blacklist_roles": "You can use the ID, mention or name of a role.\n"
                                   "`add` to add a role and `remove` to remove a role\n"
                                   "Usage: `add/remove <role>`"
        }
        checks = {
            "exp_amount": lambda m: int(m.content) in range(5, 500),
            "exp_cooldown": lambda m: int(m.content) in range(30, 1800),
            "exp_blacklist_roles": self.helper.settings_discord_object_handler,
            "exp_level_roles": self.helper.settings_discord_object_handler,
        }
        handle_setting = {
            "exp_blacklist_roles": self.helper.handle_roles,
            "exp_level_roles": self.helper.handle_roles,
        }
        paginator = self.msg.paginator_handler(
            ctx=ctx,
            base_embed=embed,
            items=items,
            func_check=self.helper.paginator_item_check(items),
            func=lambda response, self_object: self.helper.handle_settings(response, self_object, "exp", check_message,
                                                                           checks, handle_setting),
            close_after_func=True
        )
        return await paginator.start_paginator()

    @cmd_server_settings.command(name="income", aliases=["money"])
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def cmd_set_server_income(self, ctx):
        """Enable the income system or change settings."""
        server_information = await ctx.get_server_information()
        embed = discord.Embed(
            title="Server Income Settings"
        )
        embed.set_footer(
            text="Reply with the numbers next to the settings to change them."
        )
        items = {
            "Income enabled": server_information.get("income_enabled", "Disabled")
        }
        if server_information.get('income_enabled', False):
            del server_information["income_enabled"]
            settings = bot_settings.default_income
            settings.update(server_information)
            guild_roles = ctx.guild.roles
            items, embed = self.helper.setting_formatter(settings, "income", embed, guild_roles, items,
                                                         bot_settings.default_income)
        check_message = {
            "income_amount": "Allowed range: 5 to 500",
            "income_cooldown": "Allowed range: 1 to 1200 minutes",
            "daily_amount": "Allowed range: 60 to 10000",
            "income_daily_cooldown": "Allowed range: 1 to 48 hours",
            "income_multiplier_roles": "You can use the ID, mention or name of a role.\n"
                                       "`add` to add a role, `remove` to remove a role, `edit` to edit the "
                                       "settings of an already added role.\nUsage: `add <role> <multiplier>`",
            "income_blacklist_roles": "You can use the ID, mention or name of a role.\n"
                                      "`add` to add a role and `remove` to remove a role\n"
                                      "Usage: `add/remove <role>`",
            "income_tax_roles": "You can use the ID, mention or name of a role.\n"
                                "`add` to add a role and `remove` to remove a role.\n"
                                "Tax is the percentage which will be removed during `give` commands.\n"
                                "Usage: `add/remove <role> <tax>`"
        }
        checks = {
            "income_amount": lambda m: int(m.content) in range(5, 500),
            "income_cooldown": lambda m: int(m.content) in range(1, 1200),
            "daily_amount": lambda m: int(m.content) in range(30, 10000),
            "income_daily_cooldown": lambda m: int(m.content) in range(1, 48),
            "income_multiplier_roles": self.helper.settings_discord_object_handler,
            "income_blacklist_roles": self.helper.settings_discord_object_handler,
            "income_tax_roles": self.helper.settings_discord_object_handler,
        }
        handle_setting = {
            "income_blacklist_roles": self.helper.handle_roles,
            "income_multiplier_roles": self.helper.handle_roles,
            "income_tax_roles": self.helper.handle_roles
        }
        paginator = self.msg.paginator_handler(
            ctx=ctx,
            base_embed=embed,
            items=items,
            func_check=self.helper.paginator_item_check(items),
            func=lambda response, self_object: self.helper.handle_settings(response, self_object, "exp", check_message,
                                                                           checks, handle_setting),
            close_after_func=True
        )
        return await paginator.start_paginator()


def setup(bot):
    bot.add_cog(ServerSettings(bot))

# TODO: add custom permission handlers
