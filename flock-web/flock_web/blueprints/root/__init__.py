import json

from flask import render_template, Blueprint, request, redirect, url_for, g, redirect, jsonify

from sqlalchemy import func, select, Table, Column, Integer, String, sql
from sqlalchemy.sql.expression import text, and_, or_, not_, join, column
from sqlalchemy.orm.exc import NoResultFound
from paginate_sqlalchemy import SqlalchemySelectPage, SqlalchemyOrmPage
from sqlalchemy_searchable import parse_search_query
import crosstab

from celery.execute import send_task

from flock import model
from flock_web.app import db, url_for_other_page
import flock_web.queries  as q


bp_root = Blueprint(
    'root', __name__,
    static_folder='static',
    template_folder='templates',
    url_prefix='/<collection>'
    )


def stats_for_feature(feature_name, feature_filter_args=()):
    if feature_filter_args or g.query:
        feature = text(
            'select collection, tweet_id, feature_value from tweet, jsonb_array_elements_text(tweet.features->:feature) as feature_value'
        ).columns(column('collection'), column('tweet_id'), column('feature_value')).bindparams(feature=feature_name).alias()

        feature = (
            select([feature.c.feature_value, func.count().label('count')])
            .where(
                and_(
                    feature.c.collection == g.collection,
                    feature.c.collection == model.Tweet.collection,
                    feature.c.tweet_id == model.Tweet.tweet_id,
                    (
                        text(
                            "tweet.search_vector @@ to_tsquery('pg_catalog.english', :search_vector)"
                        ).bindparams(search_vector=parse_search_query(g.query))
                        if g.query else True
                    ),
                    *(
                        [
                            model.Tweet.tweet_id == model.filtered_tweets.c.tweet_id,
                            model.Tweet.collection == model.filtered_tweets.c.collection,
                        ]
                        if g.filter != 'none' else []
                    ),
                    *(
                        [
                            model.Tweet.tweet_id == model.tweet_cluster.c.tweet_id,
                            model.Tweet.collection == model.tweet_cluster.c.collection,
                            model.tweet_cluster.c._clustered_selection_id == g.clustered_selection._id,
                            model.tweet_cluster.c.label == g.cluster,
                        ]
                        if g.cluster else []
                    ),
                    *feature_filter_args
                )
            )
            .group_by(feature.c.feature_value)
            .alias()
        )

        feature = feature.alias()

    else:
        if g.filter == 'none':
            count_table = model.feature_counts
        else:
            count_table = model.feature_scores

        feature = (
            select([count_table.c.collection, count_table.c.feature_value, count_table.c.count])
            .where(
                and_(
                    count_table.c.feature_name == feature_name,
                    count_table.c.collection == g.collection,
                )
            )
            .alias()
        )

    s = (
        select([feature.c.feature_value, feature.c.count])
        .select_from(feature)
        .order_by(feature.c.count.desc())
    )

    return s


@bp_root.url_defaults
def add_collection(endpoint, values):
    values.setdefault('collection', getattr(g, 'collection', None))


@bp_root.url_value_preprocessor
def pull_collection(endpoint, values):
    g.collection = values.pop('collection')

    g.query = request.args.get('q')
    g.filter = request.args.get('filter', 'pmi')
    g.show_images = request.args.get('show_images') == 'on'

    g.filter_args = sorted(
        (k, sorted(vs))
        for k, vs in request.args.lists()
        if not k.startswith('_') and k not in ('story', 'q', 'filter', 'show_images', 'cluster')
    )

    g.selection_args = {
        'collection': g.collection,
        'query': g.query,
        'filter': g.filter,
        'filter_args': g.filter_args,
    }

    try:
        g.clustered_selection = db.session.query(model.ClusteredSelection).filter_by(celery_status='completed', **g.selection_args).one()
    except NoResultFound:
        g.clustered_selection = None

    g.cluster = request.args.get('cluster')
    if g.cluster:
        assert g.clustered_selection is not None


@bp_root.route('/')
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
        'root/index.html',
        endpoint='.index',
        collection=g.collection,
        stories=stories,
        selected_story=story,
        tweets=tweets,
    )


@bp_root.route('/tweets')
def tweets():
    page_num = request.args.get('_page', 1, type=int)
    items_per_page = request.args.get('_items_per_page', 100, type=int)

    tweets, tweet_count, feature_filter_args = q.build_tweet_query(g.collection, g.query, g.filter, g.filter_args, cluster=g.cluster, clustered_selection=g.clustered_selection)

    # page = SqlalchemyOrmPage(
    #     tweets,
    #     page=page_num,
    #     items_per_page=items_per_page,
    #     url_maker=url_for_other_page,
    # )

    if g.clustered_selection:
        clusters = q.build_cluster_query(g.clustered_selection._id)

    else:
        clusters = None

    return render_template(
        'root/tweets.html',
        tweets=tweets.all(),
        tweet_count=tweet_count,
        # page=page,
        selected_story=g.story,
        stats=[
            (f, db.session.query(stats_for_feature(f, feature_filter_args).limit(12).alias()), request.args.getlist(f))
            for f in ['screen_names', 'hashtags', 'user_mentions']
        ],
        query=g.query,
        query_form_hidden_fields=((k, v) for k, v in request.args.items(multi=True) if not k.startswith('_') and k not in ('q', 'cluster', 'story')),
        filter_form_hidden_fields=((k, v) for k, v in request.args.items(multi=True) if not k.startswith('_') and k not in ('filter', 'show_images')),
        selection_args=json.dumps(g.selection_args),
        selected_filter=g.filter,
        clusters=clusters,
        selected_cluster=g.cluster,
        collection=g.collection,
        show_images=g.show_images,
        endpoint='.tweets',
    )


@bp_root.route('/tweets/<feature_name>')
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
        'root/features.html',
        feature_name=feature_name,
        other_feature_name=other_feature,
        other_feature_values=other_feature_values,
        page=page,
        items=items,
    )


@bp_root.route('/cluster', methods=['POST'])
def cluster():
    selection_args = json.loads(request.form['selection_args'])
    from_url = request.form['from_url']

    try:
        clustered_selection = db.session.query(model.ClusteredSelection).filter_by(**selection_args).one()
    except NoResultFound:
        task_id = g.celery.send_task('flock_web.tasks.cluster_selection', kwargs={'selection_args': selection_args}).id
    else:
        task_id = clustered_selection.celery_id

    task = g.celery.AsyncResult(task_id)

    location = url_for('.cluster_status', task_id=task_id)
    if not 'redirect' in request.form:
        return jsonify({'Location': location, 'info': task.info}), 202, {'Location': location}
    else:
        return redirect(location)


@bp_root.route('/cluster/status/<task_id>')
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
                'root/cluster_snippet.html',
                clusters=clusters,
            )

    response['cluster_html_snippet'] = cluster_html_snippet


    return jsonify(response)
