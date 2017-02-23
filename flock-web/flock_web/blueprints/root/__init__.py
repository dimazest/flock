from flask import render_template, Blueprint, request, redirect, url_for, g

from sqlalchemy import func, select, Table, Column, Integer, String, sql
from sqlalchemy.sql.expression import text, and_, or_, not_, join, column
from paginate_sqlalchemy import SqlalchemySelectPage, SqlalchemyOrmPage
from sqlalchemy_searchable import search, parse_search_query

import crosstab

from flock import model
from flock_web.app import db, url_for_other_page


bp_root = Blueprint(
    'root', __name__,
    static_folder='static',
    template_folder='templates',
    url_prefix='/<collection>'
    )


def stats_for_feature(feature_name, feature_filter_args=()):
    if feature_filter_args or g.query:
        feature = text(
            'select collection, tweet_id, feature_value from tweet, jsonb_array_elements_text(tweet.features->:feature) as feature_value'
        ).columns(column('collection'), column('tweet_id'), column('feature_value')).bindparams(feature=feature_name).alias()

        feature = (
            select([feature.c.feature_value, func.count().label('count')])
            .where(
                and_(
                    feature.c.collection == g.collection,
                    feature.c.collection == model.Tweet.collection,
                    feature.c.tweet_id == model.Tweet.tweet_id,
                    (
                        text(
                            "tweet.search_vector @@ to_tsquery('pg_catalog.english', :search_vector)"
                        ).bindparams(search_vector=parse_search_query(g.query))
                        if g.query else True
                    ),
                    *(
                        [
                            model.Tweet.tweet_id == model.filtered_tweets.c.tweet_id,
                            model.Tweet.collection == model.filtered_tweets.c.collection,
                        ]
                        if g.filter != 'none' else []
                    ),
                    *feature_filter_args
                )
            )
            .group_by(feature.c.feature_value)
            .alias()
        )

        feature = feature.alias()

    else:
        if g.filter == 'none':
            count_table = model.feature_counts
        else:
            count_table = model.feature_scores

        feature = (
            select([count_table.c.collection, count_table.c.feature_value, count_table.c.count])
            .where(
                and_(
                    count_table.c.feature_name == feature_name,
                    count_table.c.collection == g.collection,
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


@bp_root.url_defaults
def add_collection(endpoint, values):
    values.setdefault('collection', getattr(g, 'collection', None))


@bp_root.url_value_preprocessor
def pull_collection(endpoint, values):
    g.collection = values.pop('collection')

    g.query = request.args.get('q')
    g.filter = request.args.get('filter', 'pmi')
    g.show_images = request.args.get('show_images') == 'on'

    filter_args = [(k, vs) for k, vs in request.args.lists() if not k.startswith('_') and k not in ( 'story', 'q', 'filter', 'show_images')]

    g.feature_filter_args = []

    positive_include = [(k, [v for v in vs if not v.startswith('-')]) for k, vs, in filter_args]
    positive_include = [(k, v) for k, vs in positive_include if vs for v in vs]
    if positive_include:
        g.feature_filter_args.append(or_(*(model.Tweet.features.contains({k: [v]}) for k, v in positive_include)))

    negative_include = [(k, [v[1:] for v in vs if v.startswith('-')]) for k, vs, in filter_args]
    negative_include = [(k, v) for k, vs in negative_include if vs for v in vs]

    if negative_include:
        g.feature_filter_args.append(and_(*(not_(model.Tweet.features.contains({k: [v]})) for k, v in negative_include)))

    _story_id = request.args.get('story', type=int)
    g.story = None
    if _story_id is not None:
        g.story = db.session.query(model.Story).get(int(_story_id))
        g.feature_filter_args.append(model.Tweet.stories.contains(g.story))


@bp_root.route('/')
def index():
    return redirect(url_for('.tweets'))


@bp_root.route('/tweets')
def tweets():
    page_num = request.args.get('_page', 1, type=int)
    items_per_page = request.args.get('_items_per_page', 100, type=int)

    tweets = db.session.query(model.Tweet)

    if g.filter == 'none':
        tweets = (
            tweets
            .filter(model.Tweet.collection == g.collection)
        )
    else:
        tweets = (
            tweets
            .select_from(model.filtered_tweets)
            .join(model.Tweet)
            .filter(model.Tweet.collection == g.collection)
            .filter(model.filtered_tweets.c.collection == g.collection)
        )

    tweets = (
        tweets
        .filter(*g.feature_filter_args)
        # # .filter(model.Tweet.features['filter', 'is_retweet'].astext == 'false' )
        # # .filter(model.Tweet.representative == None)
    )

    if g.query:
        tweets = search(tweets, g.query)

    if g.query or g.feature_filter_args:
        tweet_count = tweets.count()

        tweets = tweets.order_by(model.Tweet.created_at, model.Tweet.tweet_id)
    else:
        tweet_count = None

    if not g.story:
        tweets = tweets.limit(100)
    else:
        ts = model.tweet_story.alias()
        tweets = (
            tweets
            .join(ts)
            .order_by(None)
            .order_by(ts.c.rank)
        )

    stories = (
        db.session.query(model.Story)
        .filter(model.Story.collection == g.collection)
        .all()
    )

    # page = SqlalchemyOrmPage(
    #     tweets,
    #     page=page_num,
    #     items_per_page=items_per_page,
    #     url_maker=url_for_other_page,
    # )

    return render_template(
        'root/tweets.html',
        tweets=tweets.all(),
        tweet_count=tweet_count,
        # page=page,
        stories=stories,
        selected_story=g.story,
        stats=[
            (f, db.session.query(stats_for_feature(f, g.feature_filter_args).limit(12).alias()), request.args.getlist(f))
            for f in ['screen_names', 'hashtags', 'user_mentions']
        ],
        query=g.query,
        query_form_hidden_fields=((k, v) for k, v in request.args.items(multi=True) if not k.startswith('_') and k != 'q'),
        filter_form_hidden_fields=((k, v) for k, v in request.args.items(multi=True) if not k.startswith('_') and k not in ('filter', 'show_images')),
        selected_filter=g.filter,
        collection=g.collection,
        show_images=g.show_images,
    )


@bp_root.route('/tweets/<feature_name>')
def features(feature_name):
    other_feature = request.args.get('_other', None)
    unstack = request.args.get('_unstack', None) if other_feature is not None else None
    other_feature_values = None

    page_num = int(request.args.get('_page', 1))
    items_per_page = int(request.args.get('_items_per_page', 100))

    feature_select = stats_for_feature(feature_name, g.feature_filter_args)

    page = SqlalchemySelectPage(
        db.session, feature_select,
        page=page_num, items_per_page=items_per_page,
        url_maker=url_for_other_page,
    )
    items = page.items

    if other_feature is not None:
        feature_column = sql.literal_column('feature', String)
        other_feature_column = sql.literal_column('other_feature', String)
        stmt = (
            select(
                [feature_column, other_feature_column, func.count()]
            )
            .select_from(
                text(
                    'tweet, '
                    'jsonb_array_elements_text(tweet.features->:feature) as feature, '
                    'jsonb_array_elements_text(tweet.features->:other_feature) as other_feature'
                ).bindparams(feature=feature_name, other_feature=other_feature)
            ).where(
                and_(
                    sql.literal_column('collection') == g.collection,
                    feature_column.in_(
                        feature_select
                        .with_only_columns(['feature'])
                        .offset((page_num - 1) * items_per_page)
                        .limit(items_per_page)
                    )
                )
            )
            .group_by(feature_column, other_feature_column)
        )

        items = db.session.execute(stmt.order_by(func.count().desc()))

    if unstack:
        other_feature_values_select = (
            select([other_feature_column.distinct()])
            .select_from(stmt.alias())
        )
        other_feature_values = [
            v for v, in
            db.session.execute(other_feature_values_select.order_by(other_feature_column))
        ]

        from sqlalchemy import MetaData
        ret_types = Table(
            '_t_', MetaData(),
            Column('feature', String),
            extend_existing=True,
            *[Column(v, Integer) for v in other_feature_values]
        )

        row_total = crosstab.row_total(
            [ret_types.c[v] for v in other_feature_values]
        ).label('total')

        stmt = (
            select(
                [
                    '*', row_total,
                ]
            )
            .select_from(
                crosstab.crosstab(
                    stmt,
                    ret_types,
                    categories=other_feature_values_select,
                )
            )
            .order_by(
                row_total.desc(),
                ret_types.c.feature,
            )
        )

        items = db.session.execute(stmt)

    return render_template(
        'root/features.html',
        feature_name=feature_name,
        other_feature_name=other_feature,
        other_feature_values=other_feature_values,
        page=page,
        items=items,
    )
