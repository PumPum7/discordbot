from discord.ext import commands


class OwnerCommands(commands.Cog, name="Owner commands"):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="sbot", aliases=["botsettings"], invoke_without_command=True)
    @commands.is_owner()
    async def cmd_bot_settings(self, ctx):
        await ctx.send_help(self.cmd_bot_settings)

    @cmd_bot_settings.command(name="reload")
    async def cmd_bot_reload_cog(self, ctx, cog):
        try:
            self.bot.reload_extension(f"modules.cmd_{cog}")
        except Exception as e:
            return await ctx.send(f"Something went wrong...\n{e}")
        return await ctx.send(f'Successfully reloaded {cog}!')

    @cmd_bot_settings.command(name="error")
    async def cmd_raise_error(self, ctx):
        raise Exception("test")


def setup(bot):
    bot.add_cog(OwnerCommands(bot))
