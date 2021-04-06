import copy
from asyncio import TimeoutError as AsyncioTimeoutError, FIRST_COMPLETED as ASYNCIO_FIRST_COMPLETED, wait as async_wait
from typing import Union

import discord
from discord.ext import commands

import bot_settings


class MessageGenerator:
    def __init__(self):
        self.color = bot_settings.embed_color
        self.error_embed = 0xff0000
        self.converter = commands.ColourConverter()
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

    async def message_sender(self, ctx, embed: discord.Embed, color=None, file=None) -> discord.Message:
        """Generates the same embed for every command from a dict
        :param file: discord.File
        :type color: object
        :type embed: discord.Embed
        """
        if color is None and embed.color == discord.Embed.Empty:
            colour = await ctx.get_embed_color()
        else:
            colour = color or embed.color
        embed.colour = colour
        return await ctx.send(self.msg_gen(ctx), embed=embed, file=file)

    async def error_msg(self, ctx, msg) -> discord.Message:
        embed = discord.Embed(title="Something went wrong!", description=msg, color=self.error_embed)
        message = f"Error for command: {ctx.command.qualified_name} - **[ {ctx.author} ]**"
        return await ctx.send(message, embed=embed)

    def paginator_handler(self, ctx, base_embed: discord.Embed, items: dict, reactions: list = None,
                          timeout=120, items_per_page=5, func=None, close_after_func=True, func_check=None):
        """ Handles the paginator initiation
        :param ctx: commands.Context
            discord Context
        :param items
        :param func: function
            function to be called on messages
        :param reactions: list
            Exactly 3 reactions
        :param func_check: func
            check for on_msg
        :param close_after_func: bool
        :param timeout: int
        :param items_per_page: int
            Max 10 items per page
        :type base_embed: discord.Embed
        """
        paginator = Paginator(ctx=ctx, reactions=reactions, timeout=timeout, func=func,
                              close_after_func=close_after_func, func_check=func_check, items=items)
        # default embed
        # split the list into many small lists
        split_lists = self.split_list(list(items.items()), items_per_page)
        # create the embeds
        for item in split_lists:
            embed_copy = base_embed.copy()
            description = "\n".join(f'{self.digits[item.index(setting) + 1] if func else ""} '
                                    f'**{setting[0].capitalize()}**: '
                                    f'{setting[1] if not None else "`Not set`"}' for setting in item)
            description = description.replace("[", "").replace("]", "").replace("'", "").replace("_", " ") or "Not set"
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
                 func=None, close_after_func=True, func_check=None, items=None):
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
        if items is None:
            items = {}
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
        self.author_check_reaction = lambda r, u: u.id == self.ctx.author.id \
                                                  and r.emoji in self.reactions and r.message.id == self.controller.id
        self.author_check_message = lambda m: self.ctx.author.id == m.author.id \
                                              and m.channel.id == self.controller.channel.id

    async def close_paginator(self):
        # cleanup
        try:
            await self.controller.delete()
            del self.reactions
            del self.pages
            del self.current
            del self.ctx
            del self.timeout
            del self.func
            del self.close_after_func
        except Exception:
            pass

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
        information_value = f"{'Respond with the numbers to change the settings or exit to close the menu.'}" \
            if self.func else ""
        if not pages[self.current].fields:
            pages[self.current].add_field(
                name="Information:",
                value=f"Page: {self.current + 1}/{len(self.pages)}\n{information_value}"
            )
        self.controller = await self.msg.message_sender(ctx=self.ctx, embed=pages[0])
        for emoji in self.reactions:
            await self.controller.add_reaction(emoji)

        while True:
            try:
                # handle reactions
                tasks = [
                    self.ctx.bot.wait_for('reaction_add',
                                          timeout=self.timeout, check=self.author_check_reaction),
                    self.ctx.bot.wait_for('reaction_remove',
                                          timeout=self.timeout, check=self.author_check_reaction)]
                # handle messages
                if self.func_check:
                    tasks.append(
                        self.ctx.bot.wait_for("message",
                                              timeout=self.timeout, check=self.func_check and self.author_check_message)
                    )

                tasks_result, tasks = await async_wait(tasks, return_when=ASYNCIO_FIRST_COMPLETED)

                for task in tasks:
                    task.cancel()
                for task in tasks_result:
                    response = await task
            except AsyncioTimeoutError:
                break

            if type(response) == tuple:
                if response[0].emoji == self.reactions[0]:
                    self.current = self.current - 1 if self.current > 0 else len(self.pages) - 1
                    await self.edit_controller(embed=self.pages[self.current])

                elif response[0].emoji == self.reactions[1]:
                    break

                elif response[0].emoji == self.reactions[2]:
                    self.current = self.current + 1 if self.current < len(self.pages) - 1 else 0
                    await self.edit_controller(embed=self.pages[self.current])
            else:
                if self.func:
                    await self.func(response, copy.copy(self))
                if self.close_after_func:
                    await self.close_paginator()
                    break
        await self.close_paginator()

    async def edit_controller(self, embed):
        information_value = f"{'Respond with the numbers to change the settings or exit to close the menu.'}" \
            if self.func else ""
        if len(self.pages) > 1 and not embed.fields:
            embed.add_field(
                name="Information:",
                value=f"Page: {self.current + 1}/{len(self.pages)}\n{information_value}"
            )
        await self.controller.edit(embed=embed)
