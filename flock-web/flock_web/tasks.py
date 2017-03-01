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
from flock_web.queries import build_tweet_query


flask_app, celery = create_app(os.environ['FLOCK_CONFIG'], return_celery=True)


logger = logging.getLogger(__name__)


@celery.task
def sleep():
    import time, random

    time.sleep(5)

    return random.randint(0, 100)


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
                'tweet_count': tweet_count,
                'selection_args': selection_args,
                **extra_meta,
            }
        )


    with flask_app.app_context():

        clustered_selection = model.ClusteredSelection(celery_id=self.request.id, celery_status='started', **selection_args)
        db.session.add(clustered_selection)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            logger.info('A duplicate task.')
            return {'current': 1, 'total': 1, 'status': 'A duplicate task.'}

        tweets, tweet_count, feature_filter_args = build_tweet_query(possibly_limit=False, **selection_args)

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
            #algorithm='brute',
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

        insert_stmt = pg.insert(model.tweet_cluster)
        for doctag, label in zip(doctags, dbscan.labels_):
            tweet_id = int(doctag[3:])

            db.session.execute(
                insert_stmt.values(
                    [
                        {
                            'tweet_id': tweet_id,
                            'collection': selection_args['collection'],
                            '_clustered_selection_id': clustered_selection._id,
                            'label':str(label),
                        }
                    ]
                )
            )

        clustered_selection.celery_status = 'completed'
        db.session.commit()

    return {'current': 10, 'total': 10, 'status': 'Task completed!', 'total_labels': len(set(dbscan.labels_))}
