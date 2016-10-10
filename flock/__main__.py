import json
import logging

from itertools import chain

import click
import click_log

from poultry import readline_dir

from sqlalchemy.dialects import postgresql as pg

from . import model


logger = logging.getLogger(__name__)


def create_session(ctx, param, value):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(value)
    model.metadata.bind = engine
    Session = sessionmaker(bind=engine)

    return Session()


@click.group()
@click_log.simple_verbosity_option()
@click_log.init('flock')
def cli():
    pass


@cli.command()
@click.option('--session', default='postgresql://127.0.0.1/twitter', callback=create_session)
def initdb(session):
    model.metadata.create_all()


@cli.command()
@click.option('--session', default='postgresql://127.0.0.1/twitter', callback=create_session)
def dropdb(session):
        model.metadata.drop_all()


def create_expander(ctx, param, value):
    from flock_conf.expander import Expander

    return Expander.from_file(value)


@cli.command()
@click.option('--source', default=None, help='Tweet source.')
@click.option('--session', default='postgresql://127.0.0.1/twitter', callback=create_session)
@click.option('--clusters', default='clusters.cfg', callback=create_expander)
def insert(source, session, clusters):

    user_labels = clusters.user_labels()

    for i, t in enumerate(readline_dir(source), start=1):
        if (i % 100000) == 0:
            logger.debug('Processed %s tweets, it\'s time to flush.', i)
            session.flush()

        features = dict()

        # As a side effect, the users whose ids are not in user label don't have an @ infront.
        features['screen_names'] = list(
            user_labels.get(t.parsed['user']['id'], [t.screen_name])
        )

        features['user_mentions'] = sorted(
            chain.from_iterable(
                user_labels.get(mention['id'], [mention['screen_name']])
                for mention in t.parsed['entities']['user_mentions']
            )
        )

        features['from_riga'] = (
            t.coordinates and
            23.9325829 <= t.coordinates.lon <= 56.8570671 and
            24.3247299 <= t.coordinates.lat <= 57.0859184
        )

        stmt = pg.insert(model.Tweet.__table__).values(
            id=t.id,
            tweet=t.parsed,
            features=features,
            created_at=t.created_at,
        ).on_conflict_do_update(
            index_elements=['id'],
            set_={'features': json.dumps(features)}
        )

        session.execute(stmt)
    else:
        session.commit()
        try:
            i
        except UnboundLocalError:
            logger.warn(
                '0 tweets were inserted. '
                'Are twarc credentials set?'
            )
        else:
            logger.info('Processed %s tweets.', i)


@cli.group()
def config():
    pass


def read_poultry_config(ctx, param, value):
    from poultry.config import Config as PoultryConfig

    return PoultryConfig(value)


@config.command()
@click.option('--poultry-config', default='poultry.cfg', callback=read_poultry_config)
@click.option('--clusters', default='clusters.cfg', callback=create_expander)
def query_user_ids(poultry_config, clusters):
    from poultry.stream import create_client

    screen_names = list(
        u[1:] for u in clusters.users_without_ids()
        if u.startswith('@')
        )

    if screen_names:
        client = create_client(
            twitter_credentials=dict(poultry_config.items('twitter'))
        )

        response = client.get(
            'https://api.twitter.com/1.1/users/lookup.json',
            params={'screen_name': ','.join(screen_names)}
        )
        response.raise_for_status()

        for user in response.json():
            click.echo('@{screen_name} = {id}'.format(**user))


if __name__ == '__main__':
    cli()
