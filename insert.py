import logging
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects import postgresql
from  sqlalchemy.sql.expression import func

from poultry import readline_dir
from poultry import tweet

logging.basicConfig(filename='flock.log', level=logging.DEBUG)
logger = logging.getLogger('flock')

engine = create_engine('postgresql://localhost/twitter')
Session = sessionmaker(bind=engine)
session = Session()
Base = declarative_base()


class Tweet(Base):
    __tablename__ = 'tweet'

    id = Column(Integer, primary_key=True)

    tweet = Column(postgresql.JSONB)


for i, tweet in enumerate(readline_dir(None)):

    if (i % 100000) == 1:
        logger.debug('Processed %s tweets, it\'s time to commit %s items.', i, len(session.new))
        session.commit()

    session.add(Tweet(tweet=tweet.parsed))

session.commit()
