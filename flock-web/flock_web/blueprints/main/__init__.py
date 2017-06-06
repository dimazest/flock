import json
import collections
from urllib.parse import urlparse, urljoin

from flask import render_template, Blueprint, redirect, url_for, flash, session, abort, request, render_template_string, jsonify, current_app
import flask_login

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

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

    # # size = func.count()
    # collections = db.session.query(
    #     model.Tweet.collection,
    #     # size,
    #     # func.min(model.Tweet.created_at),
    #     # func.max(model.Tweet.created_at),
    # ).group_by(model.Tweet.collection).order_by(
    #     model.Tweet.collection,
    #     # size.desc()
    # )

    collections = ((c,) for c in current_app.config['COLLECTIONS'])

    return render_template(
        'main/welcome.html',
        collections=collections,
        current_app=current_app,
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


class TopicForm(FlaskForm):
    title = wtf.StringField('Title', [validators.Required()])
    description = wtf.TextAreaField('Description')
    narrative = wtf.TextAreaField('Narrative')

    difficulty = wtf.RadioField(
        'How easy was it to develop this topic?',
        [validators.Optional()],
        choices=[('easy', 'Easy'), ('moderate', 'Moderate'), ('difficult', 'Difficult')],
    )
    familiarity = wtf.RadioField(
        'How familiar are you with the topi?',
        [validators.Optional()],
        choices=[
            ('VIN', 'Familiar, I was checking a specific piece of information.'),
            ('CIN', 'Familiar, but I was interested in gaining new knowledge about the topic.'),
            ('MIN', 'Unfamiliar, the search was in more or less unknown knowledge area.'),
        ],
    )
    inspiration = wtf.StringField('What was the inspiration for this topic?')
    notes = wtf.TextAreaField('General comment.')

    topic_id = wtf.HiddenField()


@bp_main.route('/topics', methods=['POST'], endpoint='topic_post')
@bp_main.route('/topics', methods=['GET'], endpoint='topics')
@bp_main.route('/topics/<topic_id>', endpoint='topic')
@flask_login.login_required
def topic(topic_id=None):
    if request.method == 'POST':

        topic_id = request.form.get('topic_id', type=int)
        selection_args = json.loads(request.form['selection_args']) if 'selection_args' in request.form else None

        new_topic_created = False
        new_query_created = False

        if topic_id is None:
            collection = request.form['return_to_collection']
            query = fw_model.TopicQuery(**selection_args)
            redirect_to = url_for('collection.tweets', collection=collection, q=query.query, filter=query.filter, cluster=query.cluster, **query.filter_args_dict)

            return redirect(redirect_to)

        if topic_id > 0:
            topic = db.session.query(fw_model.Topic).get(topic_id)
            assert topic.user == flask_login.current_user

            form = TopicForm()
            if form.validate_on_submit():
                topic.title = form.title.data
                topic.description = form.description.data
                topic.narrative = form.narrative.data

                if topic.questionnaire is None:
                    topic.questionnaire = fw_model.TopicQuestionnaire()

                topic.questionnaire.answer = {
                    'difficulty': form.difficulty.data,
                    'familiarity': form.familiarity.data,
                    'inspiration': form.inspiration.data,
                    'notes': form.notes.data,
                }

        else:
            # New topic is requested
            topic = fw_model.Topic(title=selection_args['query'])
            topic.user = flask_login.current_user

            new_topic_created = True
            db.session.flush()

        redirect_to = url_for('.topic', topic_id=topic.id)

        if 'selection_args' in request.form:
            query = fw_model.TopicQuery(**selection_args)
            topic.queries.append(query)

            if 'return_to_collection' in request.form:
                collection = request.form['return_to_collection']
                redirect_to = url_for('collection.tweets', topic=topic.id, collection=collection, q=query.query, filter=query.filter, cluster=query.cluster, **query.filter_args_dict)

            new_query_created = True

        db.session.commit()

        if new_topic_created:
            flash(
                render_template_string(
                    '''
                    A new topic <a class="alert-link" href="{{ topic_url }}">"{{topic.title}}"</a> is created.
                    ''',
                    topic=topic,
                    topic_url=url_for('main.topic', topic_id=topic.id)
                ),
                'success',
            )

        elif new_query_created:
            flash(
                render_template_string(
                    '''
                    A new query was assigned to the topic <a class="alert-link" href="{{ topic_url }}">"{{topic.title}}"</a>.
                    ''',
                    topic=topic,
                    topic_url=url_for('main.topic', topic_id=topic.id)
                ),
                'success',
            )

        return redirect(redirect_to)

    if topic_id is None:
            topics = db.session.query(fw_model.Topic).filter_by(user=flask_login.current_user).order_by(fw_model.Topic.id)
            return render_template(
                'main/topics.html',
                topics=topics,
                current_app=current_app,
            )

    topic = db.session.query(fw_model.Topic).get(topic_id)
    assert topic.user == flask_login.current_user

    tweets = db.session.query(model.Tweet).filter(
        model.Tweet.tweet_id.in_(
            sa.select([fw_model.RelevanceJudgment.tweet_id])
            .where(fw_model.RelevanceJudgment.topic_id==topic.id)
            .where(fw_model.RelevanceJudgment.judgment==1)
        )
    ).distinct(model.Tweet.tweet_id).all()

    form = TopicForm(
        title=topic.title,
        description=topic.description,
        narrative=topic.narrative,
        topic_id=topic.id,
        tweets=tweets,

        difficulty=topic.questionnaire.answer.get('difficulty') if topic.questionnaire is not None else None,
        inspiration=topic.questionnaire.answer.get('inspiration')  if topic.questionnaire is not None else None,
        notes=topic.questionnaire.answer.get('notes')  if topic.questionnaire is not None else None,
    )

    return render_template(
        'main/topic.html',
        form=form,
        topic=topic,
        tweets=tweets,
        current_app=current_app,
    )


@bp_main.route('/topics.json')
def topics_json():
    topics = db.session.query(fw_model.Topic).order_by(fw_model.Topic.user_id, fw_model.Topic.id)

    result = [
        collections.OrderedDict(
            [
                ('topid', topic.id),
                ('title', topic.title),
                ('description', topic.description),
                ('narrative', topic.narrative),
                ('relevant_count', topic.judgment_count(1)),
                ('irrelevant_count', topic.judgment_count(-1)),
                ('queries', len(topic.queries)),
                ('user', {'first_name': topic.user.first_name, 'last_name': topic.user.last_name}),
            ]
        )
        for topic in topics
    ]

    return jsonify(result)


@bp_main.route('/relevance', methods=['POST'])
@flask_login.login_required
def relevance():
    # XXX: this clearly needs validation.

    topic_id = request.form.get('topic_id', type=int)
    tweet_id = request.form.get('tweet_id', type=int)
    judgment = request.form.get('judgment', type=int)

    result = dict(request.form)

    selection_args = json.loads(request.form['selection_args']) if 'selection_args' in request.form else None
    query = db.session.query(fw_model.TopicQuery).filter_by(topic_id=topic_id, **selection_args).first()
    if query is None:
        query = fw_model.TopicQuery(topic_id=topic_id, **selection_args)
        db.session.add(query)
        db.session.flush()

        result['new_query_id'] = query.id

    stmt = pg.insert(fw_model.RelevanceJudgment.__table__)
    stmt = stmt.on_conflict_do_update(
        index_elements=['topic_id', 'tweet_id'],
        set_={
            'judgment': stmt.excluded.judgment,
        },
    )

    db.session.execute(stmt, [{'topic_id': topic_id, 'tweet_id': tweet_id, 'judgment': judgment}])
    db.session.commit()

    return jsonify(result)


@bp_main.route('/user')
@flask_login.login_required
def user():
    return render_template(
        'main/user.html',
        actions=db.session.query(fw_model.UserAction).filter_by(user=flask_login.current_user).order_by(fw_model.UserAction.timestamp)
    )
