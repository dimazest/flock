import os
import logging
import itertools
import functools

from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects import postgresql as pg

from celery.result import AsyncResult

import pandas as pd
import numpy as np
from sklearn import cluster, preprocessing, metrics

from flock_web.app import create_app, db
from flock import model
from flock_web import queries as q
from flock_web import model as fw_model


flask_app, celery = create_app(os.environ['FLOCK_CONFIG'], return_celery=True)


logger = logging.getLogger(__name__)


def cached_task(func):

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        with flask_app.app_context():

            task_result = fw_model.TaskResult(name=self.name, celery_id=self.request.id, celery_status='started', args=args, kwargs=kwargs)
            db.session.add(task_result)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                logger.info('A duplicate task.')

                task_result = db.session.query(fw_model.TaskResult).filter_by(name=self.name, args=args, kwargs=kwargs).one()

                if task_result.celery_status == 'completed':
                    return task_result.result

            result = func(self, *args, **kwargs)

            task_result.result = result
            task_result.celery_status = 'completed'
            task_result.celery_id = self.request.id

            db.session.commit()

            return result

    return wrapper


@celery.task(bind=True)
@cached_task
def cluster_selection(self, selection_args):

    def update_state(current, total, status=None, state='PROGRESS', **extra_meta):
        if status is None:
            status = '{} out of {}.'.format(current, total)

        self.update_state(
            state=state,
            meta={
                'status': status,
                'current': current,
                'total': total,
                **extra_meta,
            }
        )

    update_state(1, 7, status='Started...')

    filter_ = selection_args.pop('filter', None)

    update_state(2, 7, status='Querying the database...')
    tweets = q.build_tweet_query(possibly_limit=False, filter_=filter_, **selection_args)

    def tokens(tweets):
        for tweet in tweets:
            for token in tweet.features['tokenizer']['tokens']:
                if not token.startswith('http') and len(token) > 2:
                    yield tweet.tweet_id, tweet.created_at, token

    token_stream = pd.DataFrame.from_records(tokens(tweets), columns=['tweet_id', 'created_at', 'token'])
    token_stream.drop_duplicates(inplace=True)
    collection = selection_args['collection']
    token_stream = token_stream[token_stream['created_at'] > flask_app.config.get(f'collection:{collection}')['start_date']]

    number_of_tweets = len(token_stream['tweet_id'].drop_duplicates())

    if number_of_tweets > 400_000:
        min_token_freq = 200
        min_trending_score = 2
        dbscan_min_samples = 3
        min_cluster_size = 2
    if number_of_tweets > 200_000:
        min_token_freq = 100
        min_trending_score = 2
        dbscan_min_samples = 3
        min_cluster_size = 2
    if number_of_tweets > 100_000:
        min_token_freq = 40
        min_trending_score = 1.5
        dbscan_min_samples = 2
        min_cluster_size = 2
    if number_of_tweets > 10_000:
        min_token_freq=10,
        min_trending_score=1.5
        dbscan_min_samples=2
        min_cluster_size=2
    else:
        min_token_freq=3,
        min_trending_score=1.5
        dbscan_min_samples=2
        min_cluster_size=2

    update_state(3, 7, status='Counting tokens...')
    token_counts = token_stream['token'].value_counts(sort=False)

    filtered_token_stream = pd.DataFrame(token_stream[(token_counts[token_stream['token']] > min_token_freq).values])
    filtered_token_stream['count'] = 1

    tweet_token_matrix = filtered_token_stream.set_index(['created_at', 'tweet_id', 'token']).unstack('token', fill_value=0)['count']

    window_counts = tweet_token_matrix.resample('1D', level='created_at').sum().fillna(0)

    update_state(4, 7, status='Calculating trending scores...')
    scores = (
        (window_counts - window_counts.expanding(axis='rows', min_periods=1).mean()) /
        window_counts.expanding(axis='rows', min_periods=1).std()
    )

    update_state(5, 7, status='Detecting trending words...')
    trending_words = scores.max(axis='rows').sort_values(ascending=False)
    trending_words = trending_words[trending_words > min_trending_score]

    trending_token_tweet_matrix = tweet_token_matrix[trending_words.index].T
    trending_token_tweet_matrix = trending_token_tweet_matrix.loc[:, (trending_token_tweet_matrix.max(axis='rows') > 0).values]

    if not len(trending_token_tweet_matrix):
        return {
            'data': [],
            'task_name': self.name,
        }

    update_state(6, 7, status='Trending word similarity...')
    trending_words_pairwise_distances = metrics.pairwise.pairwise_distances(trending_token_tweet_matrix.values, metric='cosine')

    dbscan = cluster.DBSCAN(
        min_samples=dbscan_min_samples,
        metric='precomputed',
        eps=0.8,
    )
    dbscan.fit(trending_words_pairwise_distances)

    result = []
    for label in set(dbscan.labels_):
        if label > 0:
            size = trending_token_tweet_matrix.loc[trending_words.loc[dbscan.labels_ == label].index].min(axis='rows').sum()

            if size < min_cluster_size:
                continue

            tokens = trending_words.iloc[np.argwhere(dbscan.labels_ == label).flatten()].index

            result.append(
                (
                    list(tokens),
                    int(size)
                ),
        )

    result = sorted(result, key=lambda i: (len(i[0]), i[1]), reverse=True)

    return {
        'data': result,
        'task_name': self.name,
    }


@celery.task(bind=True)
@cached_task
def stats_for_feature(self, feature_name, feature_alias, active_features, **query_kwargs):
    return {
        'data': db.session.query(
            q.stats_for_feature_query(feature_name=feature_name, **query_kwargs).limit(12).alias()
        ).all(),
        'task_name': self.name,
        'feature_name': feature_name,
        'feature_alias': feature_alias,
        'active_features': active_features,
    }


@celery.task(bind=True)
@cached_task
def tweets(self, count=False, **query_kwargs):
    result = q.build_tweet_query(count=count, **query_kwargs)

    if count:
        return {
            'data': result,
            'count': count,
            'task_name': self.name,
        }
    else:
        return {
            'data': [
                {
                    'tweet_id': t.tweet_id,
                    'features': t.features,
                    'created_at': t.created_at.isoformat(),
                }
                for t in result
            ],
            'count': count,
            'task_name': self.name,
        }
