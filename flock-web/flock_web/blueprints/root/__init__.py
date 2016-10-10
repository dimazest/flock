from flask import render_template, Blueprint, request

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
    )


@bp_root.route('/')
@register_menu(bp_root, '.', 'Home', order=0)
def index():
    return render_template('root/index.html')


def get_page(query):
    page = request.args.get('page', None)
    if page is None:
        page = query.paginate().pages
    else:
        page = int(page)

    return page


@bp_root.route('/tweets')
@register_menu(bp_root, 'tweets', 'Tweets', order=1)
def tweets():
    tweets = BaseQuery(model.Tweet, db.session()).order_by(model.Tweet.created_at, model.Tweet.id)

    page = get_page(tweets)

    return render_template(
        'root/tweets.html',
        tweets=tweets,
        pagination=tweets.paginate(page=page),
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
        .order_by(model.Tweet.created_at, model.Tweet.id)
    )

    page = get_page(tweets)

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
        .order_by(model.Tweet.created_at, model.Tweet.id)
    )

    page = get_page(tweets)

    return render_template(
        'root/tweets.html',
        tweets=tweets,
        pagination=tweets.paginate(page=page),
        endpoint='.feature_screen_names',
        endpoint_kwargs={'label': label},
        json=json,
    )
