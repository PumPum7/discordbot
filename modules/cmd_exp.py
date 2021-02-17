import aiohttp
from io import BytesIO

import discord
from discord.ext import commands

from functions import func_database, func_msg_gen, func_client_grpc, func_web, func_exp


class ExpCommands(commands.Cog, name="Exp Commands"):
    def __init__(self, bot):
        self.bot = bot
        self.sdb = func_database.ServerDatabase()
        self.udb = func_database.UserDatabase()
        self.msg = func_msg_gen.MessageGenerator()
        self.client_grpc = func_client_grpc.Generator()

    # TODO: add cooldown after testing
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
        avatar_img = await func_web.get_profile_bytes(str(user.avatar_url_as(format="png", size=128)))
        # get the exp roles
        exp_roles = server_settings.get("exp_level_roles", [])
        # format the exp roles dict
        exp_roles = [{"role": item["role_id"], "requirement": item["required"]} for item in exp_roles] \
            if exp_roles else [{}] if exp_roles else exp_roles
        # filter exp roles
        exp_roles = func_exp.sort_roles(exp_roles, exp)
        # create the Role object and set the requirement
        next_role = exp_roles[1]
        if len(next_role) == 0:
            next_role = func_client_grpc.Role(
                role_id=0,
                role_name="All roles earned!"
            )
            requirement = 0
        else:
            role = discord.utils.get(id=next_role[0]["role"], iterable=ctx.guild.roles)  # creates a discord.Role object
            if role:
                requirement = next_role[0]["requirement"]
                next_role = func_client_grpc.Role(
                    role_id=role.id,
                    role_name=role.name,
                )
            else:
                requirement = next_role[0]["requirement"]
                next_role = func_client_grpc.Role(
                    role_id=123,
                    role_name="Deleted role"
                )
        # grpc call to the Level image generator
        img = await self.client_grpc.get_level_image(exp, requirement, f"#{position}", user.name, ctx.guild.name,
                                                     "default", next_role, avatar_img)
        # create a file like object and send the message
        fp = BytesIO(img)
        # TODO: add progress for levels + next role
        await ctx.send("Test", file=discord.File(fp=fp, filename="level_img.png"))
        fp.close()
        return

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
