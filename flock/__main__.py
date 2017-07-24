import logging
import json
import itertools

import click
import click_log

from poultry import readline_dir

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from . import model


try:
    import psycopg2
except ImportError:
    # Fall back to psycopg2cffi
    from psycopg2cffi import compat
    compat.register()

logger = logging.getLogger(__name__)


tables = [table for name, table in model.metadata.tables.items() if name not in ('tweet_representative', 'filtered_tweets', 'feature_scores', 'feature_counts')]


def create_session(ctx, param, value):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(value, client_encoding='utf8')

    sa.orm.configure_mappers()

    model.metadata.bind = engine
    Session = sessionmaker(bind=engine)

    return Session()


@click.group()
@click_log.simple_verbosity_option()
@click_log.init('flock')
def cli():
    pass


@cli.command()
@click.option('--session', default='postgresql:///twitter', callback=create_session)
def initdb(session):

    model.metadata.create_all(tables=tables)

    # for index in model.indexes:
    #     try:
    #         index.create(session.bind)
    #     except ProgrammingError:
    #         # XXX: log error
    #         pass


@cli.command()
@click.option('--session', default='postgresql:///twitter', callback=create_session)
def dropdb(session):
        model.metadata.drop_all(tables=tables)


def create_expander(ctx, param, value):
    from flock_conf.expander import Expander

    return Expander.from_file(value)


@cli.command()
@click.option('--clusters', default='clusters.cfg', callback=create_expander)
@click.option('--source', '-s', multiple=True)
def export(clusters, source):
    clusters = clusters.reverse_user_labels()

    template = (
        "if {conditions}:\n"
        "    source = '{source}'"
    )

    result = '\n\n'.join(
        template.format(
            source=s,
            conditions=' or '.join("'{} ' in ttext".format(u) for u in users)
        )
        for s, users in clusters.items() if not source or s in source
    )

    print(result)


@cli.command()
@click.option('--source', default=None, help='Tweet source.')
@click.option('--session', default='postgresql:///twitter', callback=create_session)
@click.option('--clusters', default='clusters.cfg', callback=create_expander)
@click.option('--collection', default='default')
@click.option('--extract-retweets', is_flag=True)
@click.option('--language', default=None)
def insert(source, session, clusters, collection, extract_retweets, language):
    from . import features

    user_labels = clusters.user_labels()
    rows = []

    stmt = pg.insert(model.Tweet.__table__)
    stmt = stmt.on_conflict_do_nothing(
        index_elements=['tweet_id', 'collection'],
    )
    # stmt = stmt.on_conflict_do_update(
    #     index_elements=['tweet_id', 'collection'],
    #     set_={
    #         'features': stmt.excluded.features,
    #     }
    # )

    tweets = readline_dir(source, extract_retweets=extract_retweets)
    if language:
        tweets = (t for t in tweets if t.parsed.get('lang', language) == language)
    rows_tweets = (
        features.doc2vec_features(
            features.filter_features(
                features.tokenizer_features(
                    features.basic_features(tweets, user_labels)
                )
            )
        )
    )

    if collection == 'lv':
        rows_tweets = features.lv_features(rows_tweets)

    for i, (row, tweet) in enumerate(rows_tweets, start=1):
        row['collection'] = collection

        rows.append(row)

        if (i % 10000) == 0:
            logger.debug('Processed %s tweets.', i)

            session.execute(stmt, rows)
            rows[:] = []
    else:
        if rows:
            session.execute(stmt, rows)

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


@cli.command()
@click.option('--session', default='postgresql:///twitter', callback=create_session)
@click.option('--collection', default='2015-04-04.through.2014-04-10_EN')
@click.option('--index-size', default=10*1000)
@click.option('--probability-index-near-match', default=0.1)
def find_near_matches(session, collection, index_size, probability_index_near_match):
    from simhash import Simhash, SimhashIndex
    logging.getLogger().setLevel(logging.CRITICAL)

    tweet_id_simhash_value = session.execute(
        sa.select([model.Tweet.tweet_id, model.Tweet.features['filter','simhash']])
        .where(model.Tweet.collection == collection)
    )

    simhash_index = SimhashIndex([], k=7)

    insert_relation_stmt = pg.insert(model.relation)
    # insert_tweet_near_matches_stmt = insert_tweet_near_matches_stmt.on_conflict_do_update(
    #     index_elements=['tweet_id', 'collection'],
    #     set_={
    #         'earliest_near_match_id': insert_tweet_near_matches_stmt.excluded.earliest_near_match_id
    #     }
    # )

    indexed_tweet_ids = []

    for i, (tweet_id, simhash_value) in enumerate(tweet_id_simhash_value):

        if (i % 100000) == 1000:
            logger.info('Processed %s tweets. Committing.', i)
            session.commit()

        simhash = Simhash(simhash_value)

        near_matches_ids = simhash_index.get_near_dups(simhash)

        if not near_matches_ids:
            simhash_index.add(tweet_id, simhash)
            indexed_tweet_ids.append((tweet_id, simhash))

            if len(indexed_tweet_ids) > index_size:
                simhash_index.delete(*indexed_tweet_ids.pop(0))

        if near_matches_ids:
            near_match_id = min(near_matches_ids)

            logger.debug('A near match %s for tweet %s', near_match_id, tweet_id)
            session.execute(
                insert_relation_stmt.values(
                    [(tweet_id, collection, 'near_match', near_match_id)]
                )
            )

    session.commit()


@cli.command()
@click.option('--session', default='postgresql:///twitter', callback=create_session)
@click.option('--collection')
@click.argument('story_file', type=click.File())
def insert_stories(session, collection, story_file):
    stories = json.load(story_file)

    insert_stmt = pg.insert(model.tweet_story)

    for story_id, data in stories['topics'].items():
        title = data['topic']
        tweet_ids = itertools.chain.from_iterable(data['clusters'])

        story = model.Story(story_id=story_id, collection=collection, title=title)
        session.add(story)
        session.flush()

        for tweet_rank, tweet_id in enumerate(tweet_ids):
            tweet_id = int(tweet_id)

            tweet = session.query(model.Tweet).get((tweet_id, collection))

            for id_ in [tweet_id]: # + tweet.features.get('retweeted_status__id', []):
                session.execute(
                    insert_stmt.values(
                        [(id_, collection, story._id, tweet_rank)]
                    ),
                )

    session.commit()


if __name__ == '__main__':
    cli()
