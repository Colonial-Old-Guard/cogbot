""" Logistics cog """

# nextcord stuff
import nextcord
from nextcord.ext import commands
from nextcord import Integration, SlashOption, Forbidden, HTTPException

# the bot bits
# pylint: disable=import-error
from cogbot import logger, cogGuild, is_logi_lead

if __name__ == "__main__":
    # pylint: disable=pointless-statement
    exit

class LogiCog(commands.Cog):
    """
    Logistics cog
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @nextcord.slash_command(
        name="logistics",
        description="Grant someone logistic roles.",
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
        role: str = SlashOption(
            name="role",
            description="What role?",
            choices={
                "Logistics High Value": "925770000067858442",
                "Logistics Main": "925720078027223070",
                "Logistics Newbie": "980563823226404895"
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

        logi_log_channel = interaction.guild.get_channel(986978973382758492)


        logi_role = interaction.guild.get_role(int(role))

        if add_or_remove == "add" and is_logi_lead(interaction.user):
            if logi_role.id in member.roles:
                logger.info(f"{member.nick}|{member.id}"\
                    f" already has the {logi_role.name}|{logi_role.id} role")
                await interaction.response.send_message(ephemeral=True,content=
                f"{member.mention} already has the {logi_role.mention} role"
                )
            else:
                try:
                    logger.info(f"{interaction.user.nick}|{interaction.user.id}"\
                        f" adding {logi_role.name} to {member.nick}|{member.id}")
                    await member.add_roles(logi_role)
                    await logi_log_channel.send(content=f"{interaction.user.mention}"\
                        f" granted {logi_role.mention} to {member.mention}"
                    )
                    await interaction.response.send_message(ephemeral=True,
                        content=f"Granted {member.mention} the {logi_role.mention} role")
                except Forbidden as error:
                    print(f"no permissions: {error}")
                    logger.error(f"Incorrect permissions adding roles to "
                        f"{member.name}|{member.id}: {error}")
                except HTTPException as error:
                    print(f"Other error: {error}")
                    logger.error(f"HTTP error adding roles to "
                        f"{member.name}|{member.id}: {error}")

        if add_or_remove == "remove" and is_logi_lead(interaction.user):
            if logi_role.id in member.roles:
                try:
                    logger.info(f"{interaction.user.nick}|{interaction.user.id}"\
                        f" removing roles to {member.nick}|{member.id}")
                    await member.remove_roles(logi_role)
                    await logi_log_channel.send(content=f"{interaction.user.mention}"\
                        f" removed {logi_role.mention} to {member.mention}"
                    )
                    await interaction.response.send_message(ephemeral=True,
                        content=f"Removed {member.mention} from  the {logi_role.mention} role")
                except Forbidden as error:
                    print(f"no permissions: {error}")
                    logger.error(f"Incorrect permissions adding roles to "
                        f"{member.name}|{member.id}: {error}")
                except HTTPException as error:
                    print(f"Other error: {error}")
                    logger.error(f"HTTP error adding roles to "
                        f"{member.name}|{member.id}: {error}")
            else:
                logger.info(f"{member.nick}|{member.id}"\
                    f" does not have the {logi_role.name}|{logi_role.id} role")
                await interaction.response.send_message(ephemeral=True,content=
                f"{member.mention} does not have the {logi_role.mention} role"
                )


def setup(bot):
    """
    Magic
    """
    bot.add_cog(LogiCog(bot))
