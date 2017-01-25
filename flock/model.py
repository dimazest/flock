import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.dialects import postgresql as pg

from sqlalchemy.ext.declarative import declarative_base

metadata = sa.MetaData()
Base = declarative_base(metadata=metadata)


# tweet_representative = sa.Table(
#     'tweet_representative', metadata,
#     sa.Column('tweet_id', sa.BigInteger, sa.ForeignKey('tweet.tweet_id')),
#     sa.Column('collection', sa.String),
#     sa.Column('representative_tweet_id', sa.BigInteger, sa.ForeignKey('tweet.tweet_id')),
# )


class Tweet(Base):
    __tablename__ = 'tweet'
    __table_args__ = (
    )

    tweet_id = sa.Column(types.BigInteger, nullable=False, primary_key=True)
    collection = sa.Column(types.String, nullable=False, primary_key=True)

    # tweet = Column(pg.JSONB, nullable=False)
    label = sa.Column(types.String)
    features = sa.Column(pg.JSONB)

    created_at = sa.Column(types.DateTime, nullable=False, index=True)

    # representative = sa.orm.relationship(
    #     'Tweet',
    #     uselist=False,
    #     secondary=tweet_representative,
    #     primaryjoin=tweet_id == tweet_representative.c.tweet_id,
    #     secondaryjoin=tweet_representative.c.representative_tweet_id == tweet_id,
    # )


indexes = [
    sa.Index(
        'idx_tweet_features_screen_names',
        Tweet.features['screen_names'],
    ),

    sa.Index(
        'idx_tweet_features_user_mentions',
        Tweet.features['user_mentions'],
    ),

    sa.Index(
        'idx_tweet_features_hashtags',
        Tweet.features['hashtags'],
    ),

    sa.Index(
        'idx_tweet_features_languages',
        Tweet.features['languages'],
    ),

    sa.Index(
        'idx_tweet_features_filter_simhash',
        Tweet.features['filter', 'simhash'],
    ),

    sa.Index(
        'idx_tweet_features_filter_is_retweet',
        Tweet.features['filter', 'is_retweet'],
    ),
]


relation = sa.Table(
    'relation', metadata,
    sa.Column('tweet_id', sa.BigInteger, primary_key=True),
    sa.Column('collection', sa.String, primary_key=True, index=True),
    sa.Column('relation', sa.String, primary_key=True, index=True),
    sa.Column('head_tweet_id', sa.BigInteger),
)
