import asyncio
import discord
from discord.ext import commands, tasks
import random
import datetime

import bot_settings
from functions import func_msg_gen, func_economy, func_database


class Gambling(commands.Cog):
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
        if not user:
            user = ctx.author
        balance = await self.udb.get_user_information(user.id).distinct("balance")
        if len(balance) < 1:
            balance = 0
        else:
            balance = balance[0]
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
    async def cmd_blackjack(self, ctx, bet: func_economy.GlobalMoney):
        """Play blackjack with this command."""
        # TODO: add emotes or even generated images for cards
        # TODO: double down (hard 9, 10 or 11)
        # TODO: double down:
        hand = {'bot': [], 'human': []}
        suits = ['c', 'h', 'd', 's']
        deck = []
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
            value=func_economy.bj_field_generator("bot", hand)
        )
        msg = await self.msg.message_sender(ctx, embed=start_embed)
        for i in self.bj_reactions.keys():
            await msg.add_reaction(i)
        playing = True
        playerBusted = False
        while playing:
            # wait for reactions (15 sec timeout)
            try:
                reaction, user = await self.bot.wait_for("reaction_add",
                                                         check=lambda reaction, user:
                                                         user == ctx.author and reaction.emoji in self.bj_reactions.keys(),
                                                         timeout=20.0)
            except asyncio.TimeoutError:
                await self.udb.edit_money(ctx.author.id, ctx.guild.id, -bet)
                return await self.msg.error_msg(ctx, "You only have 20 seconds to react."
                                                     "The money has been deducted from your balance.")
            # blackjack reaction handler
            if self.bj_reactions[reaction.emoji] == "hit":
                hand['human'].append(deck.pop(0))
                if func_economy.bj_hand_counter(hand['human']) > 21:
                    playerBusted = True
                    playing = False
                else:
                    await msg.remove_reaction(emoji=reaction.emoji, member=ctx.author)
                    await msg.edit(embed=self.blackjack_msg_updater(msg, hand))
            elif self.bj_reactions[reaction.emoji] == "stand":
                playing = False
            # TODO: add double down
            else:
                pass
        # bot hands handler
        botBusted = False
        if not playerBusted:
            # generates the bots hand
            hand, deck, botBusted = func_economy.bj_handle_bot_cards(hand, deck)
        # handler for winner
        text, win, bet_edited = func_economy.bj_winner_handler(hand, playerBusted, botBusted, bet)
        # sends the embeds and changes the currency
        embed = self.blackjack_msg_updater(msg, hand)
        embed.description = text.format(bet_edited)
        embed.color = discord.Color.green() if win else discord.Color.red()
        await self.udb.edit_money(ctx.author.id, ctx.guild.id, bet_edited)
        return await msg.edit(embed=embed, content=msg.content)

    @commands.command(name="claim", aliases=["work"])
    async def cmd_daily(self, ctx) -> discord.Message:
        # TODO: change to use server setting
        amount = bot_settings.daily_amount
        cooldown = 24
        user = ctx.author
        # check if they cna claim it again
        last_claim = await self.udb.get_user_information(user.id).distinct("claimed_daily")
        if not last_claim:
            claimed_daily = False
        else:
            claimed_daily = last_claim[0] + datetime.timedelta(hours=cooldown) > datetime.datetime.utcnow()
        embed = discord.Embed()
        if not claimed_daily:
            await self.udb.claim_daily(user.id, ctx.guild.id, amount)
            msg = f"{amount}{self.cur} claimed!"
            colour = discord.Color.green()
            next_claim = datetime.datetime.utcnow() + datetime.timedelta(hours=cooldown)
        else:
            next_claim = (last_claim[0] + datetime.timedelta(hours=cooldown))
            colour = discord.Color.red()
            embed.title = ""
            msg = "You have already claimed your credits."
        embed.set_footer(text="Next claim:")
        embed.timestamp = next_claim
        embed.description = msg
        return await self.msg.message_sender(ctx, embed, color=colour)


def setup(bot):
    bot.add_cog(Gambling(bot))
