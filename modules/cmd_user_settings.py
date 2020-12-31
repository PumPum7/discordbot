import discord
from discord.ext import commands
from functions import func_database, func_msg_gen
import bot_settings as bset


class UserSettings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = func_database.UserDatabase()
        self.msg = func_msg_gen.MessageGenerator()

    @commands.group(name="set", invoke_without_command=True)
    async def cmd_group_set(self, ctx):
        """Set commands"""
        embed = discord.Embed()
        embed.title = "User Settings"
        embed.add_field(name="Commands:", value="> set prefix <action> <prefix>")
        await self.msg.message_sender(ctx, embed)

    async def prefix_handler(self, action, new_prefix, ctx):
        action = action.lower()
        if action == "add":
            action = True
            msg = f"Successfully added `{new_prefix}` to your prefixes!"
        elif action == "remove":
            action = False
            msg = f"Successfully removed `{new_prefix}` from your prefixes!"
        else:
            return False
        prefix = await self.db.edit_prefix(ctx.author.id, new_prefix, action)
        return prefix, msg

    @cmd_group_set.command(name="prefix")
    async def cmd_set_prefix(self, ctx, action=None, new_prefix: str = False):
        """Change the bots prefix. Action can be either add or remove"""
        prefix_ = await self.db.get_user_information(ctx.author.id).distinct("prefix")
        # Check if there are already 10 prefixes added
        if len(prefix_) > 10:
            message = "You can only add up to 10 custom prefixes. Please remove one " \
                      "of your prefixes before adding new ones!"
        # check if its already registered
        elif new_prefix in prefix_:
            message = f"`{new_prefix}` is already registered as prefix."
        # no action specified
        elif not new_prefix or not action:
            message = f"To change your prefix add `add` or `remove`.\n" \
                      f"For more information use `{ctx.prefix}help set prefix`."
        # adds or removes a prefix
        else:
            prefix = await self.prefix_handler(action, new_prefix, ctx)
            if not prefix:
                raise commands.MissingRequiredArgument(ctx.command)
            prefix_ = prefix[0]["prefix"]
            message = prefix[1]
        embed = discord.Embed(title="Prefix Menu", description=message)
        embed.add_field(
            name="Your current prefixes:",
            value=", ".join(prefix_)
        )
        await self.msg.message_sender(ctx, embed)


def setup(bot):
    bot.add_cog(UserSettings(bot))
