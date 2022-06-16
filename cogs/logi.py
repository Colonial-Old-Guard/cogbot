""" Logistics cog """

# nextcord stuff
import nextcord
from nextcord.ext import commands
from nextcord import Integration, SlashOption, Forbidden, HTTPException

# the bot bits
# pylint: disable=import-error
from cogbot import logger, cogGuild

if __name__ == "__main__":
    # pylint: disable=pointless-statement
    exit

class LogiCog(commands.Cog):
    """
    Promotions cog
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @nextcord.slash_command(
        name="promotion",
        description="Promote a member",
        guild_ids=cogGuild,
    )

    # pylint: disable=no-self-use
    async def fuck(
        self,
        interaction: Integration,
        add_or_remove: str = SlashOption(
            name="add_or_remove",
            description="Add or Remove role?",
            choices={"Add": "add", "Remove": "remove"},
            required=True
            ),
        role: int = SlashOption(
            name="role",
            description="What role?",
            choices={
                "Logistics High Value": 925770000067858442,
                "Logistics Main": 925720078027223070,
                "Logistics Newbie": 980563823226404895
                },
            required=True
            ),
        member: nextcord.Member = SlashOption(
            name="member",
            description="Member for promotion",
            required=True
        ),
        ):
        """ Logi stuff """
        logger.info("Running logi command")

        logi_role = interaction.guild.get_role(role)

        if add_or_remove == "add":
            try:
                logger.info(f"Adding roles to {member.nick}|{member.id}")
                await member.add_roles(logi_role)
            except Forbidden as error:
                print(f"no permissions: {error}")
                logger.error(f"Incorrect permissions adding roles to "
                    f"{member.name}|{member.id}: {error}")
            except HTTPException as error:
                print(f"Other error: {error}")
                logger.error(f"HTTP error adding roles to "
                    f"{member.name}|{member.id}: {error}")

        if add_or_remove == "remove":
            try:
                logger.info(f"Adding roles to {member.nick}|{member.id}")
                await member.remove_roles(logi_role)
            except Forbidden as error:
                print(f"no permissions: {error}")
                logger.error(f"Incorrect permissions adding roles to "
                    f"{member.name}|{member.id}: {error}")
            except HTTPException as error:
                print(f"Other error: {error}")
                logger.error(f"HTTP error adding roles to "
                    f"{member.name}|{member.id}: {error}")

def setup(bot):
    """
    Magic
    """
    bot.add_cog(LogiCog(bot))
