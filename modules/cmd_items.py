import discord
from discord.ext import commands

import asyncio
import json

from functions import func_database, func_msg_gen, func_setting_helpers

import bot_settings


class ServerItems(commands.Cog, name="Server Items"):
    def __init__(self, bot):
        self.bot = bot
        self.udb = func_database.UserDatabase()
        self.sdb = func_database.ServerDatabase()
        self.idb = func_database.ItemDatabase()
        self.msg = func_msg_gen.MessageGenerator()
        self.helper = func_setting_helpers.SettingHelper(bot)

    @commands.command(name="shop", aliases=["store"])
    @commands.guild_only()
    async def cmd_shop(self, ctx, item: str = None):
        """Buy new items from the servers shop."""
        items = self.idb.get_items(server_id=ctx.guild.id)
        await ctx.send("not implemented currently", item)

    @commands.group(name="item", invoke_without_command=True)
    @commands.guild_only()
    async def cmd_item(self, ctx, item: str = None):
        """Check your items and use them."""
        await ctx.send("not implemented currently", item)

    @cmd_item.command(name="add")
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def cmd_add_item(self, ctx):
        """Add a new server item"""
        item = {
            "server_id": ctx.guild.id,
            "item_id": "",
            "name": "",
            "type": "",
            "description": "",
            "available": "",
            "usable_amount": "",
            "emoji": ""
        }
        setting_txt = {
            "item_id": "Please input an item ID. This has to be unique.",
            "name": "Please input an item name.",
            "type": "Please select one of these item types: `role` or `text`",
            "description": "Please input an item description.",
            "available": "Do you want the item to be available in the shop? Input has to be either `true` or `false`",
            "usable_amount": "Please enter the usable amount. This can be 0 for not usable, -1 for unlimited uses "
                             "or any other number",
            "emoji": "Please enter an emoji for the item. It has to be an emoji from the server or a standard "
                     "discord emoji"
        }
        for setting in item.keys():
            if item[setting] == "":
                response = await self.get_user_input(ctx, setting, setting_txt[setting])
                if response == "":
                    return
                else:
                    item[setting] = response
        duplicate_check = await self.idb.get_item(ctx.guild.id, item["item_id"])
        if duplicate_check:
            await self.msg.error_msg(ctx, "An item with this message ID already exists!")
            return
        # handle role items
        if item.get("type", "") == "role":
            response = await self.get_user_input(ctx, "role_settings", "Please input the role ID.")
            if response == "":
                return
            try:
                role = discord.utils.get(iterable=ctx.guild.roles, id=int(response))
                item["information"] = {"role_id": role.id}
            except Exception as e:
                print(e)
                await self.msg.error_msg(ctx, "Something went wrong! Make sure you have specified a valid role ID.")
                return
        if item.get("type", "") == "text":
            response = await self.get_user_input(ctx, "text_settings",
                                                 "Please input a text which will be used for this text item!")
            item["information"] = {"text": response}
        if item["available"].lower() == "true":
            store_settings = {
                "price": "",
                "stock": "",
                "requirement": "",
                "max_amount": ""
            }
            store_settings_text = {
                "price": "Please input a price for the item.",
                "stock": "Please input the stock for this item.",
                "requirement": "Please input a required role for this item. This can be `none` for no required role.",
                "max_amount": "Please input a max amount of items a user can have in their inventory."
            }
            for store_setting in store_settings.keys():
                response = await self.get_user_input(ctx, store_setting, store_settings_text[store_setting])
                if store_setting == "requirement":
                    if response == "none":
                        store_settings["requirement"] = 0
                    else:
                        try:
                            role = discord.utils.get(iterable=ctx.guild.roles, id=int(response))
                            store_settings["requirement"] = role.id
                        except:
                            await self.msg.error_msg(
                                ctx,
                                "Something went wrong! Make sure you have specified a valid role ID."
                            )
                            return
                else:
                    if response == "":
                        return
                    else:
                        try:
                            store_settings[store_setting] = int(response)
                        except ValueError:
                            await self.msg.error_msg(
                                ctx,
                                f"Something went wrong! Make sure you have specified a valid value "
                                f"for the {store_setting} setting."
                            )
                            return
            item["store"] = store_settings
        await self.idb.create_item(item)
        item.pop("_id")
        await ctx.send(embed=discord.Embed(
            title="Item successfully created!",
            description=f"Item Settings:\n```json\n{json.dumps(item, indent=4)}\n```"
        ))

    async def get_user_input(self, ctx, title: str, text: str) -> str:
        title = title.replace("_", " ").capitalize()
        msg = await ctx.send(embed=discord.Embed(
            title=title,
            description=text,
            color=bot_settings.embed_color
        ))
        try:
            response = await self.bot.wait_for(
                "message", check=lambda m: ctx.author.id == m.author.id and m.channel.id == ctx.channel.id, timeout=60
            )
        except asyncio.TimeoutError:
            await msg.delete()
            await self.msg.error_msg(
                ctx,
                f"Please provide a valid input for {title}. The item creation process has been stopped."
            )
            return ""
        await msg.delete()
        return response.content

    @cmd_item.command(name="list")
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def cmd_list_items(self, ctx):
        """Get a list of all current items."""
        items = await self.idb.get_items(ctx.guild.id)
        base_embed = discord.Embed(
            title="All server items:",
            description=f"Use the `{ctx.prefix}item edit` command to edit items.",
            color=bot_settings.embed_color
        )
        paginator = func_msg_gen.Paginator(ctx, None, 180, None, items_per_page=1)
        embeds = []
        async for item in items:
            embed = base_embed.copy()
            embed.add_field(
                name=f"Item settings for " + item.get("name", "name"),
                value=f"```json\n{json.dumps(item, indent=4)}\n```"
            )
            embeds.append(embed)
        paginator.add_pages(embeds)
        paginator_msg = await paginator.start_paginator()

    @cmd_item.command(name="remove", aliases=["delete"])
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def cmd_remove_item(self, ctx, item: str):
        """Delete a specified item."""
        result = await self.idb.delete_item(ctx.guild.id, item_id=item)
        result = result.deleted_count
        await ctx.send(f"Successfully deleted %s items." % result)

    @cmd_item.command(name="edit")
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def cmd_edit_item(self, ctx, item: str = None):
        """Edit one of the servers items."""
        # TODO: get the item
        await ctx.send("not implemented currently", item)


def setup(bot):
    bot.add_cog(ServerItems(bot))
