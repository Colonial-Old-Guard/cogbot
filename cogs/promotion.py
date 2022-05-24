""" Promotion cog """
import time

# nextcord stuff
import nextcord
from nextcord.ext import commands
from nextcord import Integration, SlashOption, Forbidden, HTTPException

# sqlalchemy
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound

# the bot bits
# pylint: disable=import-error
from cogbot import logger, cogGuild, db, MembersInfo, Ranks, get_steam_profile, is_cog

if __name__ == "__main__":
    # pylint: disable=pointless-statement
    exit

def get_ranks():
    """
    Returns the current ranks list
    """
    result = {}
    statement = select(Ranks.rank_name, Ranks.rank_weight, Ranks.id, \
        Ranks.auto_promotion_enabled).order_by(Ranks.rank_weight)
    try:
        # result = db.execute(statement).mappings().all()
        result = db.execute(statement).all()
        # for row in db.execute(statement):
        #     result[row.rank_weight] = {'rank': row.rank_name, \
        # 'auto_promotion': row.auto_promotion_enabled, 'id': row.id}
        #     # result =
        #     # result.append(row)
        return result
    except IntegrityError as error:
        logger.error(f"Error: {error}")
        return None

def member_info(discord_id):
    """
    Returns the database content of the member who's discord id is provided.
    """
    result = {}
    try:
        result = db.execute(select(MembersInfo).where\
            (MembersInfo.discord_id == discord_id)).one_or_none()
        if not result is None:
            result = result[0]
        return result
    except NoResultFound as error:
        logger.error(f"No results found: {error}")
        return None

def rank_info_and_next_rank(rank_id):
    """
    Returns rank info for the rank id + the next rank above
    """
    result = []
    ranks = get_ranks()
    i=0

    while i < len(ranks):
        if ranks[i][2] == rank_id:
            result.append(ranks[i])

            # avoid promoting Col to Rec
            if i == 0:
                result.append(ranks[i])
            else: result.append(ranks[i-1])
        i += 1

    return result


class PromotionCog(commands.Cog):
    """
    Promotions cog
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot



    @nextcord.slash_command(
        name="promotion",
        description="Promote a member",
        default_permission=False,
        guild_ids=cogGuild,
    )

    # pylint: disable=no-self-use,too-many-branches,too-many-statements,too-many-nested-blocks
    async def promotion(
        self,
        interaction: Integration,
        command: str = SlashOption(
            name="command",description="What do you want to do?",\
                required=True,choices={"Status": "status", "Promote": "promote"}
            ),
        member: nextcord.Member = SlashOption(
            name="member",
            description="Member for promotion",
            required=True
        ),
        hidden: bool = SlashOption(
            name="hidden",
            description="Should the bot responses be visible to others",
            default=True,
            required=False
        )

    ):
        """
        Promotion stuff goes here
        """
        logger.info(f"Running promotion. command: {command} member: {member} hidden: {hidden}")
        promotion_recruits_channel = interaction.guild.get_channel(940626074344239194)


        if member.roles and command == "status":
            # Check if mentioned user has the COG role
            if is_cog(member.roles):
                member_db = member_info(member.id)


                member_rank = rank_info_and_next_rank(member_db.rank_id)


                embed = nextcord.Embed(
                    title="Promotion status",
                    timestamp=interaction.created_at)
                embed.add_field(name="Member", value=member.mention)
                embed.add_field(name="Verified", value=\
                    f"<t:{int(time.mktime(member_db.verified_datetime.timetuple()))}:f>")
                embed.add_field(name="Last Promotion", value=\
                    f"<t:{int(time.mktime(member_db.last_promotion_datetime.timetuple()))}:f>")
                embed.add_field(name="Rank", value=member_rank[0][0])
                embed.add_field(name="Next Promotion Rank", value=member_rank[1][0])


                if hidden:
                    await interaction.send(ephemeral=True, embed=embed)
                else:
                    await interaction.send(ephemeral=False, embed=embed)
            else:
                await interaction.send(ephemeral=True, \
                    content=f"This member is not in COG {member.mention}")

        if member and command == "promote":
            if is_cog(member.roles):

                member_db = member_info(member.id)
                member_rank = rank_info_and_next_rank(member_db.rank_id)
                member_steam = await get_steam_profile(member_db.steam_64)

                if member_rank[0][1] > member_rank[1][1] \
                    and member_steam["response"]["players"][0]["personaname"]:
                    new_name_and_rank = member_rank[1][0] + " | " \
                        + member_steam["response"]["players"][0]["personaname"]
                    statement = update(MembersInfo).where\
                        (MembersInfo.discord_id == member.id).values\
                            (rank_id = member_rank[1][2], last_promotion_datetime = func.now())
                    try:
                        logger.info(f"Promoting {member.name}|{member.id} from \
                            {member_rank[0]}:{member_rank[0][2]} to \
                            {member_rank[1]}:{member_rank[1][2]}")
                        db.execute(statement)
                        result = db.commit()
                        logger.info(f"Updated the database successfully {result}")
                        try:
                            logger.info(f"Changing nick of \
                                {member.name}|{member.id} to {new_name_and_rank}")
                            await member.edit(nick=new_name_and_rank)

                            embed = nextcord.Embed(
                                title="Promotion!",
                                timestamp=interaction.created_at,
                                colour=nextcord.Color.gold())
                            embed.add_field(name="Member", value=member.mention)
                            embed.add_field(name="Officer Promoting",\
                                value=interaction.user.mention)
                            embed.add_field(name="Last Promotion", value=\
                        f"<t:{int(time.mktime(member_db.last_promotion_datetime.timetuple()))}:f>")
                            embed.add_field(name="Old Rank", value=member_rank[0][0])
                            embed.add_field(name="New Rank", value=member_rank[1][0])

                            await promotion_recruits_channel.send(embed=embed)

                            if hidden:
                                await interaction.send(ephemeral=True, embed=embed)
                            else: await interaction.send(embed=embed)
                        except Forbidden as error:
                            print(f"no permissions: {error}")
                            logger.error(f"Incorrect permissions changing nick of \
                                {member.name}|{member.id}: {error}")
                        except HTTPException as error:
                            print(f"Other error: {error}")
                            logger.error(f"HTTP error updating nick of \
                                {member.name}|{member.id}: {error}")
                    except IntegrityError as error:
                        logger.error("Error updating the db: %s", error)
                        db.rollback()

            else:
                await interaction.send(ephemeral=True, \
                    content=f"This member is not in COG {member.mention}")


def setup(bot):
    """
    Magic
    """
    bot.add_cog(PromotionCog(bot))
