

# nextcord stuff
from logging import exception
import nextcord
from nextcord.ext import commands
from nextcord import Integration, SlashOption, CommandOption

# sqlalchemy
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound

from cogbot import logger, cogGuild, db, MembersInfo, bot

if __name__ == "__main__":
    exit

def getAllId():
    result = {}
    statement = select(MembersInfo.discord_id)
    try:
        result = db.execute(statement).all()
        return result
    except Exception as e:
        logger.error(f"Error: {e}")
        return None

class AdminCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
    
    @nextcord.slash_command(
        name="admin",
        description="Administrator commands",
        default_permission=False,
        guild_ids=cogGuild,
        
    )

    async def promotion(
        self, 
        interaction: Integration,
        command: str = SlashOption(
            name="command",
            description="...",
            choices={"Purge old users from the db": "purge"},
            required=True)):

        if interaction.user.id == 136929317316853760:
            # await interaction.send(ephemeral=True, content=f"Fuck")
            if command == "purge":
                await interaction.send(ephemeral=True, content=f"PURGE THEM")
                # print(getAllId())
                # all_db_members = getAllId()
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
            await interaction.send(ephemeral=True, content=f"49 only command")

def setup(bot):
    bot.add_cog(AdminCog(bot))