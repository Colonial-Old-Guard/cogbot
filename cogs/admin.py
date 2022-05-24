""" Admin cog for admin commands """

# nextcord stuff
import nextcord
from nextcord.ext import commands
from nextcord import Integration, SlashOption

# sqlalchemy
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

# pylint: disable=import-error
from cogbot import logger, cogGuild, db, MembersInfo

if __name__ == "__main__":
    # pylint: disable=pointless-statement
    exit

def get_all_id():
    """
    Returns all discord_ids from the db
    """
    result = {}
    statement = select(MembersInfo.discord_id)
    try:
        result = db.execute(statement).all()
        return result
    except IntegrityError as error:
        logger.error("Error: %s", error)
        return None

class AdminCog(commands.Cog):
    """
    Admin cog
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @nextcord.slash_command(
        name="admin",
        description="Administrator commands",
        default_permission=False,
        guild_ids=cogGuild,

    )

    # pylint: disable=no-self-use
    async def promotion(
        self,
        interaction: Integration,
        command: str = SlashOption(
            name="command",
            description="...",
            choices={"Purge old users from the db": "purge"},
            required=True)):
        """
        promotion?
        """

        if interaction.user.id == 136929317316853760:
            # await interaction.send(ephemeral=True, content=f"Fuck")
            if command == "purge":
                await interaction.send(ephemeral=True, content="PURGE THEM")
                # print(get_all_id())
                # all_db_members = get_all_id()
                # intents = nextcord.Intents(messages=True, guilds=True)
                # intents.members = True
                # all_discord_members = bot.guilds[0].members

                # all_discord_members = bot.guilds[0].fetch_members().flatten()

                # all_discord_members = await interaction.guild.chunk()

                # all_discord_members = await bot.guilds[0].chunk()

                # print(all_discord_members)
                # print("fuck")
                # guilds = bot.guilds
                # for member in guilds[0].members:
                #     print(member)

        else:
            await interaction.send(ephemeral=True, content="49 only command")

def setup(bot):
    """
    Magic
    """
    bot.add_cog(AdminCog(bot))
