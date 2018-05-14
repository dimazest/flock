import sqlalchemy as sa
from sqlalchemy.sql.expression import text, and_, or_, not_, join, column, select, func
from sqlalchemy_searchable import search, search_manager

from flock import model
from .app import db


def build_feature_filter(filter_args):
    feature_filter_args = []

    positive_include = [(k, [v for v in vs if not v.startswith('-')]) for k, vs, in filter_args]
    positive_include = [(k, v) for k, vs in positive_include if vs for v in vs]
    if positive_include:
        feature_filter_args.append(or_(*(model.Tweet.features[k].has_key(v) for k, v in positive_include)))

    negative_include = [(k, [v[1:] for v in vs if v.startswith('-')]) for k, vs, in filter_args]
    negative_include = [(k, v) for k, vs in negative_include if vs for v in vs]
    if negative_include:
        feature_filter_args.append(and_(*(not_(model.Tweet.features[k].has_key(v)) for k, v in negative_include)))

    return feature_filter_args


def build_tweet_query(collection, query, filter_args, possibly_limit=True, story=None, cluster=None, clustered_selection_id=None, count=False):
    feature_filter_args = build_feature_filter(filter_args)

    tweets = db.session.query(model.Tweet).without_no_load_balance_comment()

    tweets = (
        tweets
        .filter(model.Tweet.collection == collection)
        .filter(*feature_filter_args)
        # .filter(model.Tweet.features['filter', 'is_retweet'].astext == 'false')
        # .filter(model.Tweet.representative == None)
    )

    if query:
        tweets = search(tweets, query, sort=not count)

    if story is not None:
        ts = model.tweet_story.alias()
        tweets = (
            tweets
            .join(ts)
            .order_by(None).order_by(ts.c.rank)
        )
    elif cluster is not None:
        assert clustered_selection_id

        tweets = (
            tweets
            .join(model.tweet_cluster)
            .filter(
                model.tweet_cluster.c.label == cluster,
                model.tweet_cluster.c._clustered_selection_id == clustered_selection_id,
            )
        )

    if count:
        return db.session.scalar(tweets.selectable.with_only_columns([func.count()]))

    tweets = tweets.order_by(model.Tweet.created_at, model.Tweet.tweet_id)

    # if possibly_limit and story is None:
    #     tweets = tweets.limit(100)

    return tweets


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
    ).without_no_load_balance_comment()


def stats_for_feature_query(feature_name, query, collection, clustered_selection_id, cluster, filter_args):
    feature_filter_args = build_feature_filter(filter_args)

    extracted_features = {
        'screen_names': (model.screen_names, 'screen_name'),
        'hashtags': (model.hashtags, 'hashtag'),
        'user_mentions': (model.user_mentions, 'user_mention'),
    }

    if feature_filter_args or query:

        if feature_name in extracted_features:
            table, feature_column = extracted_features[feature_name]
            feature = select([table.c.collection, table.c.tweet_id, table.c[feature_column].label('feature_value')]).alias()
        else:
            feature = text(
                'select collection, tweet_id, feature_value from tweet, jsonb_array_elements_text(tweet.features->:feature) as feature_value'
            ).columns(column('collection'), column('tweet_id'), column('feature_value')).bindparams(feature=feature_name).alias()

        feature = (
            select([feature.c.feature_value, func.count().label('count')])
            .where(
                and_(
                    feature.c.collection == collection,
                    feature.c.collection == model.Tweet.collection,
                    feature.c.tweet_id == model.Tweet.tweet_id,
                    model.Tweet.features['filter', 'is_retweet'].astext == 'false',
                    (
                         model.Tweet.search_vector.op('@@')(sa.func.tsq_parse(search_manager.options['regconfig'], query))
                        if query else True
                    ),
                    *(
                        [
                            model.Tweet.tweet_id == model.tweet_cluster.c.tweet_id,
                            model.Tweet.collection == model.tweet_cluster.c.collection,
                            model.tweet_cluster.c._clustered_selection_id == clustered_selection_id,
                            model.tweet_cluster.c.label == cluster,
                        ]
                        if cluster else []
                    ),
                    *feature_filter_args
                )
            )
            .group_by(feature.c.feature_value)
        )

        feature = feature.alias()

    else:
        count_table = model.feature_counts

        feature = (
            select([count_table.c.collection, count_table.c.feature_value, count_table.c.count])
            .where(
                and_(
                    count_table.c.feature_name == feature_name,
                    count_table.c.collection == collection,
                )
            )
            .alias()
        )

    s = (
        select([feature.c.feature_value, feature.c.count])
        .select_from(feature)
        .order_by(feature.c.count.desc())
    )

    return s
