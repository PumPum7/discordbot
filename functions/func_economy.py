from discord.ext import commands

import bot_settings as bs
from functions import func_database, func_errors
from data.blackjack import blackjack_emotes

udb = func_database.UserDatabase()


class LocalBalance(commands.Converter):
    async def convert(self, ctx, argument: int) -> tuple[int, int]:
        """

        :param ctx: commands.context
        :type argument: int
        """
        try:
            argument: int = int(argument)
        except Exception:
            raise commands.BadArgument()
        if argument < 1:
            raise func_errors.EconomyError("You can't use a negative amount of currency for this action!")
        information = await ctx.get_user_information()
        balance: int = information[1].get("balance", 0) if information else 0 # gets the local balance
        if argument > balance:
            raise func_errors.EconomyError(f"You only have {balance}{bs.currency_name}!")
        else:
            return argument, balance


class Card:
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit
        self.cardName = {1: 'Ace', 2: 'Two', 3: 'Three', 4: 'Four', 5: 'Five', 6: 'Six', 7: 'Seven', 8: 'Eight',
                         9: 'Nine',
                         10: 'Ten', 11: 'Jack', 12: 'Queen', 13: 'King'}
        self.cardSuit = {'c': 'Clubs', 'h': 'Hearts', 's': 'Spades', 'd': 'Diamonds'}
        self.emotes = blackjack_emotes.blackjack

    @property
    def __str__(self) -> str:
        return self.emotes[f"white_{self.suit}_{self.rank}"]

    def get_rank(self) -> str:
        """

        :rtype: int
        """
        return self.rank

    def get_suit(self) -> str:
        return self.suit

    def bj_value(self) -> int:
        if self.rank > 9:
            return 10
        else:
            return self.rank


def bj_hand_counter(hand) -> int:
    hand_count = 0
    for card in hand:
        hand_count += card.bj_value()
    return hand_count


def bj_string_generator(reactions) -> str:
    bj_message = []
    for action in reactions.keys():
        bj_message.append(f"{reactions[action].capitalize()}: {action}\n")
    return f"{''.join(bj_message)}\nDouble down is only available if you have a score of 9, 10 or 11"


def bj_field_generator(cur_player, hands) -> str:
    cur_hands = hands[cur_player]
    return f"Score: {bj_hand_counter(cur_hands)}\n" \
           f"Cards: {', '.join((i.__str__ for i in cur_hands))}"


def bj_handle_bot_cards(hand, deck) -> tuple:
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


def bj_winner_handler(hand, player_busted: bool, bot_busted: bool, bet: float) -> tuple:
    """

    :type bot_busted: bool
    :type bet: float
    :type player_busted: bool
    :type hand: dict
    """
    hand_human = bj_hand_counter(hand['human'])
    hand_bot = bj_hand_counter(hand['bot'])
    if player_busted:
        win = False
        msg = "Busted! You lost {}" + bs.currency_name + "..."
        bet *= -1.0
    elif bot_busted:
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
    return msg, win, int(round(bet, 0))
