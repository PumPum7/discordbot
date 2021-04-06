from discord.ext import commands


class EconomyError(commands.CommandError):
    pass


class TooManyItems(commands.CommandError):
    pass


class DuplicateItem(commands.CommandError):
    pass
