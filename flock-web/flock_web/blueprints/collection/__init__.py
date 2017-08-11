import json

from flask import render_template, Blueprint, request, url_for, g, redirect, jsonify, get_template_attribute, Response, stream_with_context, flash
import flask_login

import sqlalchemy as sa
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.dialects import postgresql

from flock import model
from flock_web.app import db
import flock_web.queries as q
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
        collection=g.collection,
        stories=stories,
        selected_story=story,
        tweets=tweets,
    )


@bp_collection.route('/tweets')
@flask_login.login_required
def tweets():

    if not g.query:
        flash('Please enter a query.')

        return (redirect(url_for('.index')))

    # page_num = request.args.get('_page', 1, type=int)
    # items_per_page = request.args.get('_items_per_page', 100, type=int)

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
            stats=stat_tasks,
            query_form_hidden_fields=((k, v) for k, v in request.args.items(multi=True) if not k.startswith('_') and k not in ('q', 'cluster', 'story')),
            filter_form_hidden_fields=((k, v) for k, v in request.args.items(multi=True) if not k.startswith('_') and k not in ('filter', 'show_images')),
            selection_args=json.dumps(g.selection_args),
            selection_for_topic_args=json.dumps(selection_for_topic_args),
            topics=flask_login.current_user.topics,
            clusters=clusters,
            # relevance_judgments={j.tweet_id: j.judgment for j in g.topic.judgments} if g.topic is not None else {},
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


@bp_collection.route('/eval/topics')
@flask_login.login_required
def user_eval_topics():

    user_eval_topics = db.session.query(fw_model.EvalTopic).filter_by(user=flask_login.current_user, collection=g.collection)

    return render_template(
        'collection/eval_topics.html',
        user_eval_topics=user_eval_topics,
    )


@bp_collection.route('/eval/topics/<rts_id>')
@flask_login.login_required
def eval_topic(rts_id):
    eval_topic = db.session.query(fw_model.EvalTopic).filter_by(rts_id=rts_id, collection=g.collection).one()

    return render_template(
        'collection/eval_topic.html',
        eval_topic=eval_topic,
        state=eval_topic.judge_state(),
    )


@bp_collection.route('/eval/topics/<rts_id>.json')
@flask_login.login_required
def eval_topic_json(rts_id):
    eval_topic = db.session.query(fw_model.EvalTopic).filter_by(rts_id=rts_id, collection=g.collection).one()

    return jsonify(eval_topic.judge_state())


@bp_collection.route('/eval/topics/<rts_id>/cluster', methods=['GET', 'POST', 'DELETE', 'PUT'])
@flask_login.login_required
def cluster_eval_topic(rts_id):
    eval_topic = db.session.query(fw_model.EvalTopic).filter_by(rts_id=rts_id, collection=g.collection).one()

    extra_state = {}

    if request.method == 'GET':
            return render_template(
                'collection/eval_topic_cluster.html',
                state=eval_topic.state(),
                eval_topic=eval_topic,
            )

    request_json = request.get_json()

    eval_cluster = None
    if request.method == 'POST':
        eval_cluster = fw_model.EvalCluster(
            gloss=request_json['gloss'],
            eval_topic=eval_topic,
        )

        db.session.flush()
        extra_state['newClusterID'] = eval_cluster.rts_id

    if eval_cluster is None:
        eval_cluster = db.session.query(fw_model.EvalCluster).get((rts_id, g.collection, request_json['clusterID']))

    if request.method == 'DELETE':
        for a in eval_cluster.assignments:
            db.session.delete(a)
        db.session.delete(eval_cluster)

    if request.method == 'PUT':
        eval_cluster.gloss = request_json['gloss']

    db.session.commit()

    state = eval_topic.state()
    state.update(extra_state)

    return jsonify(state)


@bp_collection.route('/eval/topics/<eval_topic_rts_id>/cluster/assign_tweet', methods=['POST'])
@flask_login.login_required
def assign_tweet_to_eval_cluster(eval_topic_rts_id):
    assignment = request.get_json()

    t = fw_model.EvalClusterAssignment.__table__
    insert_stmt = postgresql.insert(t).values(
        eval_topic_rts_id=eval_topic_rts_id,
        eval_topic_collection=g.collection,
        tweet_id=int(assignment['tweet_id']),
        eval_cluster_rts_id=assignment['cluster_id'],
    )
    insert_stmt = insert_stmt.on_conflict_do_update(
        constraint=t.primary_key,
        set_={'eval_cluster_rts_id': insert_stmt.excluded.eval_cluster_rts_id},
    )

    db.session.execute(insert_stmt)
    db.session.commit()

    eval_topic = db.session.query(fw_model.EvalTopic).filter_by(rts_id=eval_topic_rts_id, collection=g.collection).one()
    state = eval_topic.state()

    return jsonify(state)


@bp_collection.route('/eval/topics/<eval_topic_rts_id>/cluster/swap_clusters', methods=['PUT'])
@flask_login.login_required
def swap_clusters(eval_topic_rts_id):
    data = request.get_json()

    cluster1 = db.session.query(fw_model.EvalCluster).get((eval_topic_rts_id, g.collection, data['clusterID1']))
    cluster2 = db.session.query(fw_model.EvalCluster).get((eval_topic_rts_id, g.collection, data['clusterID2']))

    cluster1.position, cluster2.position = cluster2.position, cluster1.position

    db.session.commit()

    eval_topic = db.session.query(fw_model.EvalTopic).filter_by(rts_id=eval_topic_rts_id, collection=g.collection).one()
    return jsonify(eval_topic.state())


@bp_collection.route('/eval/topics/<eval_topic_rts_id>/judge_tweet', methods=['POST'])
@flask_login.login_required
def judge_tweet(eval_topic_rts_id):
    data = request.get_json()

    if data['judgment'] == 'missing':
        judgment = None
        missing = True
    else:
        judgment = int(data['judgment']) if data['judgment'] is not None else None
        missing = False

    t = fw_model.EvalRelevanceJudgment.__table__
    insert_stmt = postgresql.insert(t).values(
        eval_topic_rts_id=eval_topic_rts_id,
        collection=g.collection,
        tweet_id=int(data['tweet_id']),
        judgment=judgment,
        missing=missing,
    )
    insert_stmt = insert_stmt.on_conflict_do_update(
        constraint=t.primary_key,
        set_={
            'judgment': insert_stmt.excluded.judgment,
            'missing': insert_stmt.excluded.missing,
        },
    )

    db.session.execute(insert_stmt)
    db.session.commit()

    eval_topic = db.session.query(fw_model.EvalTopic).filter_by(rts_id=eval_topic_rts_id, collection=g.collection).one()
    state = eval_topic.judge_state()

    return jsonify(state)


@bp_collection.route('/eval/qrelsfile')
def qrelsfile():
    def records():
        judgments = (
            db.session.query(fw_model.EvalRelevanceJudgment)
            .filter_by(collection=g.collection)
            .filter(
                sa.or_(
                    fw_model.EvalRelevanceJudgment.judgment != None,
                    fw_model.EvalRelevanceJudgment.missing == True,
                )
            )
            .order_by(
                fw_model.EvalRelevanceJudgment.eval_topic_rts_id,
                fw_model.EvalRelevanceJudgment.position,
                fw_model.EvalRelevanceJudgment.tweet_id,
            )
        )
        for j in judgments:
            judgment = j.judgment if j.judgment is not None else ''
            if j.missing:
                judgment = -2

            yield '{j.eval_topic_rts_id} Q0 {j.tweet_id} {judgment}'.format(j=j, judgment=judgment)

    return Response('\n'.join(records()), 200, mimetype='text/text')


@bp_collection.route('/eval/clusters')
def clusters():
    def records():
        assignments = (
            db.session.query(fw_model.EvalClusterAssignment)
            .filter_by(eval_topic_collection=g.collection)
        )

        for a in assignments:
            yield '{a.eval_topic_rts_id} {a.eval_cluster_rts_id} {a.tweet_id}'.format(a=a)

    return Response('\n'.join(records()), 200, mimetype='text/text')


@bp_collection.route('/eval/glosses')
def glosees():
    def records():
        clusters = (
            db.session.query(fw_model.EvalCluster)
            .filter_by(eval_topic_collection=g.collection)
        )

        for c in clusters:
            yield '{c.eval_topic_rts_id}\t{c.rts_id}\t{c.gloss}'.format(c=c)

    return Response('\n'.join(records()), 200, mimetype='text/text')
