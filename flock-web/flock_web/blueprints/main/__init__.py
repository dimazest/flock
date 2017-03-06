import json
from urllib.parse import urlparse, urljoin

from flask import render_template, Blueprint, redirect, url_for, flash, session, abort, request
import flask_login

from sqlalchemy import func
from flock import model

from flock_web.app import db
from flock_web import model as fw_model


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

    next = wtf.HiddenField('Next', [validators.Optional()])

    def __init__(self, *args, **kwargs):
        FlaskForm.__init__(self, *args, **kwargs)
        self.user = None

    def validate(self):
        rv = FlaskForm.validate(self)
        if not rv:
            return False

        if not is_safe_url(self.next.data):
            return False

        user = db.session.query(User).filter_by(first_name=self.first_name.data, last_name=self.last_name.data).one_or_none()
        if user is None:
            flash('''Such user doesn't exist''', 'danger')
            return False

        self.user = user
        return True


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


@bp_main.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(next=request.args.get('next'))

    if form.validate_on_submit():
        session['user_id'] = form.user.id
        return redirect(form.next.data or url_for('.welcome'))

    return render_template('main/login.html', form=form)


@bp_main.route('/logout')
@flask_login.login_required
def logout():
    flask_login.logout_user()
    return redirect(url_for('.login'))


@bp_main.route('/topics')
@flask_login.login_required
def topics():
    topics = db.session.query(fw_model.Topic).filter_by(user=flask_login.current_user)
    return render_template(
        'main/topics.html',
        topics=topics,
    )


class TopicForm(FlaskForm):
    title = wtf.StringField('Title', [validators.Required()])
    description = wtf.TextAreaField('Description')
    narrative = wtf.TextAreaField('Narrative')

    topic_id = wtf.HiddenField()


@bp_main.route('/topic', methods=['POST'], endpoint='topic_post')
@bp_main.route('/topic/<topic_id>', endpoint='topic_with_id')
@flask_login.login_required
def topic(topic_id=None):
    if request.method == 'POST':

        topic_id = request.form.get('topic_id', type=int)

        if topic_id > 0:
            topic = db.session.query(fw_model.Topic).get(topic_id)
            assert topic.user == flask_login.current_user

            form = TopicForm()
            if form.validate_on_submit():
                form.populate_obj(topic)

                flash('A topic is updated.', 'success')

        else:

            selection_args = json.loads(request.form['selection_args'])

            if topic_id < 0:
                # New topic is requested
                topic = fw_model.Topic(title=selection_args['query'])
                topic.user = flask_login.current_user

                flash('A new topic is created.', 'success')

            else:
                topic = db.session.query(fw_model.Topic).get(topic_id)
                assert topic.user == flask_login.current_user

            query = fw_model.TopicQuery(**selection_args)

            topic.queries.append(query)

            db.session.add(query)

        db.session.commit()

        return redirect(url_for('.topic_with_id', topic_id=topic.id))



    from flask import jsonify

    topic = db.session.query(fw_model.Topic).get(topic_id)
    assert topic.user == flask_login.current_user

    form = TopicForm(
        title=topic.title,
        description=topic.description,
        narrative=topic.narrative,
        topic_id=topic.id,
    )

    return render_template(
        'main/topic.html',
        form=form,
    )

