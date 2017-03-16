import os
import logging
import itertools

from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects import postgresql as pg

from gensim.models.doc2vec import LabeledSentence, Doc2Vec
from sklearn import cluster, preprocessing, neighbors, metrics
import hdbscan

from flock_web.app import create_app, db
from flock import model
from flock_web import queries as q


flask_app, celery = create_app(os.environ['FLOCK_CONFIG'], return_celery=True)


logger = logging.getLogger(__name__)


def sentences(tweets):

    for i, tweet in enumerate(tweets, start=1):
        if not tweet.features['doc2vec']:
            logger.warning('Empty features for tweet %s.', tweet.tweet_id)
            continue

        yield LabeledSentence(**tweet.features['doc2vec'])

    logger.info('%s tweets were selected from the DB.', i)


def Epochs(model, sentences):
    epoch = 0
    while True:
        logger.info('Epoch {}. Alpha {:.3f}'.format(epoch, model.alpha))
        epoch += 1
        model.train(sentences())
        model.alpha = max(model.alpha - 0.001, 0.001)
        model.min_alpha = model.alpha

        yield


@celery.task(bind=True)
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


    with flask_app.app_context():

        update_state(1, 3, status='Started.')

        filter_ = selection_args.pop('filter', None)

        clustered_selection = model.ClusteredSelection(celery_id=self.request.id, celery_status='started', filter=filter_, **selection_args)
        db.session.add(clustered_selection)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            logger.info('A duplicate task.')
            return {'current': 1, 'total': 1, 'status': 'A duplicate task.'}



        tweets = q.build_tweet_query(possibly_limit=False, filter_=filter_, **selection_args)

        insert_stmt = pg.insert(model.tweet_cluster)

        if flask_app.config.get('MOCK_CLUSTERING'):
            update_state(2, 3, status='Mocked clustering.')

            import random
            for tweet in tweets:
                db.session.execute(
                    insert_stmt.values(
                        [
                            {
                                'tweet_id': tweet.tweet_id,
                                'collection': selection_args['collection'],
                                '_clustered_selection_id': clustered_selection._id,
                                'label': random.choice('ABCDEFG'),
                            }
                        ]
                    )
                )

        else:
            doc2vec_model = Doc2Vec(
                size=100,
                sample=1e-5,
                negative=15,
                alpha=0.025,
                min_alpha=0.025,
                workers=8,
                min_count=10,
            )

            EPOCH_NUM = 25
            TOTAL = 1 + EPOCH_NUM + 2

            update_state(1, TOTAL, step='Building vocabulary.')
            doc2vec_model.build_vocab(sentences(tweets))

            epochs = Epochs(doc2vec_model, lambda: sentences(tweets))

            for s in range(EPOCH_NUM):
                next(epochs)
                update_state(s + 1, TOTAL, status='Training word vectors.')

            doc2vec_model.docvecs.init_sims(replace=True)
            doc2vec_model.init_sims(replace=True)

            doctags = [doctag for doctag in doc2vec_model.docvecs.doctags.keys() if doctag.startswith('id:')]
            tweet_vectors = doc2vec_model.docvecs[doctags]

            update_state(1 + EPOCH_NUM + 1, TOTAL, status='Calculating nearest neighbors.')
            neigh = neighbors.NearestNeighbors(
                metric='euclidean',
                radius=0.9,
                algorithm='brute',
                n_jobs=8,
            )

            neigh.fit(tweet_vectors)
            A = neigh.radius_neighbors_graph(mode='distance',)

            update_state(1 + EPOCH_NUM + 2, TOTAL, status='DBSCAN.')
            dbscan = cluster.DBSCAN(
                min_samples=3,
                metric='precomputed',
                eps=0.8,
                #     algorithm='kd_tree',
                n_jobs=-1,
            )

            dbscan.fit(A)

            for doctag, label in zip(doctags, dbscan.labels_):
                tweet_id = int(doctag[3:])

                db.session.execute(
                    insert_stmt.values(
                        [
                            {
                                'tweet_id': tweet_id,
                                'collection': selection_args['collection'],
                                '_clustered_selection_id': clustered_selection._id,
                                'label': str(label),
                            }
                        ]
                    )
                )

                clustered_selection.celery_status = 'completed'
                db.session.commit()

    # return {'current': 10, 'total': 10, 'status': 'Task completed!', 'total_labels': len(set(dbscan.labels_))}
    return {'current': 10, 'total': 10, 'status': 'Task completed!', 'total_labels': None}


@celery.task
def stats_for_feature(**query_kwargs):
    with flask_app.app_context():
        return db.session.query(
            q.stats_for_feature_query(**query_kwargs).limit(12).alias()
        ).all()


@celery.task
def tweets(count=False, **query_kwargs):
    with flask_app.app_context():
        result = q.build_tweet_query(count=count, **query_kwargs)

        if count:
            return result
        else:
            return [
                {
                    'tweet_id': t.tweet_id,
                    'features': t.features,
                    'created_at': t.created_at,
                }
                for t in result
            ]
