""" Verify cog """

# pylint: disable=duplicate-code

from urllib.parse import urlparse
import re
from datetime import datetime

# nextcord stuff
import nextcord
from nextcord.ext import commands
from nextcord import Integration, SlashOption, Forbidden, HTTPException

# the bot bits
# pylint: disable=import-error
from cogbot import logger, cogGuild, get_steam_plus_name, update_member_verification, is_in_role

# pylint: disable=too-many-arguments
def custom_embed_thing(title:str, timestamp:datetime, description:str,
    footer_text:str, image_url=None, colour=None):
    """
    returns embed
    """
    embed = nextcord.Embed(
        title=title,
        timestamp=timestamp)
    embed.set_footer(text=footer_text)
    embed.description=description
    if colour:
        embed.colour=colour
    if image_url:
        if image_url.avatar:
            if image_url.avatar.url:
                embed.set_thumbnail(url=image_url.avatar.url)
    return embed

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
        guild_ids=cogGuild,
    )
# pylint: disable=too-many-locals,too-many-statements,too-many-branches
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
                            'http[s]?:\/\/(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\), ]|(?:%[0-9a-fA-F][0-9a-fA-F]))\w{0,}.\w{0,}\/\w{0,}\/\w{0,}', \
                                 message.content):
                            logger.debug(f"Found URL: {url}")
                            urls.append((url, message.author.id))
                    else:
                        logger.debug(f"IsBot: {message.author.bot}, "
                            f"message author: {message.author.name}")


                logger.debug(f"Checking for Steam URLs in array {urls}")
                for url in urls:
                    if url[0].startswith("https://steamcommunity.com/id/")\
                        or url[0].startswith("https://steamcommunity.com/profiles/")\
                        or url[0].startswith("http://steamcommunity.com/id/")\
                        or url[0].startswith("http://steamcommunity.com/profiles/"):

                        logger.debug(f"Found steam URL: {url[0]}")

                        # this is overkill and can be cut down later
                        # just needs to find the newest message with a valid steam URL, and put the
                        # steam API results into the full_steam_profile bit
                        parsed_url = urlparse(url[0])

                        logger.debug(f"Trying find user with id {url[1]}")

                        member = await interaction.guild.fetch_member(url[1])

                        steam_profile_type = parsed_url.path.rstrip("/").split("/")[1]
                        steam_profile_id = parsed_url.path.rstrip("/").split("/")[2]

                        logger.debug(f"get_steam_plus_name({steam_profile_type},"
                             f"{steam_profile_id})")
                        full_steam_profile = await \
                            get_steam_plus_name(steam_profile_type, steam_profile_id)

                        if full_steam_profile is None:
                            await interaction.send(ephemeral=True,content=
                            "Steam is either not responding, or with nonsense. Try again later")
                            break

                        if full_steam_profile["response"]["players"][0]["steamid"] \
                            and full_steam_profile["response"]["players"][0]["personaname"]:
                            break

                db_update = None

                if len(full_steam_profile) == 0 or full_steam_profile is None:
                    # await interaction.send(ephemeral=True, \
                    db_update = await update_member_verification(member=member,
                        verification_type=verification_type, interaction=interaction)

                else:
                    db_update = await update_member_verification(member=member,
                        verification_type=verification_type, interaction=interaction,
                        steam=[full_steam_profile["response"]["players"][0]["steamid"],
                        full_steam_profile["response"]["players"][0]["personaname"]])

                if db_update == 1:
                    await interaction.response.send_message(ephemeral=True,
                    content="Added/updated user verification!"
                    "Trying to add roles and update name.")

                    steam_name = full_steam_profile["response"]["players"][0]["personaname"]
                    steam_64 = full_steam_profile["response"]["players"][0]["steamid"]

                    missing_roles = []
                    cog_roles = [926172865097781299,925531185554276403,925531141128196107,
                    986376132637106207,989899109190217758,990345561225981962]

                    for role in cog_roles:
                        if not is_in_role(member, role):
                            missing_roles.append(interaction.guild.get_role(role))

                    try:
                        if missing_roles:
                            for missing_role in missing_roles:
                                await member.add_roles(missing_role, reason='Verification')
                                logger.info("adding %s to %s",missing_role.name, member.name)
                    except Forbidden as error:
                        logger.error(f"Incorrect permissions changing roles of "
                            f"{member.name}|{member.id}: {error}")
                    except HTTPException as error:
                        logger.error(f"HTTP error updating roles of "
                            f"{member.name}|{member.id}: {error}")

                    try:
                        logger.info(f"Changing nick of "
                            f"{member.name}|{member.id} to {steam_name}")
                        await member.edit(nick=steam_name)
                    except Forbidden as error:
                        print(f"no permissions: {error}")
                        logger.error(f"Incorrect permissions changing nick of "
                            f"{member.name}|{member.id}: {error}")
                    except HTTPException as error:
                        print(f"Other error: {error}")
                        logger.error(f"HTTP error updating nick of "
                            f"{member.name}|{member.id}: {error}")

                    await interaction.channel.send(embed=custom_embed_thing(
                        title='COG verification', timestamp=interaction.created_at,
                        footer_text=interaction.user.name, description=f'Welcome to COG '
                        f'{member.mention}!\n\nPlease make sure to have read a'
						f'nd understood the <#976906183849951302>, and have assigned you'
						f'rself a timezone and any other roles you want from '
						f'<#925697546125467698>\n\n> **Verified as** COG\n> **User** '
						f'{member.name}#{member.discriminator} '
						f'({member.mention})\n> **ID** `{member.id}`', colour=0x516c4b
                    ))

                    promotion_recruits_channel = interaction.guild.get_channel(971763222937993236)
                    await promotion_recruits_channel.send(embed=custom_embed_thing(
                        title='COG verification', timestamp=interaction.created_at,
                        footer_text=interaction.user.name, description=f'> **Verified as** COG\n> '
                        f'**User** {member.name}#{member.discriminator} ({member.mention}'
                        f')\n> **Discord ID** `{member.id}`\n> **Steam name** '
                        f'`{steam_name}`\n> **Steam ID** `{steam_64}`\n> **Steam profile** https://'
                        f'steamcommunity.com/profiles/{steam_64}\n> **Verified by** '
                        f'{interaction.user.name}#{interaction.user.discriminator} '
                        f'({interaction.user.mention})', colour=0x516c4b,
                        image_url=member
                    ))


            # Ally verification goes here
            if verification_type == "ally":
                logger.info("Verifying as an Ally")
                await interaction.response.send_message(ephemeral=True,
                    content="Verify as Ally. Command not finished yet!")

            # Warden verification goes nowhere
            if verification_type == "blue":
                logger.info("Verifying as a Warden")
                await interaction.response.send_message(ephemeral=True,
                    content="Verify as Warden. Command not finished yet!")


            logger.info("Ok")
        else:
            logger.info(
                f"{interaction.user.nick}|{interaction.user.id} running "
                f"the command from outside of the RECRUITMENT category, "
                f"or not a ticket!")
            await interaction.response.send_message(ephemeral=True,
                content="This command can only be run inside the "
                    "RECRUITMENT category, and a ticket!")

def setup(bot):
    """
    Magic
    """
    bot.add_cog(VerifyCog(bot))
