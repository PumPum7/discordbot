from discord.ext import commands
from discord import utils, Object, errors

import aioredis
import logging
from logging.handlers import RotatingFileHandler

from functions import func_msg_gen, func_database, func_errors

import bot_settings

__name__ = "cmd_listeners"


class ListenerTest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.msg_generator = func_msg_gen.MessageGenerator()
        self.cache = None
        self.sdb = func_database.ServerDatabase()
        self.udb = func_database.UserDatabase()

    async def create_cache(self):
        self.cache = await aioredis.create_redis_pool(bot_settings.redis_settings["url"], db=0)
        return

    # @commands.Cog.listener("on_command_error")
    # async def error_handler(self, ctx, error):
    #     # no error handler if there is a local error handler
    #     if hasattr(ctx.command, 'on_error'):
    #         return
    #     cog = ctx.cog
    #     if cog:
    #         if cog._get_overridden_method(cog.cog_command_error) is not None:
    #             return
    #     error_ = getattr(error, 'original', error)
    #     ignored = (commands.CommandNotFound, commands.NotOwner, commands.DisabledCommand, commands.NoPrivateMessage)
    #     if isinstance(error_, ignored):
    #         return
    #     elif isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument, commands.MemberNotFound)):
    #         msg = f"Please make sure you have specified all required arguments correctly! \n" \
    #               f"Use `{ctx.prefix}help {ctx.command.qualified_name}` for more information."
    #     elif isinstance(error, commands.CommandOnCooldown):
    #         msg = str(error)
    #     elif isinstance(error, func_errors.EconomyError):
    #         msg = str(error)
    #     elif isinstance(error, func_errors.TooManyItems):
    #         msg = str(error) + f"\nIf you want to add more items, remove another item or " \
    #                            f"consider donate here: {bot_settings.subscription_website}"
    #     elif isinstance(error, func_errors.DuplicateItem):
    #         msg = str(error)
    #     else:
    #         self.bot.logger.error(f"An errror occured in the {ctx.command} command: {error}")
    #         msg = "The error has been reported."
    #     await self.msg_generator.error_msg(ctx, msg)

    @commands.Cog.listener("on_message")
    async def on_message_handlers(self, message):
        # return if user is a bot
        if message.author.bot:
            return
        if not self.cache:
            await self.create_cache()
        # handle user exp
        exp_ = await self.cache.get(key=f"{message.author.id} - {message.guild.id}")
        if not exp_:
            server_information = await self.sdb.get_server_information(message.guild.id).to_list(length=1)
            server_information = server_information[0] or {}
            if server_information.get("exp_enabled", False):
                await self.handle_exp(message, server_information)

    async def handle_exp(self, message, server_information):
        # TODO: multiplier for certain roles
        # get the required information and set exp
        exp_amount = server_information.get("exp_amount", bot_settings.default_exp["exp_amount"])
        cooldown = server_information.get("exp_cooldown", bot_settings.default_exp["exp_cooldown"])
        roles = server_information.get("exp_level_roles", bot_settings.default_exp["exp_level_roles"])
        roles_blacklisted = server_information.get("exp_blacklist_roles", bot_settings.default_exp["exp_blacklist_roles"])
        user_roles = [i.id for i in message.author.roles]
        if [i for i in roles_blacklisted if i["role_id"] in user_roles]:
            return
        await self.cache.set(f"{message.author.id} - {message.guild.id}", 1, expire=cooldown)
        result = await self.udb.set_setting_local(
            user_id=message.author.id,
            server_id=message.guild.id,
            query={"$inc": {"exp_amount": exp_amount}}
        )
        cur_exp = result.get("exp_amount", 0)
        if roles:
            # filters out all roles which the user already has, and which they should get
            roles = [i for i in roles if i["value"] <= cur_exp and i["role_id"] not in user_roles]
            # creates a object for every role with the attribute id to use the edit function with it
            new_roles = utils._unique(Object(id=r["role_id"]) for r in roles)
            try:
                await message.author.add_roles(*new_roles, reason="Leveled roles")
            except errors.Forbidden:
                self.bot.logger.info(f"No permission to add leveled role in server "
                                     f"{server_information.get('server_id')}")
            except Exception as error:
                self.bot.logger.info(f"Error while adding exp role in server {server_information.get('server_id')}: "
                                     f"{error}")
            finally:
                return

def setup(bot):
    # bot.add_listener(on_command_error)
    # bot.add_listener(on_message)
    bot.add_cog(ListenerTest(bot))
