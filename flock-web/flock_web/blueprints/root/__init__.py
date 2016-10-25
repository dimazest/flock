from flask import render_template, Blueprint, request, redirect, url_for, g

from sqlalchemy import func, select, Table, Column, Integer, String, and_, sql
from sqlalchemy.sql.expression import text, and_
from paginate_sqlalchemy import SqlalchemySelectPage, SqlalchemyOrmPage

import crosstab

from flock import model
from flock_web.app import db, url_for_other_page


bp_root = Blueprint(
    'root', __name__,
    static_folder='static',
    template_folder='templates',
    url_prefix='/<collection>'
    )


@bp_root.url_defaults
def add_collection(endpoint, values):
    values.setdefault('collection', getattr(g, 'collection', None))


@bp_root.url_value_preprocessor
def pull_collection(endpoint, values):
    g.collection = values.pop('collection')


@bp_root.route('/')
def index():
    return redirect(url_for('.tweets'))


def feature_query_args():
    feature_query = request.args.copy()
    return feature_query


@bp_root.route('/tweets')
def tweets():
    page_num = int(request.args.get('_page', 1))
    items_per_page = int(request.args.get('_items_per_page', 20))

    feature_query = feature_query_args()

    tweets = (
        db.session.query(model.Tweet)
        .filter(model.Tweet.collection == g.collection)
        .filter(*(model.Tweet.features.contains({k: [v]}) for k, v in feature_query.items() if not k.startswith('_')))
        .order_by(model.Tweet.created_at, model.Tweet.tweet_id)
    )

    page = SqlalchemyOrmPage(
        tweets,
        page=page_num, items_per_page=items_per_page,
        url_maker=url_for_other_page,
    )

    return render_template(
        'root/tweets.html',
        page=page,
    )


@bp_root.route('/tweets/<feature_name>')
def features(feature_name):
    other_feature = request.args.get('_other', None)
    unstack = request.args.get('_unstack', None) if other_feature is not None else None
    other_feature_values = None

    page_num = int(request.args.get('_page', 1))
    items_per_page = int(request.args.get('_items_per_page', 20))

    feature_query = feature_query_args()

    features_to_filter = [model.Tweet.features.contains({k: [v]}) for k, v in feature_query.items() if not k.startswith('_')]
    feature_select = (
        select(['feature', func.count()])
        .select_from(
            text(
                ('tweet, ' if not features_to_filter else '') +
                'jsonb_array_elements_text(tweet.features->:feature) as feature'
            ).bindparams(feature=feature_name)
        )
        .where(
            and_(
                sql.literal_column('collection') == g.collection,
                *features_to_filter,
            )
        )
        .group_by('feature')
        .order_by(func.count().desc())
    )

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
