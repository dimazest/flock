import click
import click_log

from flock.__main__ import create_session
from flock.model import metadata

from flock_web.app import create_app
import flock_web.model as model


@click.group()
@click_log.simple_verbosity_option()
@click_log.init('flock-web')
def cli():
    pass


@cli.command()
@click.argument('filename')
def runserver(filename):
    app = create_app(filename)
    app.run()


@cli.command()
@click.option('--session', default='postgresql:///twitter', callback=create_session)
def initdb(session):
    metadata.create_all(tables=[model.User.__table__])


if __name__ == '__main__':
    cli()
