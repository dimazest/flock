from flask import render_template, Blueprint, send_from_directory, request

from sqlalchemy import func
from flock import model

from flock_web.app import db


bp_main = Blueprint(
    'main',
    __name__,
    template_folder='templates',
    static_folder='static',
    )


@bp_main.route('/')
def welcome():

    size = func.count()
    collections = db.session.query(
        model.Tweet.collection,
        size,
        func.min(model.Tweet.created_at),
        func.max(model.Tweet.created_at),
    ).group_by(model.Tweet.collection).order_by(size.desc())

    return render_template(
        'main/welcome.html',
        collections=collections,
    )


@bp_main.route('/robots.txt')
def static_from_root():
    return send_from_directory(bp_main.static_folder, request.path[1:])
