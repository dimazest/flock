import os
import logging

from sqlalchemy.exc import IntegrityError

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


@celery.task(bind=True)
def cluster_selection(self, selection_args):
    with flask_app.app_context():

        # clustered_selection = model.ClusteredSelection(celery_id=self.request.id, celery_status='started', **selection_args)
        # db.session.add(clustered_selection)
        # try:
        #     db.session.commit()
        # except IntegrityError:
        #     db.session.rollback()
        #     logger.info('A duplicate task.')
        #     return {'current': 1, 'total': 1, 'status': 'A duplicate task.'}

        tweets, tweet_count, feature_filter_args = build_tweet_query(**selection_args)

        for i in range(10):
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': i,
                    'total': 10,
                    'status': '{} out of {}.'.format(i, 10),
                    'tweets': tweet_count,
                    'selection_args': selection_args,
                }
            )
            import time
            time.sleep(1)

        # clustered_selection.celery_status = 'completed'
        # db.session.commit()

    return {'current': 10, 'total': 10, 'status': 'Task completed!'}
