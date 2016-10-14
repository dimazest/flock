from flask import render_template, Blueprint

from sqlalchemy import func
from flock import model

from flock_web.app import db


bp_main = Blueprint(
    'main',
    __name__,
    template_folder='templates',
    )


@bp_main.route('/')
def welcome():

    size = func.count()
    collections = db.session.query(
        model.Tweet.collection,
        size,
    ).group_by(model.Tweet.collection).order_by(size.desc())

    return render_template(
        'main/welcome.html',
        collections=collections,
    )
