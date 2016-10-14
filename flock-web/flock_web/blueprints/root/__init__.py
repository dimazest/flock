from flask import render_template, Blueprint, request, redirect, url_for, g

from flask_sqlalchemy import BaseQuery

from sqlalchemy import func, select, Table, Column, Integer, String
import crosstab

from flock import model
from flock_web.app import db, url_for_other_page

from . sa_helpers import jsonb_array_elements_text

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

    g.tweets = (
        BaseQuery(model.Tweet, db.session())
        .filter_by(collection=g.collection)
        .order_by(model.Tweet.created_at, model.Tweet.tweet_id)
    )
    g.tweets_selectable = g.tweets.selectable.alias()

    g.labels = g.tweets.session.query(
            func.distinct(g.tweets_selectable.columns['tweet_label'])
    ).order_by(g.tweets_selectable.columns['tweet_label'])
    g.label_names = [c for (c, ) in g.labels.all()]


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
        'ct_{}'.format(g.collection), model.metadata,
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
