from sqlalchemy import Column, Table, MetaData, types
from sqlalchemy.dialects import postgresql as pg

from sqlalchemy.ext.declarative import declarative_base

metadata = MetaData()
Base = declarative_base(metadata=metadata)


class Tweet(Base):
    __tablename__ = 'tweet'

    id = Column(types.BigInteger, primary_key=True)
    tweet = Column(pg.JSONB, nullable=False)
    features = Column(pg.JSONB)

    created_at = Column(types.DateTime, nullable=False)


screen_name_view = Table(
    'screen_name', metadata,
    Column('screen_name', types.String),
    Column('lv', types.String),
    Column('ru', types.String),
    Column('en', types.String),
    Column('total', types.Integer),
    Column('score', types.Float),
)


user_mention_view = Table(
    'user_mention', metadata,
    Column('user_mention', types.String),
    Column('lv', types.String),
    Column('ru', types.String),
    Column('en', types.String),
    Column('total', types.Integer),
    Column('score', types.Float),
)
