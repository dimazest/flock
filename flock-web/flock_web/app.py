from flask import Flask

from flask_sqlalchemy import SQLAlchemy
from flask.ext.cache import Cache
from flask.ext.twitter_oembedder import TwitterOEmbedder
from flask.ext.iniconfig import INIConfig
from flask.ext.navigation import Navigation

from flock.model import metadata


cache = Cache()
db = SQLAlchemy(metadata=metadata)
ini_config = INIConfig()
nav = Navigation()
twitter_oembedder = TwitterOEmbedder()

nav.Bar('top', [
    nav.Item('Tweets', '.tweets'),
])

def create_app(config_file):
    app = Flask(__name__)

    ini_config.init_app(app)
    app.config.from_inifile(config_file)

    cache.init_app(app)

    db.init_app(app)
    nav.init_app(app)

    twitter_oembedder.init(app, cache, timeout=60*60*24*30)

    from .blueprints.root import bp_root
    app.register_blueprint(bp_root)

    return app
