from discord.ext import commands

from functions import func_msg_gen


class BasicCommands(commands.Cog, name="Basic Commands"):
    def __init__(self, bot):
        self.bot = bot
        self.msg_gen = func_msg_gen.MessageGenerator()

    @commands.command(name="ping")
    async def cmd_ping(self, ctx):
        """Pong!"""
        return await ctx.send(f"Pong! {round(self.bot.latency * 1000)}ms")


def setup(bot):
    bot.add_cog(BasicCommands(bot))
