import click
import click_log

from flock_web.app import create_app


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


if __name__ == '__main__':
    cli()
