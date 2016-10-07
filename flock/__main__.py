import logging

import click
import click_log

from poultry import readline_dir
from sqlalchemy.dialects import postgresql as pg

from .model import tweet_table, metadata


logger = logging.getLogger(__name__)


def create_session(ctx, param, value):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(value)
    metadata.bind = engine
    Session = sessionmaker(bind=engine)

    return Session()


@click.group()
@click_log.simple_verbosity_option()
@click_log.init('flock')
def cli():
    pass


@cli.command()
@click.option('--session', default='postgresql://localhost/twitter', callback=create_session)
def initdb(session):
        metadata.create_all()


@cli.command()
@click.option('--session', default='postgresql://localhost/twitter', callback=create_session)
def dropdb(session):
        metadata.drop_all()


@cli.command()
@click.option('--source', default=None, help='Tweet source.')
@click.option('--session', default='postgresql://localhost/twitter', callback=create_session)
def insert(source, session):
    for i, t in enumerate(readline_dir(source), start=1):
        if (i % 100000) == 0:
            logger.debug('Processed %s tweets, it\'s time to flush.', i)
            session.flush()

        stmt = pg.insert(tweet_table).values(
            _id=t.id,
            tweet=t.parsed,
        ).on_conflict_do_nothing(index_elements=['_id'])

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


def create_expander(ctx, param, value):
    from flock_conf.expander import Expander

    return Expander.from_file(value)


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
