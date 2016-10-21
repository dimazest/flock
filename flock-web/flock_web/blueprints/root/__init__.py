from flask import render_template, Blueprint, request, redirect, url_for, g

from flask_sqlalchemy import BaseQuery

from sqlalchemy import func, select, Table, Column, Integer, String
from sqlalchemy.sql.expression import text
from paginate_sqlalchemy import SqlalchemySelectPage

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

    g.tweets_selectable = (
        select([model.Tweet])
        .where(model.Tweet.collection == g.collection)
        .order_by(model.Tweet.created_at, model.Tweet.tweet_id)
    ).alias('t')


@bp_root.route('/')
def index():
    return redirect(url_for('.tweets'))


def get_page(query):
    page = request.args.get('page', None)
    if page is None:
        page = query.paginate().pages
        redirect = True
    else:
        page = int(page)
        redirect = False

    return page, redirect


@bp_root.route('/tweets', defaults={'feature_name': None, 'feature_value': None})
@bp_root.route('/tweets/<feature_name>/<feature_value>')
def tweets(feature_name, feature_value):

    if feature_name is not None:
        g.tweets = (
            g.tweets.from_self()
            .filter(
                model.Tweet.features[feature_name]
                .contains('"{}"'.format(feature_value))
            )
        )

    page, do_redirect = get_page(g.tweets)
    if do_redirect:
        return redirect(url_for_other_page(page))

    return render_template(
        'root/tweets.html',
        pagination=g.tweets.paginate(page=page),
        label_names=g.label_names,
    )



@bp_root.route('/feature/<feature_name>')
def feature(feature_name):
    other_feature = request.args.get('other', None)
    unstack = request.args.get('unstack', None) if other_feature is not None else None
    other_feature_values = None

    page_num = request.args.get('page', 1)
    items_per_page = request.args.get('items_per_page', 4)

    feature_select = (
        select([g.tweets_selectable.columns['tweet_id'], 'feature'])
        .select_from(
            text('jsonb_array_elements(t.features->:feature) as feature').bindparams(feature=feature_name)
        )
    ).alias()

    feature_counts_select = (
        select(
            [feature_select.columns['feature'], func.count().label('total')]
        )
        .select_from(feature_select)
        .group_by(feature_select.columns['feature'])
        .order_by(func.count().desc())
    )

    #page = SqlalchemySelectPage(db.session, feature_counts_select.alias(), page=page_num, items_per_page=items_per_page, url_maker=url_for_other_page)

    if other_feature is not None:
        feature_select = (
            select([g.tweets_selectable.columns['tweet_id'], 'feature', 'other_feature'])
            .select_from(
                text(
                    'jsonb_array_elements_text(t.features->:feature) as feature,'
                    'jsonb_array_elements_text(t.features->:other_feature) as other_feature'
                ).bindparams(feature=feature_name, other_feature=other_feature)
            )
            .alias()
        )
        _ = feature_counts_select.alias()
        feature_counts_select = (
            select(
                [feature_select.columns['feature'], feature_select.columns['other_feature'], func.count().label('total')]
            )
            .select_from(feature_select)
            .where(
                feature_select.columns['feature'].in_(
                    select([_.columns['feature']])
                    .offset((page_num - 1) * items_per_page)
                    .limit(items_per_page)
                )
            )
            .group_by(feature_select.columns['feature'], feature_select.columns['other_feature'])
            .order_by(func.count().desc())
        )


    # if unstack:
    #     other_feature_values_select = (
    #         select(
    #             [feature_select.columns['other_feature'].distinct()]
    #         )
    #         .order_by(feature_select.columns['other_feature'])
    #     )
    #     other_feature_values = [v for v, in db.session.execute(other_feature_values_select)]

    #     ret_types = Table(
    #         '__t'.format(g.collection, feature_name, other_feature).replace('.', '__').replace('-', '__'), model.metadata,
    #         Column('feature', String),
    #         extend_existing=True,
    #         *[Column(v, Integer) for v in other_feature_values]
    #     )

    #     row_total = crosstab.row_total(
    #         [ret_types.c[v] for v in other_feature_values]
    #     ).label('total')

    #     feature_counts_select = (
    #         select(
    #             [
    #                 '*', row_total,
    #             ]
    #         )
    #         .select_from(
    #             crosstab.crosstab(
    #                 feature_counts_select,
    #                 ret_types,
    #                 categories=other_feature_values_select,
    #             )
    #         )
    #         .order_by(
    #             row_total.desc(),
    #             ret_types.c.feature,
    #         )
    #     )

    return render_template(
        'root/feature.html',
        feature_name=feature_name,
        other_feature_name=other_feature,
        # other_feature_values=other_feature_values,
        #page=page,
        items=db.session.execute(feature_counts_select)
    )


@bp_root.route('/tweets/<feature_name>')
def feature_info(feature_name):
    feature = jsonb_array_elements_text(
        g.tweets_selectable.columns['tweet_features'][feature_name]
    ).alias('feature')

    crosstab_input = (
        db.session.query(
            feature.c.value, g.tweets_selectable.columns['tweet_label'], func.count()
        )
        .select_from(g.tweets_selectable, feature)
        .group_by(feature, g.tweets_selectable.columns['tweet_label'])
    ).selectable

    ret_types = Table(
        'ct_{}'.format(g.collection.replace('.', '__').replace('-', '__')), model.metadata,
        Column('feature_value', String),
        extend_existing=True,
        *[Column(c, Integer) for c in g.label_names]
    )

    row_total = crosstab.row_total(
        [ret_types.c[c] for c in g.label_names]
    ).label('total')

    q = (
        select(
            [
                '*', row_total,
            ]
        )
        .select_from(
            crosstab.crosstab(
                crosstab_input,
                ret_types,
                categories=g.labels.selectable,
            )
        )
        .order_by(
            row_total.desc(),
            ret_types.c.feature_value
        )
    )

    return render_template(
        'root/statistics.html',
        result=db.session.execute(q),
        feature_name=feature_name,
        category_labels=g.label_names,
    )
