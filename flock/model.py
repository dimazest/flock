from sqlalchemy import Column, Table, UniqueConstraint, MetaData, types
from sqlalchemy.dialects import postgresql as pg

from sqlalchemy.ext.declarative import declarative_base

metadata = MetaData()
Base = declarative_base(metadata=metadata)


class Tweet(Base):
    __tablename__ = 'tweet'
    __table_args__ = (
        UniqueConstraint('tweet_id', 'collection', name='uix_'),
    )

    id = Column(types.Integer, primary_key=True)

    tweet_id = Column(types.BigInteger, nullable=False)
    collection = Column(types.String, nullable=False)

    # tweet = Column(pg.JSONB, nullable=False)
    label = Column(types.String)
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
