from flask import render_template, Blueprint, redirect, url_for, flash, session
import flask_login

from sqlalchemy import func
from flock import model

from flock_web.app import db


bp_main = Blueprint(
    'main',
    __name__,
    template_folder='templates',
    )


@bp_main.route('/')
@flask_login.login_required
def welcome():

    size = func.count()
    collections = db.session.query(
        model.Tweet.collection,
        size,
        # func.min(model.Tweet.created_at),
        # func.max(model.Tweet.created_at),
    ).group_by(model.Tweet.collection).order_by(size.desc())


    return render_template(
        'main/welcome.html',
        collections=collections,
    )

from flask_wtf import FlaskForm
import wtforms as wtf
from wtforms import validators
from flock_web.model import User


class LoginForm(FlaskForm):
    first_name = wtf.StringField('First name', [validators.Required()])
    last_name = wtf.StringField('Last name', [validators.Required()])

    def __init__(self, *args, **kwargs):
        FlaskForm.__init__(self, *args, **kwargs)
        self.user = None

    def validate(self):
        rv = FlaskForm.validate(self)
        if not rv:
            return False

        user = db.session.query(User).filter_by(first_name=self.first_name.data, last_name=self.last_name.data).one_or_none()
        if user is None:
            self.first_name.errors.append('Unknown user')
            return False

        self.user = user
        return True


@bp_main.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        flash('Logged in successfully.')

        session['user_id'] = form.user.id
        return redirect(url_for('.welcome'))

    return render_template('main/login.html', form=form)


@bp_main.route('/logout')
@flask_login.login_required
def logout():
    flask_login.logout_user()
    return redirect(url_for('.login'))
