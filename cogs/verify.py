""" Verify cog """

# import datetime

from urllib.parse import urlparse
import re

# nextcord stuff
import nextcord
from nextcord.ext import commands
from nextcord import Integration, SlashOption, Forbidden, HTTPException

# sqlalchemy
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
# from sqlalchemy.orm.exc import NoResultFound

# the bot bits
# pylint: disable=import-error
from cogbot import logger, cogGuild, db, MembersInfo, get_steam_plus_name

if __name__ == "__main__":
    # pylint: disable=pointless-statement
    exit

class VerifyCog(commands.Cog):
    """
    Verify command, used to verify members
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot



    @nextcord.slash_command(
        name="verify",
        description="Verify a member",
        default_permission=False,
        guild_ids=cogGuild,
    )


    # pylint: disable=too-many-locals,no-self-use,too-many-statements,too-many-branches
    async def verify(
        self,
        interaction: Integration,
        verification_type: str = SlashOption(
            name="as",
            description="Verifying as a Member of COG, as an Ally, or a Warden?",
            choices={"Member": "cog", "Ally": "ally", "Warden": "blue"},
            required=True
        )
    ):
        """
        Verify member as COG, Colonial Ally, or Warden
        """
        logger.info(f"{interaction.user.nick}|{interaction.user.id} Is running verify command")

        # Check if the category is right and in a ticket
        if interaction.channel.category_id == 940624551946092614 \
            and (interaction.channel.name).startswith("ticket-"):


            # Colonial verification stuff goes here.
            if verification_type == "cog":
                logger.info("Verifying as a member of COG")

                urls = []
                full_steam_profile = ""
                member = 0

                async for message in interaction.channel.history(limit=200):
                    # hopefully only scans messages sent by the person who opened the ticket
                    if message.author.bot is False:
                        for url in re.findall(
                            # pylint: disable=line-too-long,anomalous-backslash-in-string
                            'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', \
                                 message.content):
                            logger.debug(f"Found URL: {url}")
                            urls.append((url, message.author.id))
                    else:
                        logger.debug(f"IsBot: {message.author.bot}, \
                            message author: {message.author.name}")


                logger.debug(f"Checking for Steam URLs in array {urls}")
                for url in urls:
                    if url[0].startswith("https://steamcommunity.com/id/") \
                        or url[0].startswith("https://steamcommunity.com/profiles/"):

                        logger.debug(f"Found steam URL: {url[0]}")

                        # this is overkill and can be cut down later
                        # just needs to find the newest message with a valid steam URL, and put the
                        # steam API results into the full_steam_profile bit
                        parsed_url = urlparse(url[0])

                        logger.debug(f"Trying find user with id {url[1]}")

                        member = await interaction.guild.fetch_member(url[1])

                        steam_profile_type = parsed_url.path.rstrip("/").split("/")[1]
                        steam_profile_id = parsed_url.path.rstrip("/").split("/")[2]

                        logger.debug(f"get_steam_plus_name({steam_profile_type},\
                             {steam_profile_id})")
                        full_steam_profile = await \
                            get_steam_plus_name(steam_profile_type, steam_profile_id)

                        if full_steam_profile["response"]["players"][0]["steamid"] \
                            and full_steam_profile["response"]["players"][0]["personaname"]:
                            break

                if len(full_steam_profile) == 0 or full_steam_profile is None:
                    await interaction.send(ephemeral=True, \
                        content="No steam URLs (or valid ones) have been found.")

                # hopefully this if stops most crashes :S
                elif full_steam_profile["response"]["players"][0]["steamid"] \
                    and full_steam_profile["response"]["players"][0]["personaname"] and member:
                    db.add(MembersInfo(
                        discord_id = member.id,
                        discord_discriminator = str(member),
                        steam_64 = full_steam_profile["response"]["players"][0]["steamid"],
                        name = full_steam_profile["response"]["players"][0]["personaname"],
                        rank_id = 12,
                        joined_datetime = member.joined_at,
                        verified = True,
                        verified_datetime = func.now(),
                        last_promotion_datetime = func.now()
                    ))

                    # if someone can find a way to avoid doing this get_role
                    # and get_channel BS this can get cut down.
                    role_cog = interaction.guild.get_role(926172865097781299)
                    role_foxhole_verified = interaction.guild.get_role(925531185554276403)
                    promotion_recruits_channel = \
                        interaction.guild.get_channel(971763222937993236)
                    rank_and_steam = "Rec. | " + \
                        full_steam_profile["response"]["players"][0]["personaname"]

                    try:
                        # this way around we don't fuck with discord stuff if
                        # the DB has an issue, or the user is already in it.
                        result = db.commit()
                        logger.info(f"Added {member.name}|{member.id} to DB: {result}")

                        try:
                            logger.info(f"Changing nick of \
                                {member.name}|{member.id} to {rank_and_steam}")
                            await member.edit(nick=rank_and_steam)
                        except Forbidden as error:
                            print(f"no permissions: {error}")
                            logger.error(f"Incorrect permissions changing nick of \
                                {member.name}|{member.id}: {error}")
                        except HTTPException as error:
                            print(f"Other error: {error}")
                            logger.error(f"HTTP error updating nick of \
                                {member.name}|{member.id}: {error}")

                        try:
                            logger.info(f"Adding roles to {member.nick}|{member.id}")
                            await member.add_roles(role_cog, role_foxhole_verified)
                        except Forbidden as error:
                            print(f"no permissions: {error}")
                            logger.error(f"Incorrect permissions adding roles to \
                                {member.name}|{member.id}: {error}")
                        except HTTPException as error:
                            print(f"Other error: {error}")
                            logger.error(f"HTTP error adding roles to \
                                {member.name}|{member.id}: {error}")



                        embed = nextcord.Embed(
                            title="New member!",
                            timestamp=interaction.created_at,
                            colour=nextcord.Color.dark_green())
                        embed.add_field(name="New Member", value=member.mention)
                        embed.add_field(name="New Id", value=member.id)
                        embed.add_field(name="Officer Verifying", value=interaction.user.mention)
                        embed.add_field(name="Officer Id", value=interaction.user.id)

                        # now = datetime.datetime.utcnow()
                        # await promotion_recruits_channel.send(f"<@{member.id}> {now.date()} \
                        # {now.date() + datetime.timedelta(days=7)} \
                        # verified by <@{interaction.user.id}>")
                        await promotion_recruits_channel.send(embed=embed)
                        await interaction.send(content=f"Welcome <@{member.id}>\
                            |`{member.id}` you are have been verified by \
                                <@{interaction.user.id}>|`{interaction.user.id}`!")

                    except IntegrityError as error:
                        db.rollback()
                        logger.error(f"Error adding {member.id} to db: {error}")
                        await interaction.send(ephemeral=True, \
                            content=f"Error adding {member.name} to db: {error.orig}")


            # Ally verification goes here
            if verification_type == "ally":
                logger.info("Verifying as an Ally")
                await interaction.response.send_message(ephemeral=True, \
                    content="Verify as Ally. Command not finished yet!")

            # Warden verification goes nowhere
            if verification_type == "blue":
                logger.info("Verifying as a Warden")
                await interaction.response.send_message(ephemeral=True, \
                    content="Verify as Warden. Command not finished yet!")


            logger.info("Ok")
        else:
            logger.info(f"{interaction.user.nick}|\
                {interaction.user.id} running the command from outside\
                     of the RECRUITMENT category, or not a ticket!")
            await interaction.response.send_message(ephemeral=True, \
                content="This command can only be run inside the \
                    RECRUITMENT category, and a ticket!")

def setup(bot):
    """
    Magic
    """
    bot.add_cog(VerifyCog(bot))
