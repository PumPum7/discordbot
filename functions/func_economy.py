from discord.ext import commands

from functions import func_database, func_errors
import bot_settings as bs

udb = func_database.UserDatabase()


class GlobalMoney(commands.Converter):
    async def convert(self, ctx, argument: int):
        try:
            argument = int(argument)
        except:
            raise commands.BadArgument
        if argument < 1:
            raise func_errors.EconomyError("You can't use a negative amount of currency for this action!")
        balance = await udb.get_user_information(ctx.author.id).distinct("balance")
        if len(balance) < 1:
            balance = 0
        else:
            balance = balance[0]
        if argument > balance:
            raise func_errors.EconomyError(f"You only have {balance}{bs.currency_name}!")
        else:
            return argument


class Card:
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit
        self.cardName = {1: 'Ace', 2: 'Two', 3: 'Three', 4: 'Four', 5: 'Five', 6: 'Six', 7: 'Seven', 8: 'Eight',
                         9: 'Nine',
                         10: 'Ten', 11: 'Jack', 12: 'Queen', 13: 'King'}
        self.cardSuit = {'c': 'Clubs', 'h': 'Hearts', 's': 'Spades', 'd': 'Diamonds'}

    def __str__(self):
        return self.cardName[self.rank] + " Of " + self.cardSuit[self.suit]

    def getRank(self):
        return self.rank

    def getSuit(self):
        return self.suit

    def BJValue(self):
        if self.rank > 9:
            return 10
        else:
            return self.rank


def bj_hand_counter(hand):
    handCount = 0
    for card in hand:
        handCount += card.BJValue()
    return (handCount)


def bj_string_generator(reactions):
    bj_message = []
    for action in reactions.keys():
        bj_message.append(f"{reactions[action].capitalize()}: {action}\n")
    return "".join(bj_message)


def bj_field_generator(cur_player, hands):
    return f"Score: {bj_hand_counter(hands[cur_player])}\n" \
           f"Cards: {', '.join(str(i) for i in hands[cur_player])}"


def bj_handle_bot_cards(hand, deck):
    finished = False
    busted = False
    while not finished:
        if bj_hand_counter(hand['bot']) < 17:
            hand['bot'].append(deck.pop(0))
        else:
            finished = True
    if bj_hand_counter(hand['bot']) > 21:
        busted = True
    return hand, deck, busted


def bj_winner_handler(hand, playerBusted, botBusted, bet: float):
    hand_human = bj_hand_counter(hand['human'])
    hand_bot = bj_hand_counter(hand['bot'])
    if playerBusted:
        win = False
        msg = "Busted! You lost {}" + bs.currency_name + "..."
        bet *= -1.0
    elif botBusted:
        win = True
        msg = "Dealer bust! You won {}" + bs.currency_name + " !"
    elif hand_human > hand_bot:
        win = True
        msg = "You won {}" + bs.currency_name + "!"
        if bj_hand_counter(hand["human"]) == 21:
            bet *= 1.5
    elif hand_human == hand_bot:
        win = False
        msg = "Push! You got your money back."
        bet = 0.0
    else:
        win = False
        msg = "You lost {}" + bs.currency_name + "..."
        bet *= -1.0
    return msg, win, bet
