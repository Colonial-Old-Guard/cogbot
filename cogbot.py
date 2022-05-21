

import os
import logging

# nextcord stuff
import nextcord
from nextcord.ext import commands

# sqlalchemy
from sqlalchemy import create_engine, Column, String, Text, Integer, BigInteger, Boolean, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.schema import ForeignKey
from sqlalchemy.orm import sessionmaker

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
  if (os.getenv('DATABASE') == 'sqlite'):
    db_string = 'sqlite:///{}'.format(os.getenv('DATABASE_DB'))
    return db_string
  elif (os.getenv('DATABASE') == 'postgresql'):
    db_string = 'postgresql://{}:{}@{}:{}/{}'.format(
      os.getenv('DATABASE_USERNAME'),
      os.getenv('DATABASE_PASSWORD'),
      os.getenv('DATABASE_HOSTNAME'),
      os.getenv('DATABASE_PORT'),
      os.getenv('DATABASE_DB'))
    return db_string

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
intents.members = True
# bot = nextcord.Client()
bot = commands.Bot(command_prefix='.', Intents=intents)


class MembersInfo(Base):
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

class Ranks(Base):
  __tablename__ = 'ranks'

  id = Column(Integer, primary_key=True)
  rank_weight = Column(Integer, nullable=False, unique=True)
  rank_name = Column(String, nullable=False)
  staff = Column(Boolean, nullable=False)
  auto_promotion_enabled = Column(Boolean, nullable=False)

class PromotionRecomendation(Base):
  __tablename__ = 'promotion_recomendation'

  member_discord_id = Column(BigInteger, ForeignKey('member_info.discord_id'), primary_key=True)
  officer_discord_id = Column(BigInteger, ForeignKey('member_info.discord_id'), primary_key=True)
  notes = Column(Text, nullable=True)
  recommendation_datetime = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

# DB Magic
Base.metadata.create_all(engine)
Session = sessionmaker(bind = engine)
db = Session()

# Hello world
@bot.event
async def on_ready():
    logger.info(f"COGBOT is running!")

# load cogs
@bot.command()
async def load(ctx, extension):
    logger.debug(f'Loading cog extension: {extension}')
    bot.load_extension(f'cogs.{extension}')

@bot.command()
async def unload(ctx, extension):
    logger.debug(f'Unloading cog extension: {extension}')
    bot.unload_extension(f'cogs.{extension}')

for filename in os.listdir('./cogs'):
    logger.debug(f'Loading cogs: {filename}')
    if filename.endswith('.py'):
        bot.load_extension(f'cogs.{filename[:-3]}')   

# runs mah bot
bot.run(os.getenv('DISCORD_TOKEN'))