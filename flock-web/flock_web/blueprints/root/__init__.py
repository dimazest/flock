from flask import render_template, Blueprint, request, redirect, url_for, g

from flask_sqlalchemy import BaseQuery

from sqlalchemy import func, select, Table, Column, Integer, String
import crosstab

from flock import model
from flock_web.app import db

from . sa_helpers import jsonb_array_elements_text

bp_root = Blueprint(
    'root', __name__,
    static_folder='static',
    template_folder='templates',
    url_prefix='/<collection>'
    )


@bp_root.url_defaults
def add_collection(endpoint, values):
    values.setdefault('collection', g.collection)


@bp_root.url_value_preprocessor
def pull_collection(endpoint, values):
    g.collection = values.pop('collection')

    g.tweets = (
        BaseQuery(model.Tweet, db.session())
        .filter_by(collection=g.collection)
        .order_by(model.Tweet.created_at, model.Tweet.tweet_id)
    )


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
        kwargs = {} if not feature_name else{'feature_name': feature_name, 'filter_value': feature_value}
        return redirect(url_for('.tweets', page=page, **kwargs))

    return render_template(
        'root/tweets.html',
        pagination=g.tweets.paginate(page=page),
        endpoint='.tweets',
        endpoint_kwargs={},
    )


@bp_root.route('/tweets/<filter_key>')
def feature_info(filter_key):
    feature = jsonb_array_elements_text(model.Tweet.features[filter_key]).alias('feature')

    crosstab_input = (
        g.tweets.session.query(
            feature.c.value, model.Tweet.label, func.count()
        )
        .select_from(g.tweets.selectable, feature)

        .group_by(feature, model.Tweet.label)
    ).selectable.where(model.Tweet.label.in_(['lv', 'ru', 'en']))

    categories = (
        g.tweets.session.query(
            func.distinct(model.Tweet.label),
        )
    ).selectable.where(model.Tweet.label.in_(['lv', 'ru', 'en']))

    ret_types = Table(
        'ct', model.metadata,
        Column('label', String),
        Column('en', Integer),
        Column('lv', Integer),
        Column('ru', Integer),
        extend_existing=True,
    )

    row_total = crosstab.row_total(
        [ret_types.c[l] for l in ('en', 'lv', 'ru')]
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
                categories=categories,
            )
        )
        .order_by(row_total.desc(), ret_types.c.label)
    )

    return render_template(
        'root/statistics.html',
        result=db.session.execute(q),
        filter_key=filter_key,
    )
