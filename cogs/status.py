""" Status COG """

# python stuff
import datetime
import time

# nextcord stuff
import nextcord
from nextcord.ext import commands
from nextcord import Integration, SlashOption

# the bot bits
# pylint: disable=import-error
from cogbot import logger, cogGuild, get_member_info

if __name__ == '__main__':
    # pylint: disable=pointless-statement
    exit

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

class StatusCog(commands.Cog):
    """
    Status cog
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @nextcord.slash_command(
        name='status',
        description='Get a members status',
        guild_ids=cogGuild,
    )

    # pylint: disable=no-self-use
    async def retire(
        self,
        interaction: Integration,
        member: nextcord.Member = SlashOption(
            name='member',
            description='Member to check',
            required=False
        ),
        discord_id: str = SlashOption(
            name='discord_id',
            description='Discord ID of the member (if you can\'t use the member option for example',
            required=False
        ),
        show_history: bool = SlashOption(
            name='show_history',
            description='Show history of verification of this user',
            required=False
        )
        # command: str = SlashOption(
        #     name="command",description="What do you want to do?",\
        #         required=True,choices={"Status": "status", "Promote": "promote", "List": "list"}
        #     ),

    ):
        """
        Status command stuff
        """
        if not member and not discord_id:
            logger.info('%s|%s has not provided a member or discord ID',
            interaction.user.id,interaction.user.name)
            await interaction.response.send_message(ephemeral=True,
            content="You need to provide a Member or discord ID to be able to use this command.")

        elif member and discord_id:
            logger.info('%s|%s has provided both a member and discord ID',
            interaction.user.id,interaction.user.name)
            await interaction.response.send_message(ephemeral=True,
            content="You need to provide only 1 of these parameters Member or Discord ID to be able"
            " to use this command.")

        elif (member or discord_id) and not show_history:
            logger.info('%s|%s running command with history as %s',
            interaction.user.id,interaction.user.name,show_history)

            result = []

            if member:
                for members_list, members_details in await get_member_info(member):
                    result.append([members_list, members_details])
            elif discord_id:
                for members_list, members_details in await get_member_info(discord_id):
                    result.append([members_list, members_details])


            await interaction.response.send_message(ephemeral=True,
            embed=custom_embed_thing(title='Verification Status', timestamp=interaction.created_at,
            description=f"> **User** {result[0][1].discord_discriminator} (<@"
            f"{result[0][0].discord_id}>)\n> **Discord ID** `{result[0][0].discord_id}`\n> **Steam"
            f" name** {result[0][1].steam_name}\n> **Steam ID** `{result[0][1].steam_64}`\n> **Ste"
            f"am Profile** https://steamcommunity.com/profiles/{result[0][1].steam_64}\n> **Verifi"
            f"cation Status** {result[0][1].is_verified} <t:"
            f"{int(time.mktime(result[0][1].last_modified_datetime.timetuple()))}:f>\n> **Verified"
            f" by** `{result[0][1].last_modified_by}` (<@{result[0][1].last_modified_by_id}>)",
            footer_text=interaction.user.name))

            # await interaction.response.send_message(ephemeral=True,
            # content=f"Returns: {result}")


def setup(bot):
    """
    Magic
    """
    bot.add_cog(StatusCog(bot))
