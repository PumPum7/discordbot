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
from functions import func_msg_gen, func_database, func_context, func_prefix

logger = logging.getLogger('discord')
logger.setLevel(logging.ERROR)
handler = RotatingFileHandler(filename='data/errors/errors_bot.log', encoding='utf-8', mode='a')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

MSG_GENERATOR = func_msg_gen.MessageGenerator()

UserDB = func_database.UserDatabase()
ServerDB = func_database.ServerDatabase()
Prefix = func_prefix.Prefix()


class FullBot(commands.Bot):
    def __init__(self, command_prefix, **options):
        super().__init__(command_prefix, **options)

    async def get_context(self, message, *, cls=func_context.FullContext):
        return await super().get_context(message, cls=cls)


async def get_prefix(bot, message):
    # gets the bot prefix
    prefix = await Prefix.get_prefix(message.author.id, message.guild.id)
    return commands.when_mentioned_or(*prefix)(bot, message)

bot = FullBot(command_prefix=get_prefix, description="", case_insensitive=True)


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
    bot.load_extension('jishaku')


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


loop = asyncio.get_event_loop()


bot.run(bot_settings.token, bot=True, reconnect=True)


def get_bot():
    return bot
