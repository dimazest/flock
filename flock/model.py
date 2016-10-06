from sqlalchemy import Column, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects import postgresql as pg

Base = declarative_base()


class Tweet(Base):
    __tablename__ = 'tweet'

    id = Column(BigInteger, primary_key=True)
    tweet = Column(pg.JSONB)
