import os

from flask import Flask, request, url_for

from flask_sqlalchemy import SQLAlchemy
from flask.ext.cache import Cache
from flask.ext.twitter_oembedder import TwitterOEmbedder
from flask.ext.iniconfig import INIConfig
from flask.ext.sqlalchemy import get_debug_queries
from flask_humanize import Humanize
from flask_debugtoolbar import DebugToolbarExtension

from werkzeug.datastructures import MultiDict

from flock.model import metadata


cache = Cache()
db = SQLAlchemy(metadata=metadata)
ini_config = INIConfig()
twitter_oembedder = TwitterOEmbedder()
humanise = Humanize()
toolbar = DebugToolbarExtension()


def url_for_other_page(page):
    return restricted_url(_page=page)


def restricted_url(endpoint=None, include=None, exclude=None, **single_args):
    if endpoint is None:
        endpoint = request.endpoint

    if endpoint == request.endpoint:
        args = MultiDict(request.view_args)
    else:
        args = MultiDict()

    args.update(request.args)

    if endpoint != request.endpoint:
        for arg in list(args.keys()):
            if arg.startswith('_'):
                del args[arg]

    if include:
        args.update(include)

    if exclude:
        for k, to_exclude in exclude.items():
            args.setlist(k, [v for v in args.getlist(k) if v != to_exclude])

    for k, v in single_args.items():
        args.setlist(k, [v])

    return url_for(endpoint, **args)


def create_app(config_file):
    app = Flask(__name__)

    ini_config.init_app(app)
    app.config.from_inifile(config_file)

    cache.init_app(app)
    db.init_app(app)
    twitter_oembedder.init(app, cache, timeout=60*60*24*30)
    humanise.init_app(app)

    app.config['SECRET_KEY'] = os.urandom(24)
    toolbar.init_app(app)

    from .blueprints.main import bp_main
    app.register_blueprint(bp_main)

    from .blueprints.root import bp_root
    app.register_blueprint(bp_root)

    app.jinja_env.globals['url_for_other_page'] = url_for_other_page
    app.jinja_env.globals['restricted_url'] = restricted_url

    @app.after_request
    def after_request(response):
        for query in get_debug_queries():
            if query.duration >= app.config['DATABASE_QUERY_TIMEOUT']:
                app.logger.warning(
                    'SLOW QUERY: %s\n'
                    'Parameters: %s\n'
                    'Duration: %fs\n'
                    'Context: %s\n',
                    query.statement,
                    query.parameters,
                    query.duration,
                    query.context,
                )

        return response

    return app
