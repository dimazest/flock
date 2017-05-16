import json

from flask import render_template, Blueprint, request, redirect, url_for, g, redirect, jsonify, get_template_attribute, Response, stream_with_context, current_app, flash
import flask_login

from sqlalchemy import func, select, Table, Column, Integer, String, sql
from sqlalchemy.sql.expression import text, and_, or_, not_, join, column
from sqlalchemy.orm.exc import NoResultFound
from paginate_sqlalchemy import SqlalchemySelectPage, SqlalchemyOrmPage
import crosstab

from celery.execute import send_task

from flock import model
from flock_web.app import db, url_for_other_page
import flock_web.queries  as q
import flock_web.model as fw_model

from sklearn.feature_extraction.text import TfidfVectorizer

bp_collection = Blueprint(
    'collection', __name__,
    static_folder='static',
    template_folder='templates',
    url_prefix='/c/<collection>'
    )


@bp_collection.url_defaults
def add_collection(endpoint, values):
    values.setdefault('collection', getattr(g, 'collection', None))


@bp_collection.url_value_preprocessor
def pull_collection(endpoint, values):
    g.collection = values.pop('collection')

    g.query = request.args.get('q')
    g.query_type = 'multiword' if g.query is not None and ' ' in g.query else 'singleword'
    g.filter = request.args.get('filter', 'pmi')
    g.show_images = request.args.get('show_images') == 'on'

    g.filter_args = sorted(
        (k, sorted(vs))
        for k, vs in request.args.lists()
        if not k.startswith('_') and k not in ('q', 'filter', 'show_images', 'cluster', 'topic')
    )

    g.selection_args = {
        'collection': g.collection,
        'query': g.query,
        'filter': g.filter,
        'filter_args': g.filter_args,
    }

    clustered_selection = db.session.query(model.ClusteredSelection).filter_by(celery_status='completed', **g.selection_args).one_or_none()
    g.clustered_selection_id = None if clustered_selection is None else clustered_selection._id

    g.cluster = request.args.get('cluster')
    if g.cluster:
        assert g.clustered_selection_id is not None


    topic_id = request.args.get('topic', None, type=int)
    if topic_id is not None:
        g.topic = db.session.query(fw_model.Topic).get(topic_id)
    else:
        g.topic = None


@bp_collection.route('/')
@flask_login.login_required
def index():

    _story_id = request.args.get('story', type=int)
    story = None
    if _story_id is not None:
        story = db.session.query(model.Story).get(int(_story_id))

    stories = (
        db.session.query(model.Story)
        .filter(model.Story.collection == g.collection)
        .all()
    )

    if story is not None:
        tweets = (
            db.session.query(model.Tweet)
            .join(model.tweet_story)
            .filter(model.tweet_story.c._story_id == story._id)
            .order_by(model.tweet_story.c.rank)
        )
    else:
        tweets = []

    return render_template(
        'collection/index.html',
        endpoint='.index',
        collection=g.collection,
        stories=stories,
        selected_story=story,
        tweets=tweets,
        current_app=current_app,
    )


@bp_collection.route('/tweets')
@flask_login.login_required
def tweets():

    if not g.query:
        flash('Please enter a query.')

        return (redirect(url_for('.index')))

    page_num = request.args.get('_page', 1, type=int)
    items_per_page = request.args.get('_items_per_page', 100, type=int)

    tweet_task, tweet_count = (
        g.celery.send_task(
            'flock_web.tasks.tweets',
            kwargs={
                'collection': g.collection,
                'query': g.query,
                'filter_': g.filter,
                'filter_args': g.filter_args,
                'cluster': g.cluster,
                'clustered_selection_id': g.clustered_selection_id,
                'count': count,
            },
           queue=f'tweets_{g.query_type}',
        ) for count in (False, True)
    )

    # page = SqlalchemyOrmPage(
    #     tweets,
    #     page=page_num,
    #     items_per_page=items_per_page,
    #     url_maker=url_for_other_page,
    # )

    if g.clustered_selection_id:
        clusters = q.build_cluster_query(g.clustered_selection_id)

    else:
        clusters = None

    selection_for_topic_args = {'cluster': g.cluster, **g.selection_args}
    del selection_for_topic_args['collection']

    stat_tasks = [
        (
            f_name,
            g.celery.send_task(
                'flock_web.tasks.stats_for_feature',
                kwargs={
                    'feature_name': f_name,
                    'feature_alias': f_alias,
                    'active_features': request.args.getlist(f_name),
                    'filter_args': g.filter_args,
                    'query': g.query,
                    'collection': g.collection,
                    'filter_': g.filter,
                    'clustered_selection_id': g.clustered_selection_id,
                    'cluster': g.cluster,
                },
                queue=f'stats_for_feature_{g.query_type}',
            ),
        )
        for f_name, f_alias in [('screen_names', 'Users'), ('hashtags', 'Hashtags'), ('user_mentions', 'User mentions')]
    ]

    response = Response(
        render_template(
            'collection/tweets.html',
            tweet_task=tweet_task,
            tweet_count=tweet_count,
            # page=page,
            stats=stat_tasks,
            query=g.query,
            query_form_hidden_fields=((k, v) for k, v in request.args.items(multi=True) if not k.startswith('_') and k not in ('q', 'cluster', 'story')),
            filter_form_hidden_fields=((k, v) for k, v in request.args.items(multi=True) if not k.startswith('_') and k not in ('filter', 'show_images')),
            selection_args=json.dumps(g.selection_args),
            selection_for_topic_args=json.dumps(selection_for_topic_args),
            topics=flask_login.current_user.topics,
            selected_filter=g.filter,
            clusters=clusters,
            selected_cluster=g.cluster,
            collection=g.collection,
            show_images=g.show_images,
            endpoint='.tweets',
            selected_topic=g.topic,
            # relevance_judgments={j.tweet_id: j.judgment for j in g.topic.judgments} if g.topic is not None else {},
            current_app=current_app,
        ),
    )
    response.headers['X-Accel-Buffering'] = 'no'
    return response


@bp_collection.route('/tweets.jsonl')
def tweets_json():
    tweets = q.build_tweet_query(
        collection=g.collection,
        query=g.query,
        filter_=g.filter,
        filter_args=g.filter_args,
        possibly_limit=False,
        cluster=g.cluster,
        clustered_selection_id=g.clustered_selection_id,
    ).all()

    vectorizer = TfidfVectorizer(binary=True)
    vectors = vectorizer.fit_transform(t.text for t in tweets)

    def generate():
        for t, v in zip(tweets, vectors):
            yield json.dumps(
                {
                    'tweet_id': t.tweet_id,
                    'text': t.text,
                    'tokens': t.features['tokenizer'],
                    'language': t.features['languages'][0],
                    'created_at': t.created_at.isoformat(),
                    'vector': v.toarray().flatten().tolist(),
                }
            ) + '\r\n'

    return Response(stream_with_context(generate()), mimetype='text/plain')


@bp_collection.route('/tweets/<feature_name>')
@flask_login.login_required
def features(feature_name):
    other_feature = request.args.get('_other', None)
    unstack = request.args.get('_unstack', None) if other_feature is not None else None
    other_feature_values = None

    page_num = int(request.args.get('_page', 1))
    items_per_page = int(request.args.get('_items_per_page', 100))

    feature_select = stats_for_feature(feature_name, g.feature_filter_args)

    page = SqlalchemySelectPage(
        db.session, feature_select,
        page=page_num, items_per_page=items_per_page,
        url_maker=url_for_other_page,
    )
    items = page.items

    if other_feature is not None:
        feature_column = sql.literal_column('feature', String)
        other_feature_column = sql.literal_column('other_feature', String)
        stmt = (
            select(
                [feature_column, other_feature_column, func.count()]
            )
            .select_from(
                text(
                    'tweet, '
                    'jsonb_array_elements_text(tweet.features->:feature) as feature, '
                    'jsonb_array_elements_text(tweet.features->:other_feature) as other_feature'
                ).bindparams(feature=feature_name, other_feature=other_feature)
            ).where(
                and_(
                    sql.literal_column('collection') == g.collection,
                    feature_column.in_(
                        feature_select
                        .with_only_columns(['feature'])
                        .offset((page_num - 1) * items_per_page)
                        .limit(items_per_page)
                    )
                )
            )
            .group_by(feature_column, other_feature_column)
        )

        items = db.session.execute(stmt.order_by(func.count().desc()))

    if unstack:
        other_feature_values_select = (
            select([other_feature_column.distinct()])
            .select_from(stmt.alias())
        )
        other_feature_values = [
            v for v, in
            db.session.execute(other_feature_values_select.order_by(other_feature_column))
        ]

        from sqlalchemy import MetaData
        ret_types = Table(
            '_t_', MetaData(),
            Column('feature', String),
            extend_existing=True,
            *[Column(v, Integer) for v in other_feature_values]
        )

        row_total = crosstab.row_total(
            [ret_types.c[v] for v in other_feature_values]
        ).label('total')

        stmt = (
            select(
                [
                    '*', row_total,
                ]
            )
            .select_from(
                crosstab.crosstab(
                    stmt,
                    ret_types,
                    categories=other_feature_values_select,
                )
            )
            .order_by(
                row_total.desc(),
                ret_types.c.feature,
            )
        )

        items = db.session.execute(stmt)

    return render_template(
        'collection/features.html',
        feature_name=feature_name,
        other_feature_name=other_feature,
        other_feature_values=other_feature_values,
        page=page,
        items=items,
    )


@bp_collection.route('/cluster', methods=['POST'])
@flask_login.login_required
def cluster():
    selection_args = json.loads(request.form['selection_args'])

    task = g.celery.send_task(
        'flock_web.tasks.cluster_selection',
        kwargs={'selection_args': selection_args},
        queue=f'cluster_{g.query_type}'
    )

    location = url_for('.task_result', task_id=task.id)
    return jsonify({'Location': location, 'info': task.info}), 202, {'Location': location}


@bp_collection.route('/cluster/status/<task_id>')
@flask_login.login_required
def cluster_status(task_id):
    task = g.celery.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'info': {
                'current': 0,
                'total': 1,
            },
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'info': task.info,
        }
    else:
        response = {
            'state': task.state,
            'current': 1,
            'total': 1,
            'status': str(task.info),  # this is the exception raised
        }

    cluster_html_snippet = None
    if task.state == 'SUCCESS':
        try:
            clustered_selection = db.session.query(model.ClusteredSelection).filter_by(celery_id=task_id).one()
        except NoResultFound:
            pass
        else:
            clusters = q.build_cluster_query(clustered_selection._id)

            cluster_html_snippet = render_template(
                'collection/cluster_snippet.html',
                clusters=clusters,
            )

    response['cluster_html_snippet'] = cluster_html_snippet

    return jsonify(response)


@bp_collection.route('/tasks/<task_id>')
@flask_login.login_required
def task_result(task_id):
    task = g.celery.AsyncResult(task_id)

    result = {'state': task.state}

    if task.successful():

        if task.result.get('task_name') == 'flock_web.tasks.tweets':

            if task.result['count']:
                render_tweet_count = get_template_attribute('collection/macro.html', 'render_tweet_count')
                result['html'] = render_tweet_count(task.result['data'])
            else:
                render_tweets = get_template_attribute('collection/macro.html', 'render_tweets')

                result['html'] = render_tweets(
                    topic=g.topic,
                    tweets=task.result['data'],
                    show_images=g.show_images,
                    relevance_judgments={j.tweet_id: j.judgment for j in g.topic.judgments} if g.topic is not None else {},
                )
        elif task.result.get('task_name') == 'flock_web.tasks.stats_for_feature':
            render_stats = get_template_attribute('collection/macro.html', 'render_stats')

            features = task.result['data']
            selected_feature_names = set(name for name, _ in features)
            active_feature_names = set(task.result['active_features'])

            missing_feature_names = active_feature_names - selected_feature_names
            features = features + [(name, 0) for name in missing_feature_names]

            result['data'] = task.result
            result['html'] = render_stats(
                feature_name=task.result['feature_name'],
                feature_alias=task.result['feature_alias'],
                features=features,
                active_feature_names=active_feature_names,
                collection=g.collection,
                hidden_fields=[(k, v) for k, v in request.args.items(multi=True) if not k.startswith('_')],
            )
        elif task.result.get('task_name') == 'flock_web.tasks.cluster_selection':
            result['data'] = task.result,
            result['html'] = render_template(
                'collection/cluster_snippet.html',
                clusters=task.result['data'],
            )

        else:
            result.update(
                {
                    'status': str(task.info),
                }
            )

    elif task.state == 'PENDING':
        result.update(
            {
                'info': {
                    'current': 0,
                    'total': 1,
                },
                'status': 'Pending...'
            }
        )
    elif task.state != 'FAILURE':
        result.update(
            {
                'info': getattr(task, 'info', {}),
            }
        )
    else:
        result.update(
            {
                'str_info': str(task.info),
            }
        )

    return jsonify(result)