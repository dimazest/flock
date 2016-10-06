from sqlalchemy import Table, Column, BigInteger, MetaData
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import mapper

from poultry.tweet import Tweet

metadata = MetaData()


tweet_table = Table(
    'tweet', metadata,

    Column('_id', BigInteger, primary_key=True),
    Column('tweet', pg.JSONB, nullable=False),

)


mapper(
    Tweet, tweet_table
)
