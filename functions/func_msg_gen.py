import discord
from naomi_paginator import Paginator

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

    def paginator_handler(self, ctx, base_embed: discord.Embed, items: dict, reactions: list = None,
                          timeout=120, items_per_page=5) -> Paginator:
        paginator = Paginator(ctx=ctx, reactions=reactions, timeout=timeout)
        # default embed
        # split the list into many small lists
        split_lists = self.split_list(list(items.items()), items_per_page)
        # create the embeds
        for i in split_lists:
            embed_copy = base_embed.copy()
            description = "\n".join(f'{setting[0]}: {setting[1]}' for setting in i)
            description = description.replace("[", "").replace("]", "").replace("'", "`")
            embed_copy.description = description
            paginator.add_page(embed_copy)
        return paginator

    @staticmethod
    def split_list(list_input: list, items_per_page: int):
        """Split"""
        list_output = []
        for i in range(0, len(list_input), items_per_page):
            list_output.append(list_input[i:i + items_per_page])
        return list_output
