""" COG bot for managing promotion stuff in the discord """

import os
import logging
import datetime

# steam / rest api stuff
# import datetime
import json
import requests
from requests.structures import CaseInsensitiveDict


# nextcord stuff
import nextcord
from nextcord import Forbidden, HTTPException
from nextcord.ext import commands

# sqlalchemy
from sqlalchemy import create_engine, Column, String, Text, Integer, \
  BigInteger, Boolean, DateTime, func, select, insert, literal_column,\
    Identity, update
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.schema import ForeignKey
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound

# dotenv
from dotenv import load_dotenv
load_dotenv()




# Init logging
logger = logging.getLogger(__name__)
loglevel = os.getenv('LOGLEVEL', default = 'WARNING')
logging.basicConfig(
  filename=os.getenv('LOGFILE', default = 'cogbot.log'),
  level=loglevel,
  format='%(asctime)s | %(levelname)s | %(name)s | %(funcName)s | %(message)s'
)


# set sql logs to the same value for debugging
logging.getLogger('sqlalchemy.engine').setLevel(loglevel)
logging.getLogger('sqlalchemy.pool').setLevel(loglevel)


# create a db string from env
def get_db_string():
    """
    Creates a connection string from the env settings
    """
    if os.getenv('DATABASE') == 'sqlite':
        result = f"sqlite:///{os.getenv('DATABASE_DB')}"
        return result
    if os.getenv('DATABASE') == 'postgresql':
        result = (
          f"postgresql://"
          f"{os.getenv('DATABASE_USERNAME')}:"
          f"{os.getenv('DATABASE_PASSWORD')}@"
          f"{os.getenv('DATABASE_HOSTNAME')}:"
          f"{os.getenv('DATABASE_PORT')}/"
          f"{os.getenv('DATABASE_DB')}"
          )
        return result
    return None

db_string = get_db_string()

# create engine and base, you can add echo = True here if needed.
engine = create_engine(db_string)
Base = declarative_base()

# COG Discord ID
cogGuild = [925496565177667664]

# pull the steam token
steam_token = os.getenv('STEAM_TOKEN')

# Init bot
intents = nextcord.Intents(messages=True, guilds=True)
# pylint: disable=assigning-non-slot
intents.members = True
# bot = nextcord.Client()
bot = commands.Bot(intents=intents)


# pylint: disable=too-few-public-methods
class MembersInfo(Base):
    """
    Member class for DB
    """
    __tablename__ = 'member_info'

    id  = Column(Integer, primary_key=True)
    discord_id = Column(BigInteger, unique=True, nullable=False)
    discord_discriminator = Column(String, nullable=False)
    steam_64 = Column(BigInteger)
    name = Column(String)
    rank_id = Column(Integer, ForeignKey('ranks.id'))
    joined_datetime = Column(DateTime(timezone=True))
    verified = Column(Boolean)
    verified_datetime = Column(DateTime(timezone=True))
    last_promotion_datetime = Column(DateTime(timezone=True))

# pylint: disable=too-few-public-methods
class MembersList(Base):
    """
    Members list class for DB
    """
    __tablename__ = 'members_list'

    id = Column(BigInteger, Identity(start=1000, cycle=True), primary_key=True)
    discord_id = Column(BigInteger, unique=True, nullable=False)
    current_revision = Column(BigInteger, unique=True)

# pylint: disable=too-few-public-methods
class MembersDetails(Base):
    """
    Members details class for DB
    """
    __tablename__ = 'members_details'

    member_info_id = Column(BigInteger, ForeignKey('members_list.id',
        ondelete="CASCADE"), primary_key=True)
    revision = Column(BigInteger, Identity(start=101, cycle=True), primary_key=True)
    discord_discriminator = Column(String, nullable=False)
    steam_64 = Column(BigInteger)
    steam_name = Column(String)
    discord_joined_datetime = Column(DateTime(timezone=True))
    is_verified = Column(Boolean, nullable=False)
    last_modified_datetime = Column(DateTime(timezone=True),
        nullable=False, server_default=func.now())
    last_modified_by = Column(String, nullable=False)
    last_modified_by_id = Column(BigInteger, nullable=False)
    regiment = Column(BigInteger, ForeignKey('regiments.id'))
    role = Column(BigInteger, ForeignKey('roles.id'))

# pylint: disable=too-few-public-methods
class Regiments(Base):
    """
    Regiments table for DB
    """
    __tablename__ = 'regiments'

    id = Column(BigInteger,Identity(start=101, cycle=True), ForeignKey('members_list.id',
        ondelete="CASCADE"), primary_key=True)
    tag = Column(String, nullable=False)
    name = Column(String, nullable=False)
    affiliation = Column(String, nullable=False)

# pylint: disable=too-few-public-methods
class Roles(Base):
    """
    Roles table for DB
    """
    __tablename__ = 'roles'

    id = Column(BigInteger,Identity(start=101, cycle=True), ForeignKey('members_list.id',
        ondelete="CASCADE"), primary_key=True)
    name = Column(String, nullable=False)

# pylint: disable=too-few-public-methods
class Ranks(Base):
    """
    Ranks class for DB
    """
    __tablename__ = 'ranks'

    id = Column(Integer, primary_key=True)
    rank_weight = Column(Integer, nullable=False, unique=True)
    rank_name = Column(String, nullable=False)
    staff = Column(Boolean, nullable=False)
    auto_promotion_enabled = Column(Boolean, nullable=False)

# pylint: disable=too-few-public-methods
class PromotionRecommendation(Base):
    """
    Promotion class for DB
    """
    __tablename__ = 'promotion_recommendation'

    member_discord_id = Column(BigInteger, ForeignKey('member_info.discord_id'), primary_key=True)
    officer_discord_id = Column(BigInteger, ForeignKey('member_info.discord_id'), primary_key=True)
    notes = Column(Text, nullable=True)
    recommendation_datetime = Column(DateTime(timezone=True), \
      nullable=False, server_default=func.now())

# DB Magic
Base.metadata.create_all(engine)
Session = sessionmaker(bind = engine)
db = Session()

# stuff to be imported into cogs
VANITY_URL = 'https://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/'
STEAM_PROFILE_URL = 'https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/'
headers = CaseInsensitiveDict()
headers["Accept"] = "application/json"

async def get_steam_profile(steam_64):
    """
    Returns parsed JSON response of a steam profile if provided with a valid steam id
    """
    logger.debug("Running get_steam_profile with id: %s", steam_64)
    params = {"key": steam_token, "steamids": steam_64}
    resp = requests.get(STEAM_PROFILE_URL, headers=headers, params=params, timeout=10)
    if not resp.status_code == requests.codes['ok']:
        logger.debug("HTTP error: %s", resp)
        return None
    logger.debug("Request result: %s", resp)
    result = json.loads(resp.content)
    logger.debug("Request result after json conversion: %s", result)
    return result

async def get_steam_id(vanity):
    """
    Returns parsed JSON response of a steam id if provided with a valid steam vanity name
    """
    logger.debug("Running get_steam_id with vanity: %s", vanity)
    params = {"key": steam_token, "vanityurl": vanity}
    resp = requests.get(VANITY_URL, headers=headers, params=params, timeout=10)
    if not resp.status_code == requests.codes['ok']:
        logger.debug("HTTP error: %s", resp)
        return None
    logger.debug("Request result: %s", resp)
    result = json.loads(resp.content)
    logger.debug("Request result after json conversion: %s", result)
    return result

async def get_steam_plus_name(steam_type: type, steam_id_or_vanity: str):
    """
    Returns the full steam profile of what you send in?
    """
    logger.debug("Running get_steam_plus_name with type (%s) and id (%s)",
        steam_type, steam_id_or_vanity)
    if steam_type == "id":
        steam_id = await get_steam_id(steam_id_or_vanity)
        if steam_id is None:
            return None
        # make sure to only pass the steam64 id into the get_steam_profile function...
        result = await get_steam_profile(steam_id["response"]["steamid"])
        if result is None:
            return None
        return result
    if steam_type == "profiles":
        result = await get_steam_profile(steam_id_or_vanity)
        if result is None:
            return None
        return result

def is_cog(roles: list):
    """
    Returns True if the member.roles snowflake contains the COG role (926172865097781299).
    """
    roles_int = []
    for role in roles:
        roles_int.append(role.id)
    return bool(926172865097781299 in roles_int)

def is_in_role(member, role: int):
    """
    Returns True if the member.roles snowflake contains the role submitted.
    """
    self_roles_int = []
    for self_role in member.roles:
        self_roles_int.append(self_role.id)
    return bool(int(role) in self_roles_int)

def is_logi_lead(member):
    """
    Returns true if a the member is a COG Logi lead.
    Feed me the member snowflake.
    """
    # 49 = 136929317316853760, Ulune = 606234691531702324,
    # persus = 145420538725007361, davey = 148818653452697600
    logi_lead_list = [
        136929317316853760,
        606234691531702324,
        145420538725007361,
        148818653452697600]
    return bool(member.id in logi_lead_list)

async def get_all_member_info():
    """
    Returns all members and their ranks from the DB
    """
    result = {}
    statement = select(MembersInfo, Ranks).filter(MembersInfo.rank_id==Ranks.id).where(
        MembersInfo.last_promotion_datetime <= datetime.datetime.utcnow() \
        - datetime.timedelta(days=7)).order_by(
            Ranks.rank_weight, MembersInfo.last_promotion_datetime)
    try:
        result = db.execute(statement).all()
        return result
    except NoResultFound as error:
        logger.error("No results found: %s", error)
        return None

async def is_in_member_list(discord_id):
    """
    Returns if in memberlist table on the DB
    """
    result = {}
    statement = select(MembersList, MembersDetails).filter(
        MembersList.id==MembersDetails.member_info_id,
    MembersList.current_revision==MembersDetails.revision).where(
        MembersList.discord_id==discord_id)
    logger.debug("Checking if user has valid record in members_list: %s", statement)
    try:
        result = db.execute(statement).all()
        logger.debug("Result from is_in_member_list: %s", result)
        return result
    except NoResultFound as error:
        logger.error("No results found: %s", error)
        return None

async def update_member_verification(verification_type :list, member :nextcord.Member,
    interaction :nextcord.Interaction, steam=None):
    """
    Add or renew member verification
    """

    if_in_member_list = await is_in_member_list(member.id)
    discriminator_name_list = [interaction.user.name+"#"+interaction.user.discriminator,
        member.name+"#"+member.discriminator]

    logger.debug("Running update_member_verification, invoked by %s|%s for user %s|%s",
        interaction.user.id,discriminator_name_list[0],member.id,discriminator_name_list[1])
    if steam is None:
        logger.debug("No steam value provided")
        steam = [None, None]

    # If in memberslist, then apply new stuff (verify/retire/unretire)
    if if_in_member_list and verification_type=='cog':
        # print(f"is in list: {if_in_member_list}")
        logger.debug("%s|%s is in members_list",member.id,discriminator_name_list[1])

        for member_list, member_details in if_in_member_list:
            logger.debug("SQL results: {%s}{%s}",member_list,member_details)


            if member_details.is_verified:
                await interaction.send(ephemeral=True, content=
                f"<@{member.id}> is already verified.")
                logger.debug("%s|%s is already verified",member.id,discriminator_name_list[1])
                return None
            statement_add_details = insert(MembersDetails).values(
                member_info_id=member_list.id, discord_discriminator=discriminator_name_list[1],
                discord_joined_datetime=member.joined_at, is_verified=True,
                last_modified_by=discriminator_name_list[0],
                last_modified_by_id=interaction.user.id,
                steam_name=steam[1], steam_64=steam[0]
            ).returning(literal_column('*'))

            for add_details in db.execute(statement_add_details):
                logger.debug("SQL add details: %s", add_details)
                statement_update_list = update(MembersList).where(MembersList.discord_id==member.id
                ).values(current_revision=add_details.revision)

            try:
                db.execute(statement_update_list)
                logger.debug("SQL commit result: %s", db.commit())
                return 1
            except NoResultFound as error:
                db.rollback()
                logger.error("No results found: %s", error)
                return None

    else:
        logger.debug("%s|%s is not in members_list, adding now",
            member.id,discriminator_name_list[1])
        statement_add_list = insert(MembersList).values(
            discord_id=member.id).returning(literal_column('*'))

        for add_list in db.execute(statement_add_list):
            logger.debug("SQL add list: %s", add_list)
            statement_add_details = insert(MembersDetails).values(
                member_info_id=add_list.id, discord_discriminator=discriminator_name_list[1],
                discord_joined_datetime=member.joined_at, is_verified=True,
                last_modified_by=discriminator_name_list[0],
                last_modified_by_id=interaction.user.id,
                steam_name=steam[1], steam_64=steam[0]
            ).returning(literal_column('*'))

        for add_details in db.execute(statement_add_details):
            logger.debug("SQL add details: %s", add_details)
            statement_update_list = update(MembersList).where(MembersList.discord_id==member.id
            ).values(current_revision=add_details.revision)

        try:
            db.execute(statement_update_list)
            result = db.commit()
            logger.debug("SQL commit result: %s", result)
            return 1
        except NoResultFound as error:
            db.rollback()
            logger.error("No results found: %s", error)
            return None

async def get_member_info(member, all_history:bool = False):
    """
    Get current member info, see also get_member_historic_info
    """


    member_id = member
    logger.debug('Given %s as input', member)
    try:
        if member.id:
            member_id = member.id
            logger.debug('Updating member_id to %s', member_id)
    except AttributeError:
        member_id = member

    statement_get_details = []

    if all_history:
        statement_get_details = select(MembersList, MembersDetails).filter(
            MembersList.id==MembersDetails.member_info_id)\
            .where(MembersList.discord_id==member_id).order_by(
                MembersDetails.last_modified_datetime.desc())
    elif not all_history:
        statement_get_details = select(MembersList, MembersDetails).filter(
            MembersList.id==MembersDetails.member_info_id,
            MembersList.current_revision==MembersDetails.revision)\
            .where(MembersList.discord_id==member_id)


    try:
        # result = db.execute(statement_get_details).scalar_one_or_none()
        result = db.execute(statement_get_details)
        db.commit()
        logger.debug('get_member_info result: %s', result)
        return result
    except NoResultFound as error:
        db.rollback()
        logger.error("No results found: %s", error)
        return None

# Hello world
@bot.event
async def on_ready():
    """
    Bot is running!
    """
    logger.info("COGBOT is running!")

# load cogs
@bot.command()
# pylint: disable=unused-argument
async def load(ctx, extension):
    """
    Load cogs
    """
    logger.debug('Loading cog extension: %s', extension)
    bot.load_extension(f'cogs.{extension}')

@bot.command()
# pylint: disable=unused-argument
async def unload(ctx, extension):
    """
    Unload cogs
    """
    logger.debug('Unloading cog extension: %s', extension)
    bot.unload_extension(f'cogs.{extension}')

for filename in os.listdir('./cogs'):
    logger.debug('Loading cogs: %s', filename)
    if filename.endswith('.py'):
        bot.load_extension(f'cogs.{filename[:-3]}')

@bot.event
async def on_member_update(before, after):
    """
    Monitors member updates, and triggers stuff
    """
    # 6 hour power role added to a user
    if not is_in_role(before, 990455799765667860) and is_in_role(after, 990455799765667860):

        # Check if member has the recruit role
        if is_in_role(after, 1034206227728699522):
            recruit_role = after.guild.get_role(1034206227728699522)
            promotion_recruits_channel = after.guild.get_channel(971763222937993236)
            try:
                await after.remove_roles(recruit_role, reason='6hourpower role has been reached!')
                logger.info('%s(%s) 6hourpower role has been reached! Removing recruit role',
                    after.name, after.id)
                await promotion_recruits_channel.send(content=f"{after.mention} has gotten the "
                    f"<@&990455799765667860> role, so the {recruit_role.mention} has been removed")
            except Forbidden as error:
                logger.error("Incorrect permissions changing roles of "
                    "%s|%s: %s", after.name, after.id, error)
            except HTTPException as error:
                logger.error("HTTP error updating roles of %s|%s: %s", after.name, after.id, error)


# runs mah bot
bot.run(os.getenv('DISCORD_TOKEN'))
