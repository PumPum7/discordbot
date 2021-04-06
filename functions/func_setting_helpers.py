import discord
from discord.ext import commands

import asyncio

from functions import func_database, func_msg_gen, func_prefix, func_errors

import bot_settings


class SettingHelper:
    def __init__(self, bot):
        self.bot = bot
        self.sdb = func_database.ServerDatabase()
        self.msg = func_msg_gen.MessageGenerator()
        self.prefix = func_prefix.Prefix()
        self.role_converter = commands.RoleConverter()
        self.channel_converter = commands.TextChannelConverter()

    @staticmethod
    def paginator_item_check(items):
        # exp_paginator_check: return if the message includes exit or cancel
        items = [str(i) for i in range(len(items.keys()) + 1)][1:]
        items += ["exit", "cancel"]

        def check(message: discord.Message):
            return message.content.lower() in items

        return check

    @staticmethod
    def settings_discord_object_handler(message) -> bool:
        # settings_discord_object_handler: checks if the message includes enough arguments
        input_ = message.content.split(" ")
        if len(input_) < 2:
            return False
        if not input_[0] in ["add", "remove", "edit"]:
            return False
        return True

    async def handle_roles(self, ctx, response: str, setting: str) -> bool:
        """Set the roles for exp settings"""
        ctx = ctx.ctx
        # Split the response
        response = response.split(" ")
        additional_settings = None
        try:
            # handle third values, handle missing values
            role = await self.role_converter.convert(ctx, response[1])
            third_value: list = bot_settings.third_value_settings
            if setting in third_value:
                if len(response) < 3:
                    # handles if the action is remove because a third value is not required there
                    if response[0] == "remove":
                        action = response[0]
                    else:
                        raise commands.BadArgument
                else:
                    action = response[0]
                    additional_settings = int(response[2])
            else:
                # handle actions
                action = response[0]
                if action not in ["add", "remove"]:
                    raise commands.BadArgument
            if not role:
                raise commands.BadArgument
            # TODO: implement multiple server levels
            # handles the limits for the setting
            server_subscription_level = "basic"
            limits = bot_settings.limits[server_subscription_level].get(setting, -1)
            current_setting = await ctx.get_server_information()
            current_setting = current_setting.get(setting, current_setting)
            if len(current_setting) > limits > -1:
                raise func_errors.TooManyItems(
                    f"You already have more than **{limits} "
                    f"{setting.replace('_', ' ')}**!"
                )
            # check if the role is already in the list
            try:
                if (
                    role.id in [i["role_id"] for i in current_setting]
                    and action == "add"
                ):
                    raise func_errors.DuplicateItem(
                        "You have already added this role! Use `edit` to edit the setting."
                    )
            except TypeError:
                pass
            await self.sdb.edit_role_settings(
                ctx.guild.id, action, setting, role.id, additional_settings, "value"
            )
        except commands.BadArgument or commands.CommandError or ValueError as error:
            # handle specific errors which probably arent an error
            self.bot.logger.info(
                f"An exception has occurred while handling exp role settings: {error}",
                error,
            )
            await self.msg.error_msg(
                ctx,
                "An error has occurred while handling role settings. "
                "Please make sure that your input was correct.",
            )
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

    @staticmethod
    def setting_formatter(
        settings, setting_type, embed, guild_roles, items, default_settings: dict
    ):
        for setting in settings.keys():
            if setting.__contains__(setting_type):
                items[setting] = settings.get(setting, default_settings[setting])
                # if setting contains role do more
                if setting.__contains__("role"):
                    role_setting = settings.get(setting, default_settings[setting])
                    if role_setting is None or len(role_setting) == 0:
                        # handler if role setting is none
                        items[setting] = None
                    elif type(role_setting[0]) == dict:
                        # handles dict by adding a new field (looks better)
                        values = [list(i.values()) for i in role_setting]
                        items[setting] = "Check the fields below for more information"
                        for v in values:
                            # get the roles
                            role = discord.utils.get(guild_roles, id=v[0])
                            if role is None:
                                # if role not found return role removed
                                role = f"role removed (`{v[0]})"
                            else:
                                role = role.mention
                            if len(v) > 1:
                                # add both values if its a list in a list
                                values[values.index(v)] = [role, v[1]]
                            else:
                                # directly add the value otherwise
                                values[values.index(v)] = role
                        if type(values[0]) == list:
                            # if its another list in the list sort it and add both values to the output
                            values = sorted(values, key=lambda x: x[1])
                            embed.add_field(
                                name=setting.replace("_", " ").capitalize(),
                                value="\n".join(
                                    [f"{i[0]}: {i[1]} {setting_type}" for i in values]
                                ),
                                inline=False,
                            )
                        else:
                            embed.add_field(
                                name=setting.replace("_", " ").capitalize(),
                                value="\n".join([f"{i}" for i in values]),
                            )

                    else:
                        # otherwise just use the default
                        items[setting] = role_setting
        return items, embed

    async def handle_settings(
        self,
        response,
        self_object,
        setting_category: str,
        check_message: dict,
        checks: dict,
        handlers: dict,
    ):
        # handle exit
        action = response.content.lower()
        if action in ["exit", "cancel"]:
            await self_object.ctx.send("Command menu closed!")
            return await self_object.close_paginator()
        # handle enabling/disabling
        setting = (
            list(self_object.items.keys())[int(response.content) - 1]
            .lower()
            .replace(" ", "_")
        )
        if action == "1":
            new_setting = not self_object.items.get(
                f"{setting_category.capitalize()} enabled", False
            )
        # everything else
        else:
            await response.channel.send(
                f"Please input your new value for {setting.replace('_', ' ').capitalize()}\n"
                f"{check_message.get(setting, '')}"
            )
            task = self_object.ctx.bot.wait_for(
                "message", timeout=60, check=checks.get(setting, False)
            )
            # wait for the response
            responded = False
            while not responded:
                try:
                    result = await task
                    new_setting = result.content
                    responded = True
                except asyncio.TimeoutError:
                    await self.msg.error_msg(
                        self_object.ctx, "Command menu was closed!"
                    )
                    responded = True
                    return await self_object.close_paginator()

        async def set_setting(*args):  # args is only a little workaround
            if setting.__contains__("enabled"):
                new_setting_formatted = bool(new_setting)
            else:
                new_setting_formatted = int(new_setting)

            await self.sdb.set_setting(
                response.guild.id, {"$set": {setting: new_setting_formatted}}
            )
            return True

        # handles the settings
        result = await handlers.get(setting, set_setting)(
            self_object, new_setting, setting
        )
        if not result:
            await self_object.ctx.send(
                "Failed to change setting. Make sure that you have included all "
                "required settings."
            )
        await self.bot.process_commands(self_object.ctx.message)
        return await self_object.close_paginator()


# TODO: add database adding to the role and channel handlers
# TODO: multiplier setting (maybe combine with blacklist setting)
