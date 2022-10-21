"""Retire COG """

# nextcord stuff
import nextcord
from nextcord.ext import commands
from nextcord import Integration, SlashOption, Forbidden, HTTPException

# the bot bits
# pylint: disable=import-error
from cogbot import logger, cogGuild, is_in_role

if __name__ == '__main__':
    # pylint: disable=pointless-statement
    exit

async def retire_member(interaction, member, roles):
    """
    retire a member
    """
    missing_roles = []
    retired_role = interaction.guild.get_role(925780963231940688)
    # member = interaction.user
    for role in roles:
        if is_in_role(interaction.user, role):
            missing_roles.append(interaction.guild.get_role(role))


    for role in missing_roles:
        try:
            await member.remove_roles(role, reason='Retirement')
            logger.debug('Removed %s from %s', role.name, member.id)
        except Forbidden as error:
            logger.error(f"Incorrect permissions changing roles of "
                f"{member.name}|{member.id}: {error}")
        except HTTPException as error:
            logger.error(f"HTTP error updating roles of "
                f"{member.name}|{member.id}: {error}")
    try:
        await member.add_roles(retired_role, reason='Retirement')
        logger.debug('Added %s from %s', role, member.id)
    except Forbidden as error:
        logger.error(f"Incorrect permissions changing roles of "
            f"{member.name}|{member.id}: {error}")
    except HTTPException as error:
        logger.error(f"HTTP error updating roles of "
            f"{member.name}|{member.id}: {error}")

    return True


class RetirementCog(commands.Cog):
    """
    Promotions cog
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @nextcord.slash_command(
        name='retire',
        description='Retire yourself, a member, or a role. (depending on your permissions)',
        guild_ids=cogGuild,
    )
    # pylint: disable=no-self-use
    async def retire(
        self,
        interaction: Integration,
        member: nextcord.Member = SlashOption(
            name='member',
            description='Member to retire',
            required=False
        ),
        role: nextcord.Role = SlashOption(
            name='role',
            description='Role to retire',
            required=False
        )

    ):
        """
        Retirement command stuff
        """
        verified_only_roles = [925530598737596507,926193382307541022,925531069896355891,
        986362366809735269,940623612069679104,986367224040288336,926172865097781299,
        925770000067858442,925720078027223070,980563823226404895,978341688168833034,
        978341943736168478,978342030927335444,978342077211492383,925781878722674779,
        925531185554276403]

        # missing_roles = []


        # fuck = nextcord.abc.Snowflake

        # retired_role = 925780963231940688
        if not member and not role:
            logger.info('%s|%s is retiring themselves', interaction.user.id,interaction.user.name)
            await interaction.response.send_message(ephemeral=True,
            content="You are going to retire.")

            if await retire_member(interaction=interaction, member=interaction.user,
                roles=verified_only_roles):
                await interaction.channel.send(
                    content=f'Retired {interaction.user.mention}')


        elif member and role:
            logger.info('%s|%s is derping with this command', interaction.user.id,
            interaction.user.name)
            await interaction.response.send_message(ephemeral=True,
            content="You can't use retire both a member and a role at the same time.")

        elif member:
            logger.info('%s|%s is retiring the member %s|%s', interaction.user.id,
            interaction.user.name, member.id, member.name)
            await interaction.response.send_message(ephemeral=True,
            content=f"Retiring {member.mention}")

            if await retire_member(interaction=interaction, member=member,
                roles=verified_only_roles):
                await interaction.channel.send(
                    content=f'Retired {member.mention}')

        elif role:
            logger.info('%s|%s is retiring the role %s|%s', interaction.user.id,
            interaction.user.name, role.id, role.name)
            await interaction.response.send_message(
            content=f"Retiring all members of {role.mention}")

            for role_member in role.members:
                if await retire_member(interaction=interaction, member=role_member,
                    roles=verified_only_roles):
                    await interaction.channel.send(
                        content=f'Retired all members of {role.mention}')




def setup(bot):
    """
    Magic
    """
    bot.add_cog(RetirementCog(bot))
