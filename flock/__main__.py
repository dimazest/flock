import logging

import click
import click_log

from poultry import readline_dir
from sqlalchemy.dialects import postgresql as pg

from .model import Tweet

logger = logging.getLogger(__name__)



def create_session(ctx, param, value):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(value)
    Session = sessionmaker(bind=engine)
    return Session()


@click.group()
@click_log.simple_verbosity_option()
@click_log.init('flock')
def cli():
    pass


@cli.command()
@click.option('--source', default=None, help='Tweet source.')
@click.option('--session', default='postgresql://localhost/twitter', callback=create_session)
def insert(source, session):
    for i, t in enumerate(readline_dir(source), start=1):

        if (i % 100000) == 0:
            logger.debug('Processed %s tweets, it\'s time to flush.', i)
            session.flush()

        stmt = pg.insert(
            Tweet.__table__,
        ).values(
            id=t.id,
            tweet=t.parsed,
        ).on_conflict_do_nothing()

        session.execute(stmt)
    else:
        session.commit()
        try:
            i
        except UnboundLocalError:
            pass
        else:
            logger.info('Processed %s tweets.', i)


if __name__ == '__main__':
    cli()
