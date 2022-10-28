""" Retire COG """

# nextcord stuff
import nextcord
from nextcord.ext import commands
from nextcord import Integration, SlashOption, Forbidden, HTTPException


# the bot bits
# pylint: disable=import-error
from cogbot import is_in_role, logger, cogGuild, update_steam_db, get_member_info, \
        get_steam_profile

# pylint: disable=too-many-return-statements
async def get_current_steam_name(member: nextcord.Member, interaction :nextcord.Interaction):
    """
    Gets current steam name using steam_64 from the DB.\n
    Returns new Steam name if different than current name.\n
    Returns 0 for success.\n
    Returns 1 if steam_64 missing from DB\n
    Returns 2 if user missing from DB.\n
    Returns 3 if steam error.\n
    Returns 4 if error updating the DB with new steam name.\n
    Returns 5 if error updating discord name\n
    Returns None if Steam_64 is found, and matches Discord.
    """

    try:
        db_member = await get_member_info(member)
        if db_member is None:
            raise ValueError
        logger.debug('%s(%s) found in DB.', member.name, member.id)
    except ValueError as error:
        logger.error('%s(%s) missing from database: %s', member.name, member.id, error)
        return 2

    steam_64 = None

    for members_list, members_details in db_member:
        logger.debug('%s(%s) results: %s, %s',
            member.name, member.id, members_list, members_details)
        steam_64 = members_details.steam_64
        logger.info('%s(%s) steam_64: %s', member.name, member.id, steam_64)

    if not steam_64:
        logger.error('%s(%s) missing steam_64 in the database', member.name, member.id)
        return 1

    steam_profile = []
    full_steam_profile = await get_steam_profile(steam_64)

    if full_steam_profile:
        steam_profile = [full_steam_profile["response"]["players"][0]["steamid"],
            full_steam_profile["response"]["players"][0]["personaname"]]
    else:
        logger.error('%s(%s) steam error getting details for steam_64: %s',
            member.name, member.id, steam_64)
        return 3

    if member.nick != steam_profile[1]:
        logger.info('%s(%s) updating user nick to new steam name: %s',
            member.name, member.id, steam_profile[1])

        try:
            if not await update_steam_db(
                interaction=interaction, member=member, steam=steam_profile):
                raise ValueError
            logger.info('%s(%s) has been updated in the DB.', member.name, member.id)

            try:
                logger.info("Changing nickname of %s(%s) to %s",
                    member.name, member.id, steam_profile[1])
                await member.edit(nick=steam_profile[1])
                return 0
            except Forbidden as error:
                logger.error("Missing permissions to change nickname of %s(%s): %s",
                    member.name, member.id, error)
                return 5
            except HTTPException as error:
                logger.error("HTTP error updating nickname of %s(%s): %s",
                    member.name, member.id, error)
                return 5

        except ValueError as error:
            logger.error('%s(%s) steam error getting details for steam_64: %s',
                member.name, member.id, error)
            return 4

    return None


class RefreshNameCog(commands.Cog):
    """
    Refresh name cog
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @nextcord.slash_command(
        name='refreshname',
        description='Refresh your name from your steam, or if High Command, someone else.',
        guild_ids=cogGuild,
    )
    # pylint: disable=too-many-branches
    async def refresh_name(
        self,
        interaction: Integration,
        member: nextcord.Member = SlashOption(
            name='member',
            description='Member to refresh with their current Steam Name.',
            required=False
        )

    ):
        """
        Refresh stuff goes here...
        """


        if member and is_in_role(interaction.user.roles, 925530598737596507):
            logger.info('%s(%s) is going to refresh %s(%s)', interaction.user.name,
                interaction.user.id, member.name, member.id)

            update_steam_name_result = await get_current_steam_name(
                interaction=interaction, member=member)

            if update_steam_name_result is None:
                await interaction.send(ephemeral=True,
                    content=f'{member.mention} is already synced with their steam name.')
            elif update_steam_name_result == 0:
                await interaction.send(ephemeral=True,
                    content=f'{member.mention} has been synced with their steam name.')
            elif update_steam_name_result == 1:
                await interaction.send(ephemeral=True,
                    content=f'{member.mention} doesn\'t have a linked steam account.')
            elif update_steam_name_result == 2:
                await interaction.send(ephemeral=True,
                    content=f'{member.mention} is not in the database.')
            elif update_steam_name_result == 3:
                await interaction.send(ephemeral=True,
                    content=f'{member.mention} Steam error. Try again later.')
            elif update_steam_name_result == 4:
                await interaction.send(ephemeral=True,
                    content=f'{member.mention} error updating the database.')
            elif update_steam_name_result == 5:
                await interaction.send(ephemeral=True,content=
                    f'{member.mention} error updating nick in discord. Check bot permissions.')

        if member and not is_in_role(interaction.user.roles, 925530598737596507):
            logger.info('%s(%s) tried to refresh %s(%s)', interaction.user.name,
                interaction.user.id, member.name, member.id)
            await interaction.send(ephemeral=True,
                content='Only <@&925530598737596507> can refresh other people\'s names.')

        update_steam_name_result = await get_current_steam_name(
            interaction=interaction, member=interaction.user)

        if update_steam_name_result is None:
            print(update_steam_name_result)
            await interaction.send(ephemeral=True, content=
                f'{interaction.user.mention} your already synced with your steam name.')
        elif update_steam_name_result == 0:
            await interaction.send(ephemeral=True, content=
                f'{interaction.user.mention} your name has been synced with your steam name.')
        elif update_steam_name_result == 1:
            await interaction.send(ephemeral=True,
                content=f'{interaction.user.mention} you don\'t have a linked steam account.')
        elif update_steam_name_result == 2:
            await interaction.send(ephemeral=True,
                content=f'{interaction.user.mention} you aren\'t in the database.')
        elif update_steam_name_result == 3:
            await interaction.send(ephemeral=True,
                content=f'{interaction.user.mention} Steam error. Try again later.')
        elif update_steam_name_result == 4:
            await interaction.send(ephemeral=True,
                content=f'{interaction.user.mention} there was an error updating the database.')
        elif update_steam_name_result == 5:
            await interaction.send(ephemeral=True,
                content=f'{interaction.user.mention} error updating your nick.')
        else:
            await interaction.send(ephemeral=True,
                content=f'{interaction.user.mention} something went wrong...')


def setup(bot):
    """
    Magic
    """
    bot.add_cog(RefreshNameCog(bot))
