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
    item_msg = await ctx.send(embed=shop_item_embed(
        selected_item,
        guser_information.get("embed_color", bot_settings.embed_color),
        luser_information.get("balance", 0)
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
        if luser_information.get("balance", 0) < store_information["price"]:
            return await MSG.error_msg(
                ctx,
                "You don't have enough money to purchase this item!"
            )
        requirement = store_information["requirement"]
        if requirement:
            if requirement not in [role.id for role in ctx.author.roles]:
                return await MSG.error_msg(ctx, "You don't have the required role for this item!")
        max_amount = store_information["max_amount"]
        if max_amount > 0:
            if user_item:
                if user_item.get("amount", 0) > max_amount:
                    return await MSG.error_msg(ctx, f"You are not allowed to own this item more than "
                                                    f"`{max_amount}` times!")
        if store_information["stock"] == 0:
            return await MSG.error_msg(ctx, "There is no stock left for this item!")
        print(user_item)
        if user_item:
            await USER_DB.user_add_owned_item(user_id=ctx.author.id, server_id=ctx.guild.id,
                                              item_id=selected_item["item_id"])
        else:
            await USER_DB.user_add_item(user_id=ctx.author.id, server_id=ctx.guild.id, item=selected_item)
        await USER_DB.edit_money(user_id=ctx.author.id, server_id=ctx.guild.id, amount=-store_information["price"])
        await ITEM_DB.remove_stock(server_id=ctx.author.id, item_id=selected_item["item_id"])
        return await ctx.send("Successfully purchased the item!")
    else:
        return await MSG.error_msg(ctx, "Invalid response, please try again!")


def shop_item_embed(item: dict, color, user_balance) -> discord.Embed:
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
