import asyncio
from typing import Union

import discord
from discord.ext import commands

import bot_settings
from functions import func_database, func_msg_gen, func_prefix


class ServerSettings(commands.Cog, name="Server Settings"):
    def __init__(self, bot):
        self.bot = bot
        self.sdb = func_database.ServerDatabase()
        self.msg = func_msg_gen.MessageGenerator()
        self.prefix = func_prefix.Prefix()
        self.role_converter = commands.RoleConverter()
        self.channel_converter = commands.TextChannelConverter()

    @commands.group(name="serversetting", aliases=["sset"], invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def cmd_server_settings(self, ctx):
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
            for setting in settings.keys():
                if setting.__contains__("exp"):
                    items[setting] = settings.get(setting, bot_settings.default_exp[setting])
                    # if setting contains role do more
                    if setting.__contains__("role"):
                        role_setting = settings.get(setting, bot_settings.default_exp[setting])
                        if role_setting is None:
                            # handler if role setting is none
                            items[setting] = None
                        elif type(role_setting[0]) == dict:
                            # handles dict by adding a new field (looks better)
                            values = [list(i.values()) for i in role_setting]
                            items[setting] = "Check the fields below for more information"
                            for v in values:
                                role = discord.utils.get(guild_roles, id=v[0])
                                if role is None:
                                    role = f"role removed (`{v[0]})"
                                else:
                                    role = role.mention
                                values[values.index(v)] = [role, v[1]]
                                # TODO: sort the values with sorted
                            embed.add_field(
                                name=setting.replace("_", " ").capitalize(),
                                value='\n'.join([f"{i[0]}: {i[1]} Exp" for i in values]),
                                inline=False
                            )
                        else:
                            # otherwise just use the default
                            items[setting] = role_setting
        paginator = self.msg.paginator_handler(
            ctx=ctx,
            base_embed=embed,
            items=items,
            func_check=self.exp_paginator_check(items),
            func=self.handle_exp_settings,
            close_after_func=True
        )
        return await paginator.start_paginator()

    @staticmethod
    def exp_paginator_check(items):
        items = [str(i) for i in range(len(items.keys()) + 1)][1:]
        items += ["exit", "cancel"]

        def check(message: discord.Message):
            return message.content.lower() in items

        return check

    async def handle_exp_settings(self, response, self_object):
        # handle exit
        action = response.content.lower()
        if action in ["exit", "cancel"]:
            await self_object.ctx.send("Command menu closed!")
            return await self_object.close_paginator()
        # handle enabling/disabling
        try:
            setting = list(self_object.items.keys())[int(response.content) - 1].lower().replace(" ", "_")
            if action == "1":
                new_setting = not self_object.items.get("Exp enabled", False)
            # everything else
            else:
                check_message = {
                    "exp_amount": "Allowed range: 5 to 500",
                    "exp_cooldown": "Allowed range: 60 to 1800 seconds",
                    "exp_blacklist_roles": "You can use the ID, mention or name of a role.\n"
                                           "`add` to add a role, `remove` to remove a role",
                    "exp_level_roles": "You can use the ID, mention or name of a role.\n"
                                           "`add` to add a role, `remove` to remove a role, `edit` to edit the "
                                       "settings of an already added role.\nUsage: `add <role> <exp amount>`",
                }
                await response.channel.send(
                    f"Please input your new value for {setting.replace('_', ' ').capitalize()}\n"
                    f"{check_message.get(setting, '')}"
                )
                checks = {
                    "exp_amount": lambda m: int(m.content) in range(5, 500),
                    "exp_cooldown": lambda m: int(m.content) in range(30, 1800),
                    "exp_blacklist_roles": self.exp_discord_object_handler,
                    "exp_level_roles": self.exp_discord_object_handler,
                }
                task = self_object.ctx.bot.wait_for(
                    "message",
                    timeout=30,
                    check=checks.get(setting, False)
                )
                responded = False
                while not responded:
                    try:
                        result = await task
                        new_setting = result.content
                        responded = True
                    except asyncio.TimeoutError:
                        await self.msg.error_msg(self_object.ctx, "Command menu was closed!")
                        responded = True
                        return await self_object.close_paginator()

            async def set_setting(*args):  # args is only a little workaround
                await self.sdb.set_setting(
                    response.guild.id,
                    {"$set": {setting: int(new_setting)}}
                )
                return True
            # handles the settings
            handle_setting = {
                "exp_blacklist_roles": self.handle_exp_roles,
                "exp_level_roles": self.handle_exp_roles,
            }
            result = await handle_setting.get(setting, set_setting)(self_object, new_setting, setting)
            if not result:
                await self_object.ctx.send("Failed to change setting. Make sure that you have included all "
                                           "required settings.")
            await self.bot.process_commands(self_object.ctx.message)
            return await self_object.close_paginator()
        except Exception as e:
            # TODO: add logging
            print(e, "error in exp settings")
            await self.msg.error_msg(self_object.ctx, "Command menu was closed!")
            return await self_object.close_paginator()

    @staticmethod
    def exp_discord_object_handler(message):
        input_ = message.content.split(" ")
        if len(input_) < 2:
            return False
        if not input_[0] in ["add", "remove", "edit"]:
            return False
        return True

    async def handle_exp_roles(self, ctx, response, setting) -> bool:
        """Set the roles for exp settings"""
        ctx = ctx.ctx
        # Split the response
        response = response.split(" ")
        additional_settings = None
        try:
            # handle third values, handle missing values
            role = await self.role_converter.convert(ctx, response[1])
            thirdValue = ["exp_level_roles"]
            if setting in thirdValue:
                if len(response) < 3:
                    # handles if the action is remove because a third value is not required there
                    if response[0] == "remove":
                        print(response[0])
                        action = response[0]
                    else:
                        raise commands.BadArgument
                else:
                    action = response[0]
                    additional_settings = int(response[2])
            else:
                action = response[0]
                if action not in ["add", "remove"]:
                    raise commands.BadArgument
            if not role:
                raise commands.BadArgument
            await self.sdb.edit_role_settings(ctx.guild.id, action, setting, role.id, additional_settings)
        except commands.BadArgument or commands.CommandError or ValueError as e:
            print(e)
            return False
        else:
            return True

    async def handle_exp_channels(self, ctx, response, setting) -> bool:
        """Set the channels for exp settings"""
        ctx = ctx.ctx
        try:
            channel = await self.channel_converter.convert(ctx, response.split(" ")[1])
        except commands.BadArgument or commands.CommandError:
            return False
        else:
            return True


def setup(bot):
    bot.add_cog(ServerSettings(bot))

# TODO: add custom permission handlers
# TODO: add database adding to the role and channel handlers
# TODO: multiplier setting (maybe combine with blacklist setting)
