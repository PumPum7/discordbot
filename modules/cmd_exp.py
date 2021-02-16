import aiohttp
from io import BytesIO

import discord
from discord.ext import commands

from functions import func_database, func_msg_gen, func_client_grpc


class ExpCommands(commands.Cog, name="Exp Commands"):
    def __init__(self, bot):
        self.bot = bot
        self.sdb = func_database.ServerDatabase()
        self.udb = func_database.UserDatabase()
        self.msg = func_msg_gen.MessageGenerator()
        self.client_grpc = func_client_grpc.Generator()

    @commands.group(name="exp", aliases=["rank", "level"], invoke_without_command=True)
    @commands.guild_only()
    async def cmd_exp(self, ctx, user: discord.Member = None):
        """Show the exp of a user"""
        user = user or ctx.author
        if user.bot:
            return await self.msg.error_msg(
                ctx=ctx,
                msg="Bot accounts don't have experience."
            )
        # checks if exp is enabled on the server
        server_settings = await ctx.get_server_information()
        exp_enabled = server_settings.get("exp_enabled", False)
        if exp_enabled:
            # gets the leaderboard ranking for the user
            exp = await self.udb.get_user_information(user.id, ctx.guild.id).distinct("exp_amount")
            users = await self.udb.user_sort(ctx.guild.id, "exp_amount", user_amount=exp[0] if exp else 0)
            position = "/"
            for i in users:
                if i.get("user_id", 0) == user.id:
                    position = users.index(i) + 1
                    break
        else:
            return await self.msg.error_msg(
                ctx=ctx,
                msg=f"This server does not have exp enabled! "
                    f"You can enable it with `{ctx.prefix}sset exp`."
            )
        # sends the exp message
        exp = exp[0] if exp else 0
        # downloads the profile picture and returns the bytes
        avatar_img = await self.get_profile_bytes(str(user.avatar_url_as(format="png", size=128)))
        # grpc call to the Level image generator
        img = await self.client_grpc.get_level_image(exp, exp+10, f"#{position}", user.name, ctx.guild.name,
                                                     "default", func_client_grpc.Role(role_id=12312, role_name="test"),
                                                     avatar_img)
        # create a file like object and send the message
        fp = BytesIO(img)
        # TODO: add progress for levels + next role
        await ctx.send("Test", file=discord.File(fp=fp, filename="level_img.png"))
        fp.close()
        return

    @staticmethod
    async def get_profile_bytes(avatar_url: str):
        # gets the avatar image as bytes
        async with aiohttp.ClientSession() as session:
            async with session.get(url=avatar_url) as result:
                if result.status != 200:
                    return result.raise_for_status()
                else:
                    image = await result.read()
        return image

    @cmd_exp.command(name="edit")
    async def cmd_exp_edit(self, ctx, action: str, amount: int, user: discord.Member):
        """Edit the exp of a user."""
        if user.bot:
            return await self.msg.error_msg(
                ctx=ctx,
                msg="Bot accounts don't have experience."
            )
        exp_enabled = await ctx.get_server_information()
        exp_enabled = exp_enabled.get("exp_enabled", False)
        if exp_enabled:
            if action not in ["add", "remove"]:
                return await self.msg.error_msg(
                    ctx=ctx,
                    msg="Please make sure you have specified a valid action.\nThe action can be `add` or `remove`"
                )
            result = await self.udb.set_setting_local(
                user_id=user.id,
                server_id=ctx.guild.id,
                query={"$inc": {"exp_amount": amount if action == "add" else -amount}}
            )
            cur_exp = result.get("exp_amount", 0)
            embed = discord.Embed(
                title="Score successfully edited!",
                description=f"The user {user.mention}({user}) has {cur_exp} exp now!"
            )
            return await self.msg.message_sender(
                ctx=ctx,
                embed=embed
            )
        else:
            return await self.msg.error_msg(
                ctx=ctx,
                msg=f"This server does not have exp enabled! "
                    f"You can enable it with `{ctx.prefix}sset exp`."
            )


def setup(bot):
    bot.add_cog(ExpCommands(bot))
