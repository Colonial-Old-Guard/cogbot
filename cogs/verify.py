

import datetime

from urllib.parse import urlparse
import re

# nextcord stuff
import nextcord
from nextcord.ext import commands
from nextcord import Integration, SlashOption

# sqlalchemy
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound

# the bot bits
from cogbot import bot, logger, cogGuild, steam_token, db, MembersInfo, getSteamPlusName

if __name__ == "__main__":
    exit

class VerifyCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    
    
    @nextcord.slash_command(
        name="verify",
        description="Verify a member",
        default_permission=False,
        guild_ids=cogGuild,
    )


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
        logger.info(f"{interaction.user.nick}|{interaction.user.id} Is running verify command") 

        # Check if the category is right and in a ticket
        if interaction.channel.category_id == 940624551946092614 and (interaction.channel.name).startswith("ticket-"):


            # Colonial verification stuff goes here.
            if verification_type == "cog":
                logger.info(f"Verifying as a member of COG")

                urls = []
                full_steam_profile = ""
                member = 0

                async for message in interaction.channel.history(limit=200):
                    # hopefully only scans messages sent by the person who opened the ticket
                    if message.author.bot == False:
                        for url in re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', message.content):
                            logger.debug(f"Found URL: {url}")
                            urls.append((url, message.author.id))
                    else:
                        logger.debug(f"IsBot: {message.author.bot}, message author: {message.author.name}")
                


                logger.debug(f"Checking for Steam URLs in array {urls}")
                for url in urls:
                    if url[0].startswith("https://steamcommunity.com/id/") or url[0].startswith("https://steamcommunity.com/profiles/"):

                        logger.debug(f"Found steam URL: {url[0]}")

                        # this is overkill and can be cut down later
                        # just needs to find the newest message with a valid steam URL, and put the steam API results into the full_steam_profile bit
                        o = urlparse(url[0])

                        logger.debug(f"Trying find user with id {url[1]}")

                        member = await interaction.guild.fetch_member(url[1])

                        steam_profile_type = o.path.rstrip("/").split("/")[1]
                        steam_profile_id = o.path.rstrip("/").split("/")[2]

                        logger.debug(f"getSteamPlusName({steam_profile_type}, {steam_profile_id})")
                        full_steam_profile = await getSteamPlusName(steam_profile_type, steam_profile_id)

                        if full_steam_profile["response"]["players"][0]["steamid"] and full_steam_profile["response"]["players"][0]["personaname"]: break
                
                if len(full_steam_profile) == 0 or full_steam_profile == None:
                    await interaction.send(ephemeral=True, content=f"No steam URLs (or valid ones) have been found.")

                # hopefully this if stops most crashes :S
                elif full_steam_profile["response"]["players"][0]["steamid"] and full_steam_profile["response"]["players"][0]["personaname"] and member:
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

                    # if someone can find a way to avoid doing this get_role and get_channel BS this can get cut down.
                    role_cog = interaction.guild.get_role(926172865097781299)
                    role_foxhole_verified = interaction.guild.get_role(925531185554276403)
                    promotion_recruits_channel = interaction.guild.get_channel(971763222937993236)
                    rank_and_steam = "Rec. | " + full_steam_profile["response"]["players"][0]["personaname"]

                    try:
                        # this way around we don't fuck with discord stuff if the DB has an issue, or the user is already in it.
                        result = db.commit()
                        logger.info(f"Added {member.name}|{member.id} to DB: {result}")

                        try:
                            logger.info(f"Changing nick of {member.name}|{member.id} to {rank_and_steam}")
                            await member.edit(nick=rank_and_steam)
                        except Exception as e:
                            logger.error(f"Error changing nick of {member.name}|{member.id}: {e}")
                        
                        try:
                            logger.info(f"Adding roles to {member.nick}|{member.id}")
                            await member.add_roles(role_cog, role_foxhole_verified)
                        except Exception as e:
                            logger.error(f"Error adding roles to {member.nick}|{member.id}: {e}")

                        
                        embed = nextcord.Embed(
                            title="New member!",
                            timestamp=interaction.created_at,
                            colour=nextcord.Color.dark_green())
                        embed.add_field(name="New Member", value=member.mention)
                        embed.add_field(name="New Id", value=member.id)
                        embed.add_field(name="Officer Verifying", value=interaction.user.mention)
                        embed.add_field(name="Officer Id", value=interaction.user.id)

                        now = datetime.datetime.utcnow()
                        # await promotion_recruits_channel.send(f"<@{member.id}> {now.date()} {now.date() + datetime.timedelta(days=7)} verified by <@{interaction.user.id}>")
                        await promotion_recruits_channel.send(embed=embed)
                        await interaction.send(content=f"Welcome <@{member.id}>|`{member.id}` you are have been verified by <@{interaction.user.id}>|`{interaction.user.id}`!")

                    except IntegrityError as e:
                        db.rollback()
                        logger.error(f"Error adding {member.id} to db: {e}")
                        await interaction.send(ephemeral=True, content=f"Error adding {member.name} to db: {e.orig}")


            # Ally verification goes here 
            if verification_type == "ally":
                logger.info(f"Verifying as an Ally")
                await interaction.response.send_message(ephemeral=True, content=f"Verify as Ally. Command not finished yet!")

            # Warden verification goes nowhere
            if verification_type == "blue":
                logger.info(f"Verifying as a Warden")
                await interaction.response.send_message(ephemeral=True, content=f"Verify as Warden. Command not finished yet!")


            logger.info(f"Ok")
        else:
            logger.info(f"{interaction.user.nick}|{interaction.user.id} running the command from outside of the RECRUITMENT category, or not a ticket!") 
            await interaction.response.send_message(ephemeral=True, content=f"This command can only be run inside the RECRUITMENT category, and a ticket!")    

def setup(bot):
    bot.add_cog(VerifyCog(bot))