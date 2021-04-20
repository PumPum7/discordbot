import discord

import bot_settings

import func_database
import func_msg_gen

MSG = func_msg_gen.MessageGenerator()
ITEM_DB = func_database.ItemDatabase()
USER_DB = func_database.UserDatabase()


def shop_embed_generator(items: list, color, user_information: dict) -> [discord.Embed]:
    try:
        item_length: int = len(items)
    except TypeError:
        item_length: int = 0
    if item_length == 0:
        empty_embed = discord.Embed(
            title="Item shop",
            description="There are no items available in this server!"
        )
        return [empty_embed]
    items = MSG.split_list(items, 6)
    embeds = []
    base_embed = discord.Embed(
        title="Item Shop",
        description=f"Respond with the number next to the item to buy it.\n"
                    f"Current Balance: {user_information.get('balance', 0)} {bot_settings.currency_name}",
        color=color
    )
    for item_page in items:
        item_embed = base_embed.copy().add_field(
            name="Items:",
            value="\n".join([f"{bot_settings.digits[item_page.index(i) + 1]} {i.get('emoji', '')} "
                             f"**{i.get('name')}**\n"
                             f"`{i['store'].get('price', 0)}` {bot_settings.currency_name} | Type `{i.get('type')}`"
                             for i in item_page])
        )
        embeds.append(item_embed)
    return embeds


async def shop_choice_handler(response: discord.Message, self_object):
    items: list = self_object.items
    cur_page: int = self_object.current
    ctx = self_object.ctx
    guser_information, luser_information = await ctx.get_user_information()
    try:
        selected_item: dict = items[(int(response.content) + (cur_page * self_object.items_per_page)) - 1]
    except ValueError or TypeError:
        return await MSG.error_msg(ctx, "Invalid item choice. "
                                        "Please only reply with the number next to the item!")
    user_item = {}
    for i in luser_information.get("items", []):
        if i.get("item_id", "") == selected_item["item_id"]:
            user_item = i
            break
    item_msg = await ctx.send(embed=shop_item_embed(
        selected_item,
        guser_information.get("embed_color", bot_settings.embed_color),
        luser_information.get("balance", 0),
        user_item
    ))
    try:
        response = await ctx.bot.wait_for(
            "message",
            check=lambda m: ctx.author.id == m.author.id
                            and m.channel.id == ctx.channel.id
                            and m.content.lower() in ["confirm", "cancel"],
            timeout=180
        )
        response = response.content.lower()
    except Exception:
        return await MSG.error_msg(ctx, "Item purchase timed out!")
    store_information = selected_item["store"]
    if response == "cancel":
        return await ctx.send("Successfully cancelled the purchase!")
    if response == "confirm":
        user_items = luser_information.get("items", [])
        user_item = filter(lambda i: i.get("item_id") == selected_item["item_id"], user_items)
        try:
            user_item = [i for i in user_item][0]
        except IndexError:
            user_item = {}
        # check if the user has enough funds to buy the item
        if luser_information.get("balance", 0) < store_information["price"]:
            return await MSG.error_msg(
                ctx,
                "You don't have enough money to purchase this item!"
            )
        # check if the user meets the requirement
        requirement = store_information["requirement"]
        if requirement:
            if requirement not in [role.id for role in ctx.author.roles]:
                return await MSG.error_msg(ctx, "You don't have the required role for this item!")
        # check if the user has not bought more than the max amount of items
        max_amount = store_information["max_amount"]
        if max_amount > 0:
            if user_item:
                if user_item.get("amount", 0) > max_amount:
                    return await MSG.error_msg(ctx, f"You are not allowed to own this item more than "
                                                    f"`{max_amount}` times!")
        # check if the item is still available
        if store_information["stock"] == 0:
            return await MSG.error_msg(ctx, "There is no stock left for this item!")
        # add the item to the user
        await add_item(ctx, user_item, selected_item)
        await USER_DB.edit_money(user_id=ctx.author.id, server_id=ctx.guild.id, amount=-store_information["price"])
        await ITEM_DB.remove_stock(server_id=ctx.author.id, item_id=selected_item["item_id"])
        return await ctx.send("Successfully purchased the item!")
    else:
        return await MSG.error_msg(ctx, "Invalid response, please try again!")


async def add_item(ctx, user_item: dict, selected_item: dict, user_id: int = None):
    if user_item:
        await USER_DB.user_change_usage_amount_item(user_id=user_id or ctx.author.id, server_id=ctx.guild.id,
                                                    item_id=selected_item["item_id"], usage=0, amount=1)
    else:
        await USER_DB.user_add_item(user_id=user_id or ctx.author.id, server_id=ctx.guild.id, item=selected_item)


async def remove_item(ctx, user_item: dict, selected_item: dict, user_id: int = None):
    if user_item:
        await USER_DB.user_change_usage_amount_item(user_id=user_id or ctx.author.id, server_id=ctx.guild.id,
                                                    item_id=selected_item["item_id"], usage=0, amount=-1)
    else:
        await USER_DB.remove_item(user_id=user_id or ctx.author.id, server_id=ctx.guild.id,
                                  item_id=selected_item["item_id"])


def shop_item_embed(item: dict, color, user_balance: int, user_item: dict) -> discord.Embed:
    store = item["store"]
    stock = store.get('stock', 0)
    embed = discord.Embed(
        title=f"{item['emoji']} {item['name']}",
        description=f"```{item['description']}```",
        color=color
    )
    embed.add_field(
        name="Item price:",
        value=f"{store['price']} {bot_settings.currency_name}",
        inline=True,
    )
    embed.add_field(
        name="Your balance:",
        value=f"{user_balance} {bot_settings.currency_name}",
        inline=True
    )
    embed.add_field(
        name="Remaining Stock:",
        value=f"{stock}" if stock > 0 else "Unlimited stock" if stock != 0 else "No stock remaining",
        inline=False
    )
    if user_item.get("amount", 0):
        embed.add_field(
            name="Inventory:",
            value=f"You currently own this item `{user_item.get('amount')}` times!",
            inline=True
        )
    if store.get("requirement", 0):
        embed.add_field(
            name="Requirement:",
            value=f"You are required to have the <@&{store.get('requirement')}> role to buy this item.",
            inline=True
        )
    embed.set_footer(
        text='Reply with "confirm" to buy the item or "cancel" to cancel the purchase!'
    )
    return embed


def item_embed_generator(items: list, color) -> [discord.Embed]:
    try:
        item_length: int = len(items)
    except TypeError:
        item_length: int = 0
    if item_length == 0:
        empty_embed = discord.Embed(
            title="Item Menu",
            description="You don't own any items currently!"
        )
        return [empty_embed]
    items = MSG.split_list(items, 6)
    embeds = []
    base_embed = discord.Embed(
        title="Item Menu",
        description=f"Respond with the number next to the item to use it!",
        color=color
    )
    for item_page in items:
        item_embed = base_embed.copy().add_field(
            name="Items:",
            value="\n".join([f"{bot_settings.digits[item_page.index(i) + 1]} **{i.get('name')}**\n"
                             f"`x{i.get('amount', 0)}` | Used {i.get('usage', 0)} times"
                             for i in item_page])
        )
        embeds.append(item_embed)
    return embeds


def item_usage_embed(user_item: dict, item: dict, color) -> discord.Embed:
    embed = discord.Embed(
        title="Item Menu",
        description=f"You are about to use the item {user_item.get('name')}! "
                    f"Reply with `use` to use this item or `cancel` to cancel.",
        color=color
    )
    usable_amount = item.get('usable_amount', 0)
    embed.add_field(
        name="Information:",
        value=f"You currently own this item `{user_item.get('amount', 0)}` times.\n"
              f"You have used this item `{user_item.get('usage', 0)}/"
              f"{usable_amount if not usable_amount == '-1' else 'unlimited'}` times."
    )
    embed.add_field(
        name="Item description:",
        value=item.get("description", "No description set.")
    )
    embed.add_field(name="Item ID:", value=f"`{user_item.get('item_id')}`")
    return embed


async def item_choice_handler(response: discord.Message, self_object):
    items: list = self_object.items
    cur_page: int = self_object.current
    ctx = self_object.ctx
    guser_information, luser_information = await ctx.get_user_information()
    try:
        selected_item: dict = items[(int(response.content) + (cur_page * self_object.items_per_page)) - 1]
    except ValueError or TypeError:
        return await MSG.error_msg(ctx, "Invalid item choice. "
                                        "Please only reply with the number next to the item!")
    item_information = await ITEM_DB.get_item(ctx.guild.id, selected_item["item_id"])
    item_msg = await ctx.send(embed=item_usage_embed(
        selected_item,
        item_information,
        guser_information.get("embed_color", bot_settings.embed_color),
    ))
    try:
        response = await ctx.bot.wait_for(
            "message",
            check=lambda m: ctx.author.id == m.author.id
                            and m.channel.id == ctx.channel.id
                            and m.content.lower() in ["use", "cancel"],
            timeout=180
        )
        response = response.content.lower()
    except Exception:
        return await MSG.error_msg(ctx, "Item usage timed out!")
    store_information = item_information["store"]
    if response == "cancel":
        return await ctx.send("Successfully cancelled the use of this item!")
    if response == "use":
        # check if the user really has the item
        if selected_item["amount"] < 1:
            return await MSG.error_msg(ctx, "You don't own this item!")
        # check if the user can use this item again
        usable_amount = int(item_information.get("usable_amount", 0))
        if selected_item["usage"] >= usable_amount >= 0:
            if selected_item["amount"] > 1:
                await USER_DB.user_change_usage_amount_item(ctx.author.id, ctx.guild.id, selected_item["item_id"],
                                                            -int(item_information.get("usable_amount", 0)), -1)
            else:
                await USER_DB.remove_item(ctx.author.id, ctx.guild.id, selected_item["item_id"])
                return await MSG.error_msg(ctx, "You cannot use this item anymore!")
        # do the role type stuff for the item
        if item_information.get("type") == "role":
            role_id = item_information["information"].get("role_id", 0)
            role = discord.utils.get(iterable=ctx.guild.roles, id=role_id)
            if not role:
                return await MSG.error_msg(ctx, "Something went wrong while assigning the role!")
            if role in ctx.author.roles:
                await ctx.author.remove_roles(role, reason="Item usage")
                description = f"You now no longer have the {role.mention} role assigned!"
            else:
                await ctx.author.add_roles(role, reason="Item usage")
                await USER_DB.user_change_usage_amount_item(ctx.author.id, ctx.guild.id, selected_item["item_id"],
                                                            1, 0)
                description = f"You now have the {role.mention} role assigned!"
            return await ctx.send(
                embed=discord.Embed(
                    title="Successfully used the item!",
                    description=description
                )
            )
        elif item_information.get("type") == "text":
            await ctx.send(item_information["information"].get("text", "No text was specified!"))
            await USER_DB.user_change_usage_amount_item(ctx.author.id, ctx.guild.id, selected_item["item_id"], 1, 0)
    else:
        return await MSG.error_msg(ctx, "Invalid response, please try again!")


def find_item_from_id(items: list, input_id: str) -> dict:
    for user_item in items:
        if user_item["item_id"] == input_id:
            return user_item
    return {}
