import ast
import random

import discord
from discord.ext import commands
import os
import traceback
import asyncio
import logging
from logging.handlers import RotatingFileHandler

import bot_settings
from functions import func_msg_gen, func_database, func_errors

logger = logging.getLogger('discord')
logger.setLevel(logging.ERROR)
handler = RotatingFileHandler(filename='data/errors/errors_bot.log', encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

MSG_GENERATOR = func_msg_gen.MessageGenerator()

UserDB = func_database.UserDatabase()


async def get_prefix(bot, message):
    # gets the bot prefix
    prefix = bot_settings.prefix
    prefix += await UserDB.get_user_information_global(message.author.id).distinct("prefix")

    return commands.when_mentioned_or(*prefix)(bot, message)

bot = commands.Bot(command_prefix=get_prefix, description="", case_insensitive=True)


def error_handler(error):
    # error handler
    print("An error occurred:")
    traceback.print_exception(type(error), error, error.__traceback__)
    logger.error(error)
    return False


if __name__ == "__main__":
    # load all modules
    modules = []
    try:
        files = os.listdir("./modules")
        for module in files:
            try:
                if module not in ["__init__.py", "__pycache__"] and module.__contains__(
                    "cmd_"
                ):
                    bot.load_extension(f"modules.{module.replace('.py', '')}")
            except Exception as e:
                error_handler(e)
    except FileNotFoundError:
        files = os.listdir()
        standard_files = ["bot_settings.py", "main_bot.py"]
        for module in files:
            if (
                ".py" in module
                and module not in standard_files
                and module.__contains__("cmd_")
            ):
                try:
                    bot.load_extension(module.replace(".py", ""))
                except Exception as e:
                    error_handler(e)
    except Exception as e:
        error_handler(e)


@bot.event
async def on_ready():
    print(
        f"\nLogged in as: {bot.user} - {bot.user.id}\nLatency: {round(bot.latency *1000)} ms\n"
        f"Connected to {len(bot.guilds)} guilds\nVersion: {discord.__version__}\n"
    )
    # commands
    bot_extensions = bot.extensions
    count_extensions = len(bot_extensions)
    if count_extensions < 2:
        extensions = f"Loaded {count_extensions} module: "
    else:
        extensions = f"Loaded {count_extensions} modules: "
    for extension in bot_extensions.keys():
        extensions = extensions + f", {extension}"
    # set playing status
    await bot.change_presence(
        activity=discord.Game(name=random.choice(bot_settings.default_game)),
        status=discord.Status.online,
    )
    # used for restarts
    file_name = "message_id.json"
    if os.path.exists(file_name):
        with open(file_name, "r") as read_file:
            content = ast.literal_eval(read_file.read())
        channel = bot.get_channel(int(content.get("channel_id")))
        if channel is None:
            channel = bot.get_user(id=int(content.get("channel_id")))
        message = await channel.get_message(int(content.get("message_id")))
        os.remove(file_name)
        await message.edit(content="Successfully restarted!")
        return print("Successfully restarted!")
    return print(f"Successfully logged in and booted...!")


@bot.event
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
        logger.error(ctx.command.qualified_name + ": " + str(error))
        msg = "The error has been reported."
    await MSG_GENERATOR.error_msg(ctx, msg)


loop = asyncio.get_event_loop()


bot.run(bot_settings.token, bot=True, reconnect=True)


def get_bot():
    return bot
