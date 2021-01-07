import discord
from discord.ext import commands
import logging
from logging.handlers import RotatingFileHandler

from functions import func_errors, func_msg_gen

MSG_GENERATOR = func_msg_gen.MessageGenerator()

logger = logging.getLogger('discord')
logger.setLevel(logging.ERROR)
handler = RotatingFileHandler(filename='data/errors/errors_bot.log', encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


async def on_command_error(ctx, error):
    # no error handler if there is a local error handler
    if hasattr(ctx.command, 'on_error'):
        return
    cog = ctx.cog
    if cog:
        if cog._get_overridden_method(cog.cog_command_error) is not None:
            return
    error_ = getattr(error, 'original', error)
    ignored = (commands.CommandNotFound, commands.NotOwner, commands.DisabledCommand, commands.NoPrivateMessage)
    if isinstance(error_, ignored):
        return
    elif isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument)):
        msg = f"Please make sure you have specified all required arguments correctly! \n" \
              f"Use `{ctx.prefix}help {ctx.command.qualified_name}` for more information."
    elif isinstance(error, commands.CommandOnCooldown):
        msg = str(error)
    elif isinstance(error, func_errors.EconomyError):
        msg = str(error)
    else:
        logger.error(f"{ctx.command.qualified_name}: {ctx.message.guild.id}: {error}")
        msg = "The error has been reported."
    await MSG_GENERATOR.error_msg(ctx, msg)


def setup(bot):
    bot.add_listener(on_command_error)