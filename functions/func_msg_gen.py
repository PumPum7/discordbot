import discord
from discord.ext import commands
from asyncio import TimeoutError as AsyncioTimeoutError
from asyncio import wait as asyncioWait
from asyncio import FIRST_COMPLETED as ASYNCIO_FIRST_COMPLETED
from typing import Union

import bot_settings


class MessageGenerator:
    def __init__(self):
        self.color = bot_settings.embed_color
        self.error_embed = 0xff0000
        self.digits = {
            10: ":keycap_10:",
            9: ":nine:",
            8: ":eight:",
            7: ":seven:",
            6: ":six:",
            5: ":five:",
            4: ":four:",
            3: ":three:",
            2: ":two:",
            1: ":one:"
        }

    @staticmethod
    def msg_gen(ctx) -> str:
        return f"Command: {ctx.command.qualified_name} - **[ {ctx.author} ]**"

    async def message_sender(self, ctx: commands.Context, embed: discord.Embed, color=None) -> discord.Message:
        """Generates the same embed for every command from a dict
        :type ctx: commands.Context
        :type color: object
        :type embed: discord.Embed
        """
        if color is None and embed.color == discord.Embed.Empty:
            embed.colour = discord.Color(self.color)
        else:
            embed.colour = color or embed.color
        return await ctx.send(self.msg_gen(ctx), embed=embed)

    async def error_msg(self, ctx, msg) -> discord.Message:
        embed = discord.Embed(title="Something went wrong!", description=msg, color=self.error_embed)
        message = f"Error for command: {ctx.command.qualified_name} - **[ {ctx.author} ]**"
        return await ctx.send(message, embed=embed)

    def paginator_handler(self, ctx, base_embed: discord.Embed, items: dict, reactions: list = None,
                          timeout=120, items_per_page=5, func=None, close_after_func=True, func_check=None):
        """ Handles the paginator initiation
        :param items
            Max 10 items per page
        :param func: function
            function to be called on messages
        :param reactions: list
            Exactly 3 reactions
        :param func_check: func
            check for on_msg
        :param close_after_func: bool
        :param timeout: int
        :param items_per_page: int
        :type base_embed: discord.Embed
        """
        paginator = Paginator(ctx=ctx, reactions=reactions, timeout=timeout, func=func,
                              close_after_func=close_after_func, func_check=func_check, items=items)
        # default embed
        # split the list into many small lists
        split_lists = self.split_list(list(items.items()), items_per_page)
        # create the embeds
        for i in split_lists:
            embed_copy = base_embed.copy()
            description = "\n".join(f'{self.digits[i.index(setting) + 1]} {setting[0].capitalize()}: {setting[1]}'
                                    for setting in i)
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


class Paginator:
    def __init__(self, ctx: commands.Context, reactions: Union[list, tuple] = None, timeout: int = 120,
                 func=None, close_after_func=True, func_check=None, items: dict = {}):
        """

        Parameters
        ----------
        ctx : commands.Context
          Current command context.
        reactions : Optional[Union[tuple, list]]
          Custom reaction emojis for paginator.
          [left_arrow, destroy_embed, right_arrow] - only 3 emojis.
        timeout : int
          Timeout in seconds (default: 120)
        func

        """
        self.controller = None
        self.reactions = reactions or ('⬅', '⏹', '➡')
        self.pages = []
        self.current = 0
        self.ctx = ctx
        self.timeout = timeout
        self.func = func
        self.close_after_func = close_after_func
        self.func_check = func_check
        if not self.func_check:
            self.func_check = lambda m: self.ctx.author.id == m.author.id \
                                        and m.channel.id == self.controller.channel.id
        self.msg = MessageGenerator()
        self.items = items

    async def close_paginator(self):
        try:
            await self.controller.delete()
        except Exception:
            pass
        # cleanup
        del self.reactions; del self.pages; del self.current; del self.ctx; del self.timeout
        del self.func; del self.close_after_func

    def add_page(self, embed: discord.Embed):
        self.pages.append(embed)

    def add_pages(self, embeds: list[discord.Embed]):
        self.pages += embeds

    def clear_pages(self):
        self.pages = []

    async def start_paginator(self, start_page: int = 0):
        pages = self.pages[start_page:] + self.pages[:start_page]
        if len(pages) != len(self.pages):
            raise IndexError(f"{start_page} is not a valid starting page!")

        self.controller = await self.msg.message_sender(ctx=self.ctx, embed=pages[0])
        for emoji in self.reactions:
            await self.controller.add_reaction(emoji)
        author_check = lambda r, u: u.id == self.ctx.author.id \
                                    and r.emoji in self.reactions and r.message.id == self.controller.id
        while True:
            try:
                tasks = [
                    self.ctx.bot.wait_for('reaction_add',
                                          timeout=self.timeout, check=author_check),
                    self.ctx.bot.wait_for('reaction_remove',
                                          timeout=self.timeout, check=author_check)]
                if self.func_check:
                    tasks.append(
                        self.ctx.bot.wait_for("message",
                                              timeout=self.timeout, check=self.func_check)
                    )

                tasks_result, tasks = await asyncioWait(tasks, return_when=ASYNCIO_FIRST_COMPLETED)

                for task in tasks:
                    task.cancel()
                for task in tasks_result:
                    response = await task
            except AsyncioTimeoutError:
                break

            if type(response) == tuple:
                if response[0].emoji == self.reactions[0]:
                    self.current = self.current - 1 if self.current > 0 else len(self.pages) - 1
                    await self.controller.edit(embed=self.pages[self.current])

                elif response[0].emoji == self.reactions[1]:
                    break

                elif response[0].emoji == self.reactions[2]:
                    self.current = self.current + 1 if self.current < len(self.pages) - 1 else 0
                    await self.controller.edit(embed=self.pages[self.current])
            else:
                await self.func(response, self)
                if self.close_after_func:
                    break
        await self.close_paginator()

