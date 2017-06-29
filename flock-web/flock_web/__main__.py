import logging

import click
import click_log

from flock.__main__ import create_session
from flock.model import metadata

from flock_web.app import create_app
import flock_web.model as fw_model


logger = logging.getLogger(__name__)


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
    metadata.create_all(
        tables=[
            o.__table__ for o in [
                fw_model.User, fw_model.Topic, fw_model.TopicQuery, fw_model.RelevanceJudgment, fw_model.TaskResult, fw_model.UserAction, fw_model.TopicQuestionnaire,
            ]
        ]
    )


@cli.command()
@click.option('--session', default='postgresql:///twitter', callback=create_session)
@click.option('--collection')
@click.option('--assr_topic_file', type=click.File())
def insert_eval_topics(session, collection, assr_topic_file):

    for line in assr_topic_file:
        rts_topic_id, assessor_user_name = line.split()
        rts_topic_id = f'RTS{rts_topic_id}'

        assessor = session.query(fw_model.User).filter_by(first_name=assessor_user_name).one_or_none()

        if assessor is None:
            assessor = fw_model.User(first_name=assessor_user_name, last_name='hi')
            session.add(assessor)

            session.flush()
            logger.warning('A new user %s is created.', assessor_user_name)

        session.add(
            fw_model.Topic(
                rts_id=rts_topic_id,
                title=rts_topic_id,
                user=assessor,
            )
        )

    session.commit()


if __name__ == '__main__':
    cli()
