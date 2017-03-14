import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from sqlalchemy.ext.declarative import declarative_base
import sqlalchemy_searchable

from sqlalchemy_utils.types import TSVectorType

metadata = sa.MetaData()
Base = declarative_base(metadata=metadata)


sqlalchemy_searchable.make_searchable()


tweet_representative = sa.Table(
    'tweet_representative', metadata,
    sa.Column('tweet_id', sa.BigInteger),
    sa.Column('collection', sa.String),
    sa.Column('representative_tweet_id', sa.BigInteger, sa.ForeignKey('tweet.tweet_id')),
    sa.ForeignKeyConstraint(
        ('tweet_id', 'collection'), ('tweet.tweet_id', 'tweet.collection')
    ),
)


filtered_tweets = sa.Table(
    'filtered_tweets', metadata,
    sa.Column('tweet_id', sa.BigInteger),
    sa.Column('collection', sa.String),
    sa.ForeignKeyConstraint(
        ('tweet_id', 'collection'), ('tweet.tweet_id', 'tweet.collection')
    ),
)


feature_counts = sa.Table(
    'feature_counts', metadata,
    sa.Column('collection', sa.String),
    sa.Column('feature_name', sa.String),
    sa.Column('feature_value', sa.String),
    sa.Column('count', sa.Integer),
)

feature_scores = sa.Table(
    'feature_scores', metadata,
    sa.Column('collection', sa.String),
    sa.Column('feature_name', sa.String),
    sa.Column('feature_value', sa.String),
    sa.Column('count', sa.Integer),
    sa.Column('global_count', sa.Integer),
    sa.Column('score', sa.Float),
)


class Tweet(Base):
    __tablename__ = 'tweet'
    __table_args__ = (
        sa.Index('ix_tweet_created_at_tweet_id', 'created_at', 'tweet_id'),
        sa.Index('ix_tweet_features', 'features', postgresql_using='gin'),
        sa.Index('ix_tweet_collection_created_at_tweet_id', 'collection', 'created_at', 'tweet_id'),
    )

    tweet_id = sa.Column(sa.BigInteger, nullable=False, primary_key=True)
    collection = sa.Column(sa.String, nullable=False, primary_key=True, index=True)

    # tweet = Column(pg.JSONB, nullable=False)
    text = sa.Column(sa.UnicodeText)
    search_vector = sa.Column(TSVectorType('text'))

    features = sa.Column(pg.JSONB)

    created_at = sa.Column(sa.DateTime, nullable=False, index=True)

    representative = sa.orm.relationship(
        'Tweet',
        uselist=False,
        secondary=tweet_representative,
        primaryjoin=sa.and_(tweet_id == tweet_representative.c.tweet_id, collection == tweet_representative.c.collection),
        secondaryjoin=sa.and_(tweet_representative.c.representative_tweet_id == tweet_id, tweet_representative.c.collection == collection),
        backref='representees',
    )

    stories = sa.orm.relationship(
        'Story',
        secondary='tweet_story',
        backref='tweets',
    )


class Story(Base):
    __tablename__ ='story'
    __table_args__ = (
        sa.UniqueConstraint('story_id', 'collection'),
    )
    _id = sa.Column(sa.Integer, primary_key=True)

    story_id = sa.Column(sa.String, nullable=False,)
    collection = sa.Column(sa.String, nullable=False)

    title = sa.Column(sa.String, nullable=False)


tweet_story = sa.Table(
    'tweet_story', metadata,
    # XXX: primary key
    sa.Column('tweet_id', sa.BigInteger),
    sa.Column('collection', sa.String),
    sa.Column('_story_id', sa.Integer, sa.ForeignKey('story._id')),
    sa.Column('rank', sa.Integer),
    sa.ForeignKeyConstraint(
        ('tweet_id', 'collection'), ('tweet.tweet_id', 'tweet.collection')
    ),
)


class ClusteredSelection(Base):
    __tablename__ = 'clustered_selection'
    __table_args__ = (
        sa.UniqueConstraint('collection', 'query', 'filter', 'filter_args'),
    )

    _id = sa.Column(sa.Integer, primary_key=True)
    celery_id = sa.Column(sa.String)
    celery_status = sa.Column(sa.String)

    collection = sa.Column(sa.String, nullable=False)
    query = sa.Column(sa.String)
    filter = sa.Column(sa.String)
    filter_args = sa.Column(pg.JSONB)


tweet_cluster = sa.Table(
    'tweet_cluster', metadata,
    sa.Column('_id', sa.Integer, primary_key=True),
    sa.Column('tweet_id', sa.BigInteger),
    sa.Column('collection', sa.String),
    sa.Column('_clustered_selection_id', sa.Integer, sa.ForeignKey('clustered_selection._id')),
    sa.Column('label', sa.String),  # XXX it should be a foreign key to the "cluster" relation that hold the label.
    sa.ForeignKeyConstraint(
        ('tweet_id', 'collection'), ('tweet.tweet_id', 'tweet.collection')
    ),
)


indexes = [
    # sa.Index(
    #     'idx_tweet_features',
    #     Tweet.features,
    #     postgresql_using='gin',
    # ),

#     sa.Index(
#         'idx_tweet_features_screen_names',
#         Tweet.features['screen_names'],
#     ),

#     sa.Index(
#         'idx_tweet_features_user_mentions',
#         Tweet.features['user_mentions'],
#     ),

#     sa.Index(
#         'idx_tweet_features_hashtags',
#         Tweet.features['hashtags'],
#     ),

#     sa.Index(
#         'idx_tweet_features_languages',
#         Tweet.features['languages'],
#     ),

#     sa.Index(
#         'idx_tweet_features_filter_simhash',
#         Tweet.features['filter', 'simhash'],
#     ),

#     sa.Index(
#         'idx_tweet_features_filter_is_retweet',
#         Tweet.features['filter', 'is_retweet'],
#     ),
]


relation = sa.Table(
    'relation', metadata,
    sa.Column('tweet_id', sa.BigInteger, primary_key=True),
    sa.Column('collection', sa.String, primary_key=True, index=True),
    sa.Column('relation', sa.String, primary_key=True, index=True),
    sa.Column('head_tweet_id', sa.BigInteger),
    sa.Index('tweet_id', 'collection'),
)
