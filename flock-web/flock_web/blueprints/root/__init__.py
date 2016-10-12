from flask import render_template, Blueprint, request, redirect, url_for, g

from flask import json
from flask_menu import register_menu
from flask_sqlalchemy import BaseQuery

from sqlalchemy import sql

from flock import model
from flock_web.app import db

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
@register_menu(bp_root, '.', 'Home', order=0)
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


@bp_root.route('/tweets', defaults={'filter_key': None, 'filter_value': None})
@bp_root.route('/tweets/<filter_key>/<filter_value>')
@register_menu(bp_root, 'tweets', 'Tweets', order=1)
def tweets(filter_key, filter_value):

    if filter_key is not None:
        g.tweets = g.tweets.from_self().filter(model.Tweet.features[filter_key].contains('"{}"'.format(filter_value)))

    page, do_redirect = get_page(g.tweets)
    if do_redirect:
        kwargs = {} if not filter_key else{'filter_key': filter_key, 'filter_value': filter_value}
        return redirect(url_for('.tweets', page=page, **kwargs))

    return render_template(
        'root/tweets.html',
        pagination=g.tweets.paginate(page=page),
        endpoint='.tweets',
        endpoint_kwargs={},
        json=json,
    )


@bp_root.route('/features/user_mentions')
@register_menu(bp_root, 'user_mentions', 'Mentions', order=3)
def list_feature_user_mentions():
    select = sql.select([model.user_mention_view])
    result = db.session.execute(select)

    return render_template(
        'root/statistics.html',
        result=result,
        details_endpoint='.feature_user_mentions',
        label='user_mention',
    )


@bp_root.route('/features/user_mentions/<label>')
# @register_menu(bp_root, 'user_mentions.details', 'Mention')
def feature_user_mentions(label):
    tweets = (
        BaseQuery(model.Tweet, db.session())
        .filter(model.Tweet.features['user_mentions'].contains('"{}"'.format(label)))
        .order_by(model.Tweet.created_at, model.Tweet.tweet_id)
    )

    page, do_redirect = get_page(tweets)
    if do_redirect:
        return redirect(url_for('.feature_user_mentions', label=label, page=page))

    return render_template(
        'root/tweets.html',
        tweets=tweets,
        pagination=tweets.paginate(page=page),
        endpoint='.feature_user_mentions',
        endpoint_kwargs={'label': label},
        json=json,
    )


@bp_root.route('/features/screen_name')
@register_menu(bp_root, 'screen_name', 'Users', order=2)
def list_feature_screen_namess():
    select = sql.select([model.screen_name_view])
    result = db.session.execute(select)

    return render_template(
        'root/statistics.html',
        result=result,
        details_endpoint='.feature_screen_names',
        label='screen_name',
    )


@bp_root.route('/features/screen_name/<label>')
def feature_screen_names(label):
    tweets = (
        BaseQuery(model.Tweet, db.session())
        .filter(model.Tweet.features['screen_names'].contains('"{}"'.format(label)))
        .order_by(model.Tweet.created_at, model.Tweet.tweet_id)
    )

    page, do_redirect = get_page(tweets)
    if do_redirect:
        return redirect(url_for('.feature_screen_names', label=label, page=page))

    return render_template(
        'root/tweets.html',
        tweets=tweets,
        pagination=tweets.paginate(page=page),
        endpoint='.feature_screen_names',
        endpoint_kwargs={'label': label},
        json=json,
    )
