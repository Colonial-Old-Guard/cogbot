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
from nextcord.ext import commands

# sqlalchemy
from sqlalchemy import create_engine, Column, String, Text, Integer, \
  BigInteger, Boolean, DateTime, func, select
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


# set sql logs to the same value for debuging
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
bot = commands.Bot(Intents=intents)


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
class PromotionRecomendation(Base):
    """
    Promotion class for DB
    """
    __tablename__ = 'promotion_recomendation'

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
    resp = requests.get(STEAM_PROFILE_URL, headers=headers, params=params)
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
    resp = requests.get(VANITY_URL, headers=headers, params=params)
    logger.debug("Request result: %s", resp)
    result = json.loads(resp.content)
    logger.debug("Request result after json conversion: %s", result)
    return result

async def get_steam_plus_name(steam_type: type, steam_id_or_vanity: str):
    """
    Returns the full steam profile of what you send in?
    """
    logger.debug("Running get_steam_plus_name")
    if steam_type == "id":
        steam_id = await get_steam_id(steam_id_or_vanity)
        # make sure to only pass the steam64 id into the get_steam_profile function...
        result = await get_steam_profile(steam_id["response"]["steamid"])
        return result
    if steam_type == "profiles":
        result = await get_steam_profile(steam_id_or_vanity)
        return result

def is_cog(roles: list):
    """
    Returns true if in COG, feed me the member.roles snowflake.
    """
    roles_int = []
    for role in roles:
        roles_int.append(role.id)
    return bool(926172865097781299 in roles_int)

def is_logi_lead(member):
    """
    Returns true if a the member is a COG Logi lead.
    Feed me the member snowflake.
    """
    # 49 = 136929317316853760, Ulune = 606234691531702324, pesus = 145420538725007361, davey = 148818653452697600
    logi_lead_list = [136929317316853760, 606234691531702324, 145420538725007361, 148818653452697600]
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

# runs mah bot
bot.run(os.getenv('DISCORD_TOKEN'))
