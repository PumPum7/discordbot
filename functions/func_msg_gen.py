import discord
import bot_settings


class MessageGenerator:
    def __init__(self):
        self.color = bot_settings.embed_color
        self.error_embed = 0xff0000

    def msg_gen(self, ctx):
        return f"Command: {ctx.command.qualified_name} - **[ {ctx.author} ]**"

    async def message_sender(self, ctx, embed: discord.Embed, color=None):
        """Generates the same embed for every command from a dict"""
        embed.color = discord.Color(self.color) if color is None else color
        return await ctx.send(self.msg_gen(ctx), embed=embed)

    async def error_msg(self, ctx, msg):
        embed = discord.Embed(title="Something went wrong!", description=msg, color=self.error_embed)
        message = f"Error for command: {ctx.command.qualified_name} - **[ {ctx.author} ]**"
        return await ctx.send(message, embed=embed)
