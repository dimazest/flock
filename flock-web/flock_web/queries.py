from sqlalchemy.sql.expression import text, and_, or_, not_, join, column
from sqlalchemy_searchable import search

from flock import model
from .app import db


def build_tweet_query(collection, query, filter, filter_args, possibly_limit=True):

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

    if query or feature_filter_args:
        tweet_count = tweets.count()

        tweets = tweets.order_by(model.Tweet.created_at, model.Tweet.tweet_id)
    else:
        tweet_count = None

    if possibly_limit:
        tweets = tweets.limit(100)
        # if not g.story:  # XXX refactor stories
        #     tweets = tweets.limit(100)
        # else:
        #     ts = model.tweet_story.alias()
        #     tweets = (
        #         tweets
        #         .join(ts)
        #         .order_by(None).order_by(ts.c.rank)
        #     )


    return tweets, tweet_count, feature_filter_args
