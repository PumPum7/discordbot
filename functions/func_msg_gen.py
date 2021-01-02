import discord
import bot_settings


class MessageGenerator:
    def __init__(self):
        self.color = bot_settings.embed_color
        self.error_embed = 0xff0000

    @staticmethod
    def msg_gen(ctx) -> str:
        return f"Command: {ctx.command.qualified_name} - **[ {ctx.author} ]**"

    async def message_sender(self, ctx, embed: discord.Embed, color=None) -> discord.Message:
        """Generates the same embed for every command from a dict
        :type ctx: commands.context
        :type color: object
        :type embed: discord.Embed
        """
        if color is None:
            embed.colour = discord.Color(self.color)
        else:
            embed.colour = color
        return await ctx.send(self.msg_gen(ctx), embed=embed)

    async def error_msg(self, ctx, msg) -> discord.Message:
        embed = discord.Embed(title="Something went wrong!", description=msg, color=self.error_embed)
        message = f"Error for command: {ctx.command.qualified_name} - **[ {ctx.author} ]**"
        return await ctx.send(message, embed=embed)
