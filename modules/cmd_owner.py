from discord.ext import commands


class OwnerCommands(commands.Cog):
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
        except:
            return await ctx.send("Something went wrong...")
        return await ctx.send(f'Successfully reloaded {cog}!')


def setup(bot):
    bot.add_cog(OwnerCommands(bot))