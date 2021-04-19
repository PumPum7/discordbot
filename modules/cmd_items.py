import discord
from discord.ext import commands

import asyncio
import json
import re

from functions import func_database, func_msg_gen, func_setting_helpers, func_items

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
    async def cmd_shop(self, ctx, *item: str):
        """Buy new items from the servers shop."""
        if len(item) == 0:
            items = await self.idb.get_shop_items(server_id=ctx.guild.id)
        else:
            item = "".join(item)
            items = await self.idb.search_shop_items(server_id=ctx.guild.id, search=item)
        item_list = []
        async for item in items:
            item_list.append(item)
        user_information = await ctx.get_user_information()
        color = user_information[0].get("embed_color", bot_settings.embed_color)
        embeds = func_items.shop_embed_generator(item_list, color, user_information[1])
        paginator = func_msg_gen.Paginator(ctx, timeout=180, items=item_list, items_per_page=6,
                                           func=func_items.shop_choice_handler, close_after_func=True,
                                           func_check=lambda m: 0 < int(m.content) < 7)
        for embed in embeds:
            paginator.add_page(embed)
        await paginator.start_paginator(0)

    @commands.group(name="item", invoke_without_command=True)
    @commands.guild_only()
    async def cmd_item(self, ctx, *item_search):
        """Check your items and use them. Search supports regex search"""
        found_items: list = []
        item_search: str = " ".join(item_search).lower()
        guser_information, luser_information = await ctx.get_user_information()
        items = luser_information.get("items", [])
        if item_search:
            for item in items:
                if re.search(item_search, item.get("name", "").lower()):
                    found_items.append(item)
        else:
            found_items = items
        color = guser_information.get("embed_color", bot_settings.embed_color)
        embeds = func_items.item_embed_generator(found_items, color)
        paginator = func_msg_gen.Paginator(ctx, timeout=180, items=found_items, items_per_page=6,
                                           func=func_items.item_choice_handler, close_after_func=True,
                                           func_check=lambda m: 0 < int(m.content) < 7)
        for embed in embeds:
            paginator.add_page(embed)
        await paginator.start_paginator(0)

    @cmd_item.command(name="transfer")
    @commands.guild_only()
    async def cmd_item_transfer(self, ctx, user: discord.Member, item: str):
        """Transfer an item to another user. You have to use the item id here
        (you can find it in the item command menu)"""
        if user == ctx.author:
            return await self.msg.error_msg(ctx, "You cannot transfer an item to yourself!")
        if user.bot:
            return await self.msg.error_msg(ctx, "You cannot transfer an item to a bot!")
        guser_information, luser_information = await ctx.get_user_information()
        found_item = func_items.find_item_from_id(luser_information.get("items", []), item)
        if not found_item:
            return await self.msg.error_msg(ctx, f"No item was found with the id `{item}`")
        if found_item["amount"] == 0:
            return await self.msg.error_msg(ctx, "You don't have this item anymore!")
        msg = await ctx.send(
            embed=discord.Embed(
                title="Transfer menu",
                description=f"Would you like to trade the item `{found_item['name']}` with the user {user.mention}?\n"
                            f"You currently have this item `{found_item['amount']}` times",
                color=discord.Color.green()
            ).set_footer(
                text="Reply with confirm or cancel."
            )
        )
        try:
            response = await ctx.bot.wait_for(
                "message",
                check=lambda m: m.author == ctx.author
                                and m.channel == ctx.channel
                                and m.content.lower() in ["confirm", "cancel"],
                timeout=180
            )
        except asyncio.TimeoutError:
            await msg.delete()
            return await self.msg.error_msg(ctx, "The transfer has timed out!")
        response = response.content.lower()
        if response == "confirm":
            try:
                receiver_information = await self.udb.get_user_information(user.id, ctx.guild.id).to_list(length=1)
                receiver_information = receiver_information[0]
                receiver_item = func_items.find_item_from_id(receiver_information.get("items", []),
                                                             found_item["item_id"])
                print(receiver_item)
            except IndexError:
                receiver_item = {}
            print(found_item, receiver_item)
            await func_items.remove_item(ctx, found_item, found_item)
            await func_items.add_item(ctx, receiver_item, found_item, user_id=user.id)
            return await msg.edit(
                embed=discord.Embed(
                    title="Successful transfer!",
                    description=f"{user.mention} has successfully received your `{found_item['name']}` item!",
                    color=discord.Color.green()
                )
            )
        return await msg.edit(
            embed=discord.Embed(
                title="Transfer successfully cancelled!",
                description=f"{user.mention} has not received your `{found_item['name']}` item!",
                color=discord.Color.red()
            )
        )

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
                             "or any other number.",
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
                "stock": "Please input the stock for this item. -1 will set the stock to unlimited ",
                "requirement": "Please input a required role for this item. This can be `none` for no required role.",
                "max_amount": "Please input a max amount of items a user can have in their inventory. "
                              "This can be 0 for not buyable, -1 for unlimited or any other number."
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
                name=f"Item settings for " + item.get("name", "Name"),
                value=f"```json\n{json.dumps(item, indent=4)}\n```"
            )
            embeds.append(embed)
        paginator.add_pages(embeds)
        await paginator.start_paginator()

    @cmd_item.command(name="remove", aliases=["delete"])
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def cmd_remove_item(self, ctx, item: str):
        """Delete a specified item."""
        result = await self.idb.delete_item(ctx.guild.id, item_id=item)
        result = result.deleted_count
        if result:
            return await ctx.send(f"Successfully deleted the item {item}!")
        return await ctx.send(f"Failed to delete the item {item}! Please make sure that the item is correct")

    @cmd_item.command(name="edit")
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def cmd_edit_item(self, ctx, item: str = None):
        """Edit one of the servers items."""
        # TODO: get the item
        await ctx.send("not implemented currently", item)


def setup(bot):
    bot.add_cog(ServerItems(bot))
