from sqlalchemy.sql.expression import text, and_, or_, not_, join, column, select, func
from sqlalchemy_searchable import search

from flock import model
from .app import db


def build_tweet_query(collection, query, filter, filter_args, possibly_limit=True, story=None, cluster=None, clustered_selection=None):

    feature_filter_args = []

    positive_include = [(k, [v for v in vs if not v.startswith('-')]) for k, vs, in filter_args]
    positive_include = [(k, v) for k, vs in positive_include if vs for v in vs]
    if positive_include:
        feature_filter_args.append(or_(*(model.Tweet.features.contains({k: [v]}) for k, v in positive_include)))

    negative_include = [(k, [v[1:] for v in vs if v.startswith('-')]) for k, vs, in filter_args]
    negative_include = [(k, v) for k, vs in negative_include if vs for v in vs]
    if negative_include:
        feature_filter_args.append(and_(*(not_(model.Tweet.features.contains({k: [v]})) for k, v in negative_include)))

    tweets = db.session.query(model.Tweet)

    if filter == 'none':
        tweets = (
            tweets
            .filter(model.Tweet.collection == collection)
        )
    else:
        tweets = (
            tweets
            .select_from(model.filtered_tweets)
            .join(model.Tweet)
            .filter(model.Tweet.collection == collection)
            .filter(model.filtered_tweets.c.collection == collection)
        )

    tweets = (
        tweets
        .filter(*feature_filter_args)
        # # .filter(model.Tweet.features['filter', 'is_retweet'].astext == 'false' )
        # # .filter(model.Tweet.representative == None)
    )

    if query:
        tweets = search(tweets, query)

    if story is not None:
        ts = model.tweet_story.alias()
        tweets = (
            tweets
            .join(ts)
            .order_by(None).order_by(ts.c.rank)
        )
    elif cluster is not None:
        assert clustered_selection

        tweets = (
            tweets
            .join(model.tweet_cluster)
            .filter(
                model.tweet_cluster.c.label == cluster,
                model.tweet_cluster.c._clustered_selection_id == clustered_selection._id,
            )
        )

    if query or feature_filter_args:
        tweet_count = tweets.count()

        tweets = tweets.order_by(model.Tweet.created_at, model.Tweet.tweet_id)
    else:
        tweet_count = None

    if possibly_limit and story is None:
        tweets = tweets.limit(100)

    return tweets, tweet_count, feature_filter_args


def build_cluster_query(clustered_selection_id):
    return (
        db.session.query(
            select([model.tweet_cluster.c.label, func.count()])
            .select_from(model.tweet_cluster)
            .where(model.tweet_cluster.c._clustered_selection_id==clustered_selection_id)
            .group_by(model.tweet_cluster.c.label)
            .order_by(model.tweet_cluster.c.label)
            .alias()
        )
    )
