import logging
import json

import click
import click_log

from poultry import readline_dir

from .core import CharacterNGramExtractor, Collection

logger = logging.getLogger(__name__)
click_log.basic_config(logger)


@click.group()
@click_log.simple_verbosity_option(logger=logger)
def cli():
    pass


@cli.command()
@click.option('--source', default=None, help='Tweet source.')
@click.option('--topic-file', type=click.File(), default='topics.json')
@click.option('--ngram-length', default=3)
@click.option('--keep-spam', is_flag=True)
@click.option('--language', default='en')
@click.option('--extract-retweets', is_flag=True)
def point(source, extract_retweets, language, ngram_length, keep_spam, topic_file):
    topics = json.load(topic_file)
    topics = [topics[-22], topics[2]]

    tweets = readline_dir(source, extract_retweets=extract_retweets)
    if language:
        tweets = (t for t in tweets if t.parsed.get('lang', language) == language and (keep_spam or not t.is_spam))

    feature_extractor = CharacterNGramExtractor(length=ngram_length)
    collection = Collection(feature_extractor)

    queries = [t['title'] for t in topics]
    for q in queries:
        collection.append(q)

    seen_tweets = set()
    for tweet in tweets:
        if tweet.id in seen_tweets:
            continue
        seen_tweets.add(tweet.id)

        collection.append(tweet.text)

        distances = collection.distance(tweet.text, queries, metric='cosine').flatten()
        for topic, distance in zip(topics, distances):
            print(
                topic['topid'],
                'Q0',
                tweet.id,
                distance,
            )
