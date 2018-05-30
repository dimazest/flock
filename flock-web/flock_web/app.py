import os
import json
import re

import sqlalchemy as sa
from celery import Celery

from flask import Flask, request, url_for, g

from flask_sqlalchemy import SQLAlchemy, get_debug_queries, BaseQuery
from flask_iniconfig import INIConfig
from flask_humanize import Humanize
from flask_debugtoolbar import DebugToolbarExtension
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect

from werkzeug.datastructures import MultiDict

from flock.model import metadata
import flock_web.model as fw_model


from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import Select
from sqlalchemy.orm.query import _generative


@compiles(Select)
def compile(element, compiler, **kw):
    s = compiler.visit_select(element, **kw)
    if hasattr(element, '_apply_no_load_balance_comment'):
        s = re.sub(r'^SELECT ', '/*NO LOAD BALANCE*/ SELECT ', s)
    return s


class PrefixedQuery(BaseQuery):
    _apply_no_load_balance_comment = True

    @_generative()
    def without_no_load_balance_comment(self):
        self._apply_no_load_balance_comment = False

    def _compile_context(self, *arg, **kw):
        context = BaseQuery._compile_context(self, *arg, **kw)
        if self._apply_no_load_balance_comment:
            context.statement._apply_no_load_balance_comment = True
        return context


db = SQLAlchemy(metadata=metadata, query_class=PrefixedQuery)
ini_config = INIConfig()
humanise = Humanize()
toolbar = DebugToolbarExtension()
lm = LoginManager()
csrf = CSRFProtect()


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

    other_args = {}
    for k, v in single_args.items():
        if k in ('collection', 'task_id'):
            other_args[k] = v
        else:
            args[k] = v

    return url_for(
        endpoint,
        **other_args,
        **args
    )


def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL'],
    )
    celery.conf.update(app.config)
    TaskBase = celery.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery


@lm.user_loader
def user_loader(user_id):
    return db.session.query(fw_model.User).get(user_id)


def create_app(config_file, return_celery=False):
    app = Flask(__name__.split('.')[0])

    ini_config.init_app(app)
    app.config.from_inifile(config_file)

    if not app.config.get('SECRET_KEY'):
        if not app.config.get('DEBUG'):
            app.config['SECRET_KEY'] = os.urandom(24)
        else:
            app.config['SECRET_KEY'] = '__DEBUG__'

    app.config['WTF_CSRF_TIME_LIMIT'] = int(app.config['WTF_CSRF_TIME_LIMIT'])

    db.init_app(app)
    sa.orm.configure_mappers()
    humanise.init_app(app)
    csrf.init_app(app)
    lm.init_app(app)

    toolbar.init_app(app)

    from .blueprints.main import bp_main
    app.register_blueprint(bp_main)

    from .blueprints.collection import bp_collection
    app.register_blueprint(bp_collection)

    app.jinja_env.globals['url_for_other_page'] = url_for_other_page
    app.jinja_env.globals['restricted_url'] = restricted_url

    celery = make_celery(app)

    app.config['COLLECTIONS'] = app.config['COLLECTIONS'].split()

    @app.before_request
    def link_celery():
        from flask import g
        g.celery = celery

    @app.before_request
    def track_user():
        if not current_user.is_authenticated or not request.endpoint or request.endpoint.startswith(
                (
                    '_debug_toolbar', 'collection.task_result', 'static', 'main.user',
                    'collection.cluster_status',
                )
        ):
            return

        request_form = dict(request.form.lists())

        if request.endpoint == 'main.relevance':
            data = request.get_json()
            if 'selection_args' in data:
                request_form['selection_args'] = data['selection_args']

        if 'csrf_token' in request_form:
            del request_form['csrf_token']

        action = fw_model.UserAction(
            user=current_user,
            url=request.url,
            endpoint=request.endpoint,
            view_args=request.view_args,
            collection=getattr(g, 'collection', None),
            request_args=dict(request.args.lists()),
            request_form=request_form,
            headers={
                'Referer': request.headers['Referer']
            } if 'Referer' in request.headers else {},
        )

        db.session.add(action)
        db.session.commit()

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

    lm.login_view = 'main.login'

    if not return_celery:
        return app
    else:
        return app, celery
