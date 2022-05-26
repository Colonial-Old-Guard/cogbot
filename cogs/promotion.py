""" Promotion cog """
import time
import datetime

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
        logger.error("No results found: %s", error)
        return None

async def get_all_member_info():
    """
    Returns all members and their ranks from the DB
    """
    result = {}
    statement = select(MembersInfo, Ranks).filter(MembersInfo.rank_id==Ranks.id).where(Ranks.auto_promotion_enabled == True and MembersInfo.last_promotion_datetime >= datetime.datetime.utcnow() - datetime.timedelta(days=7))
    try:
        result = db.execute(statement).all()
        return result
    except NoResultFound as error:
        logger.error("No results found: %s", error)
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


def get_member_promotion_status(discord_id: int, member, interaction: nextcord.Interaction):
    """
    Returns a member promotion status when provided with a discord id
    """
    member_db = member_info(discord_id)
    member_rank = rank_info_and_next_rank(member_db.rank_id)

    if member_db is None or member_rank is None:
        return None

    embed = nextcord.Embed(
        title="Promotion status",
        timestamp=interaction.created_at)
    embed.add_field(name="Member", value=f"{member.nick}: {member.mention}")
    embed.add_field(name="Verified", value=\
        f"<t:{int(time.mktime(member_db.verified_datetime.timetuple()))}:f>")
    embed.add_field(name="Last Promotion", value=\
        f"<t:{int(time.mktime(member_db.last_promotion_datetime.timetuple()))}:f>")
    embed.add_field(name="Rank", value=member_rank[0][0])
    embed.add_field(name="Next Promotion Rank", value=member_rank[1][0])
    return embed

async def promote_member(member, interaction: nextcord.Interaction, hidden: bool):
    """
    Promotoes a member, and returns an embed with the details.
    Status:
    0 = Member promoted
    1 = Member not eligible for promotion
    2 = Error promoting member
    """

    status = 2

    member_db = member_info(member.id)
    member_rank = rank_info_and_next_rank(member_db.rank_id)
    member_steam = await get_steam_profile(member_db.steam_64)

    promotion_recruits_channel = interaction.guild.get_channel(940626074344239194)


    if member_rank[0][1] > member_rank[1][1] \
        and member_steam["response"]["players"][0]["personaname"]:
        new_name_and_rank = member_rank[1][0] + " | " \
            + member_steam["response"]["players"][0]["personaname"]
        statement = update(MembersInfo).where\
            (MembersInfo.discord_id == member.id).values\
                (rank_id = member_rank[1][2], last_promotion_datetime = func.now())

        embed = nextcord.Embed(
            title="Promotion!",
            timestamp=interaction.created_at,
            colour=nextcord.Color.gold())
        embed.add_field(name="Member", value=member.mention)
        embed.add_field(name="Officer Promoting",
            value=interaction.user.mention)
        embed.add_field(name="Last Promotion", value=
    f"<t:{int(time.mktime(member_db.last_promotion_datetime.timetuple()))}:f>")
        embed.add_field(name="Old Rank", value=member_rank[0][0])
        embed.add_field(name="New Rank", value=member_rank[1][0])

        try:
            logger.info(
                f"Promoting {member.name}|{member.id} from "
                f"{member_rank[0]}:{member_rank[0][2]} to "
                f"{member_rank[1]}:{member_rank[1][2]}")
            db.execute(statement)
            result = db.commit()
            logger.info("Updated the database successfully: %s", result)
            try:
                logger.info(
                    f"Changing nick of {member.name}|{member.id} to "
                    f"{new_name_and_rank}")
                await member.edit(nick=new_name_and_rank)
                await promotion_recruits_channel.send(embed=embed)
                status = 0
                if hidden:
                    await interaction.send(ephemeral=True, embed=embed)
                else: await interaction.send(embed=embed)
            except Forbidden as error:
                print(f"no permissions: {error}")
                logger.error(f"Incorrect permissions changing nick of"
                    f"{member.name}|{member.id}: {error}")
            except HTTPException as error:
                print(f"Other error: {error}")
                logger.error(f"HTTP error updating nick of"
                    f"{member.name}|{member.id}: {error}")
        except IntegrityError as error:
            logger.error("Error updating the db: %s", error)
            db.rollback()
    else:
        status = 1
        embed = {}
    return status, embed

async def get_promotion_list(interaction: nextcord.Integration):
    """
    Returns an embed of current users, ranks, and last promotion date.
    """
    # member_list = []
    username = []
    rank_n = []
    promotion_date = []

    for member, rank in await get_all_member_info():
        # fuck = f"<@{member.discord_id}", f"<t:{int(time.mktime(member.last_promotion_datetime.timetuple()))}:f>", rank.rank_name

        username.append(f"<@{member.discord_id}")
        rank_n.append(rank.rank_name)
        promotion_date.append(f"<t:{int(time.mktime(member.last_promotion_datetime.timetuple()))}:f>")
        # member_list.append(fuck)


    embed = nextcord.Embed(
        title="Promotion / Members List",
        timestamp=interaction.created_at,
        colour=nextcord.Color.purple())
    # embed.author(interaction.user.mention)
    print(len(username))
    print(len(rank_n))
    print(len(promotion_date))
    embed.set_author(name=interaction.user.name)
    embed.add_field(name="Username", value=username)
    embed.add_field(name="Rank", value=rank_n)
    embed.add_field(name="Promotion Date", value=promotion_date)

        # print(result)

    # for member_details in member_list:
    #     embed.add_field(name="Username", value=f"<@{member_details[0]}>")
    #     embed.add_field(name="Rank", value=member_details[2])
    #     embed.add_field(name="Promotion Date",value=f"<t:{int(time.mktime(member_details[1].timetuple()))}:f>")

    return embed

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

    # pylint: disable=no-self-use
    async def promotion(
        self,
        interaction: Integration,
        command: str = SlashOption(
            name="command",description="What do you want to do?",\
                required=True,choices={"Status": "status", "Promote": "promote", "List": "list"}
            ),
        member: nextcord.Member = SlashOption(
            name="member",
            description="Member for promotion",
            required=False
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


        # if is_cog(member.roles) is False:
        #     # Check if mentioned user has the COG role, exit if not
        #     await interaction.send(ephemeral=True, \
        #         content=f"This user is not in COG {member.mention}")
        #     return

        if member and command == "status":
            if is_cog(member.roles) is False:
                # Check if mentioned user has the COG role, exit if not
                await interaction.send(ephemeral=True, \
                    content=f"This user is not in COG {member.mention}")
                return
            if hidden:
                await interaction.send(ephemeral=True,\
                    embed=get_member_promotion_status(member.id, member, interaction))
            else:
                await interaction.send(ephemeral=False,\
                    embed=get_member_promotion_status(member.id, member, interaction))

        if command == 'list':
            dong = await get_promotion_list(interaction)
            logger.error(dong)
            await interaction.send(ephemeral=True, embed=dong)


        if member and command == "promote":
            if is_cog(member.roles) is False:
                # Check if mentioned user has the COG role, exit if not
                await interaction.send(ephemeral=True, \
                    content=f"This user is not in COG {member.mention}")
                return
            promotion_details = await promote_member(member, interaction, hidden)

            if promotion_details[0] == 1:
                await interaction.send(ephemeral=True,
                    content="Member cannot be promoted")
            elif promotion_details[0] == 0 and hidden and promotion_details[1] is not None:
                await interaction.send(ephemeral=True,
                    embed=promotion_details[1])
            elif promotion_details[0] == 0 and hidden is False \
                and promotion_details[1] is not None:
                await interaction.send(ephemeral=False,
                    embed=promotion_details[1])
            else:
                await interaction.send(ephemeral=True,
                    content="Something went wrong...")


def setup(bot):
    """
    Magic
    """
    bot.add_cog(PromotionCog(bot))
