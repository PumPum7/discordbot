import discord
from discord.ext import commands

import asyncio
import datetime
import random
import typing

from functions import func_msg_gen, func_economy, func_database

import bot_settings


class EconomyCommands(commands.Cog, name="Economy Commands"):
    def __init__(self, bot):
        self.bot = bot
        self.msg = func_msg_gen.MessageGenerator()
        self.bj_reactions = {"🇭": "hit", "🇸": "stand", "🇩": "double down"}
        bj_embed = discord.Embed(
            title="Blackjack:",
            description=func_economy.bj_string_generator(self.bj_reactions)
        )
        bj_embed.set_footer(
            text="Play by pressing with the reactions below:"
        )
        self.bj_embed = bj_embed
        self.udb = func_database.UserDatabase()
        self.cur = bot_settings.currency_name  # TODO: change to use server setting

    @commands.command(name="balance", aliases=["wallet", "bal"])
    async def cmd_balance(self, ctx, user: discord.Member = None):
        """Check another users balance."""
        user = user or ctx.author
        information = await self.udb.get_user_information(user.id, ctx.guild.id).to_list(length=1)
        balance = information[0].get('balance', 0) if information else 0
        embed = discord.Embed(
            title=f"{user.display_name}'s balance:",
            description=f"> {balance}{self.cur}"
        )
        await self.msg.message_sender(ctx, embed)

    @staticmethod
    def blackjack_msg_updater(msg: discord.Message, hand: dict) -> discord.Embed:
        embed = msg.embeds[0]
        fields = embed.fields
        embed.clear_fields()
        embed.add_field(
            name=fields[0].name,
            value=func_economy.bj_field_generator("human", hand)
        )
        embed.add_field(
            name=fields[1].name,
            value=func_economy.bj_field_generator("bot", hand)
        )
        return embed

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.command(name="blackjack", aliases=["bj"])
    async def cmd_blackjack(self, ctx, bet_: func_economy.LocalBalance):
        """Play blackjack with this command."""
        hand = {'bot': [], 'human': []}
        suits = ['c', 'h', 'd', 's']
        deck = []
        bet = bet_[0]
        balance = bet_[1]
        for suit in suits:
            for rank in range(1, 14):
                deck.append(func_economy.Card(rank, suit))
        # give out the cards
        random.shuffle(deck)
        hand['human'].append(deck.pop(0))
        hand['bot'].append(deck.pop(0))

        hand['human'].append(deck.pop(0))
        hand['bot'].append(deck.pop(0))
        # create the embed
        start_embed = self.bj_embed.copy()
        start_embed.add_field(
            name=ctx.author,
            value=func_economy.bj_field_generator("human", hand)
        )
        start_embed.add_field(
            name="Bot",
            value=func_economy.bj_field_generator("bot", {"bot": [hand['bot'][0]]})
        )
        msg = await self.msg.message_sender(ctx, embed=start_embed)
        for i in self.bj_reactions.keys():
            if i == "🇩" and bet * 2 > balance:
                pass
            else:
                await msg.add_reaction(i)
        playing = True
        player_busted = False
        while playing:
            # wait for reactions (15 sec timeout)
            try:
                reaction, user = await self.bot.wait_for("reaction_add",
                                                         check=lambda reaction_, user_:
                                                         user_ == ctx.author
                                                         and reaction_.emoji in self.bj_reactions.keys(),
                                                         timeout=20.0)
            except asyncio.TimeoutError:
                await self.udb.edit_money(ctx.author.id, ctx.guild.id, -bet)
                return await self.msg.error_msg(ctx, "You only have 20 seconds to react."
                                                     "The money has been deducted from your balance.")
            # blackjack reaction handler
            if self.bj_reactions[reaction.emoji] == "hit":
                hand['human'].append(deck.pop(0))
                if func_economy.bj_hand_counter(hand['human']) > 21:
                    player_busted = True
                    playing = False
                else:
                    await msg.remove_reaction(emoji=reaction.emoji, member=ctx.author)
                    await msg.edit(embed=self.blackjack_msg_updater(msg, hand))
            elif self.bj_reactions[reaction.emoji] == "stand":
                playing = False
            elif self.bj_reactions[reaction.emoji] == "double down":
                if func_economy.bj_hand_counter(hand['human']) in [11, 10, 9] and \
                        bet * 2 < balance:
                    hand['human'].append(deck.pop(0))
                    bet *= 2
                    playing = False
            else:
                pass
        # bot hands handler
        bot_busted = False
        if not player_busted:
            # generates the bots hand
            hand, deck, bot_busted = func_economy.bj_handle_bot_cards(hand, deck)
        # handler for winner
        text, win, bet_edited = func_economy.bj_winner_handler(hand, player_busted, bot_busted, bet)
        # sends the embeds and changes the currency
        embed = self.blackjack_msg_updater(msg, hand)
        embed.description = text.format(bet_edited)
        embed.colour = discord.Color.green() if win else discord.Color.red()
        await self.udb.edit_money(ctx.author.id, ctx.guild.id, bet_edited)
        return await msg.edit(embed=embed, content=msg.content)

    @commands.command(name="claim", aliases=["work"])
    async def cmd_daily(self, ctx, user_: discord.User = None) -> discord.Message:
        """Earn money."""
        user = user_ or ctx.author
        user_roles = [i.id for i in user.roles]

        server_information = await ctx.get_server_information()
        amount = server_information.get("income_daily", bot_settings.default_income["income_daily"])
        cooldown = server_information.get("income_daily_cooldown", bot_settings.default_income["income_daily_cooldown"])
        role_multiplier = server_information.get("income_multiplier_roles",
                                                 bot_settings.default_income["income_multiplier_roles"])
        multiplier = 1
        for role in [i for i in role_multiplier]:
            if role["role_id"] in user_roles:
                multiplier = role["value"]
        amount *= multiplier
        if user.bot:
            return await self.msg.error_msg(ctx, "Bot accounts can't get money!")
        # check if they cna claim it again
        information = await ctx.get_user_information()
        try:
            last_claim: datetime.datetime = information[1].get("claimed_daily", False)
        except IndexError:
            last_claim: bool = False
        if last_claim:
            claimed_daily = last_claim + datetime.timedelta(hours=cooldown) > datetime.datetime.utcnow()
        else:
            claimed_daily = False
        embed = discord.Embed()
        if not claimed_daily:
            await self.udb.claim_daily(ctx.author.id, user.id, ctx.guild.id, amount)
            if not user_:
                msg = f"Successfully claimed **{amount}{self.cur}**!"
            else:
                msg = f"You gave **{amount}{self.cur}** to {user_}!"
            colour = None
            next_claim = datetime.datetime.utcnow() + datetime.timedelta(hours=cooldown)
        else:
            next_claim = last_claim + datetime.timedelta(hours=cooldown)
            colour = discord.Color.red()
            embed.title = ""
            msg = "You have already claimed your credits."
        embed.set_footer(text="Next claim:")
        embed.timestamp = next_claim
        embed.description = msg
        return await self.msg.message_sender(ctx, embed, color=colour)

    @commands.command(name="give")
    async def cmd_give(self, ctx, user: discord.Member, amount: func_economy.LocalBalance):
        """Transfer your money to someone else."""
        if user.bot:
            await self.msg.error_msg(ctx, "You can't transfer money to a bot!")
            return
        amount, balance = amount

        server_information: dict = await ctx.get_server_information()
        user_roles: list = [i.id for i in ctx.author.roles]
        allowed_trade: bool = False
        # allowed roles overwrites blacklisted roles
        allowed_roles = server_information.get("income_give_allowed_roles", [])
        if allowed_roles:
            for role in allowed_roles:
                role_id = role.get("role_id", 0)
                if role_id in user_roles:
                    allowed_trade = True
                    break
        # blacklist should overwrite the whitelist
        blacklisted_roles = server_information.get("income_give_disallowed_roles", [])
        if blacklisted_roles:
            for role in blacklisted_roles:
                role_id = role.get("role_id", 0)
                if role_id in user_roles:
                    return await self.msg.message_sender(
                        ctx, discord.Embed(
                            title="You are not allowed to transfer credits!",
                            description=f"The role <@&{role_id}> is not allowed to transfer credits!",
                        )
                    )
        if not allowed_trade and allowed_roles:
            return await self.msg.message_sender(
                ctx, discord.Embed(
                    title="You are not allowed to transfer credits!",
                    description=f"You are missing an allowed role."
                )
            )
        tax = server_information.get("income_tax_roles", 0)
        if type(tax) == list:
            for role in tax:
                if role.get("role_id", 0) in user_roles:
                    tax = role.get("value", tax)
        if type(tax) == list:
            tax = 0
        taxed_amount = amount - int(amount * (tax / 100))  # remove tax percentage from amount
        confirmation_num = str(random.randint(1000, 9999))
        confirm_embed = discord.Embed(
            title=f"Confirm the transfer of {amount} credits",
            description=f"Receiver: {user.mention}\n"
                        f"Amount after {tax}% tax: {taxed_amount}\n"
                        f"Reply with `{confirmation_num}` to confirm the transfer or `exit` to cancel the transfer!"
        )
        confirmation_msg = await self.msg.message_sender(ctx, confirm_embed, discord.Color.green())
        confirm_result = await self.bot.wait_for(
            "message", timeout=60, check=lambda m: (m.content == confirmation_num or m.content.lower() == "exit")
                                                   and m.author == ctx.author
        )
        if confirm_result.content.lower() == "exit":
            await confirmation_msg.delete()
            return await self.msg.message_sender(ctx, discord.Embed(title="Successfully cancelled the trade!"))

        await self.udb.edit_money(ctx.author.id, ctx.guild.id, -taxed_amount)
        receiver_balance = await self.udb.edit_money(user.id, ctx.guild.id, taxed_amount)
        receiver_balance = receiver_balance.get("balance", amount)
        embed = discord.Embed(
            title=f"Successfully transferred {taxed_amount} credits!",
            description=f"{ctx.author.name}'s balance: {balance} credits\n"
                        f"{user.name}'s balance: {receiver_balance} credits"
        )
        return await self.msg.message_sender(ctx, embed)


def setup(bot):
    bot.add_cog(EconomyCommands(bot))
