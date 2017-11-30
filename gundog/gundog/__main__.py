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
@click.option('--keep-retweets', is_flag=True)
@click.option('--qrels-file', type=click.File())
@click.option('--negative-distance-threshold', default=0.8)
def point(source, extract_retweets, language, ngram_length, keep_spam, topic_file, keep_retweets, qrels_file, negative_distance_threshold):
    topics = json.load(topic_file)
    topics = [topics[-22], topics[2]]

    qrels = {}
    for line in qrels_file:
        rts_id, _, tweet_id, judgment = line.split()
        tweet_id = int(tweet_id)
        judgment = int(judgment)

        if judgment >= 0:
            qrels[rts_id, tweet_id] = judgment

    tweets = readline_dir(source, extract_retweets=extract_retweets)
    if language:
        tweets = (
            t for t in tweets
            if t.parsed.get('lang', language) == language
            and (keep_spam or not t.is_spam)
            and (keep_retweets or not t.parsed.get('retweeted_status'))
        )

    feature_extractor = CharacterNGramExtractor(length=ngram_length)
    collection = Collection(feature_extractor)

    feedback = {}
    queries = []
    for topic in topics:
        query = topic['title']

        queries.append(query)
        collection.append(query)
        feedback[topic['topid']] = [query], []

    seen_tweets = set()
    for tweet in tweets:
        if tweet.id in seen_tweets:
            continue
        seen_tweets.add(tweet.id)

        collection.append(tweet.text)

        distances_to_queries = collection.distance(tweet.text, queries, metric='cosine').flatten()
        for topic, distance_to_query in zip(topics, distances_to_queries):

            positive, negative = feedback[topic['topid']]

            distance_to_positive = min(collection.distance(tweet.text, positive).flatten())
            distance_to_negative = min(collection.distance(tweet.text, negative).flatten()) if negative else negative_distance_threshold
            score = distance_to_positive / min(distance_to_negative, negative_distance_threshold)

            retrieve = score < 1
            if retrieve:
                relevant = qrels.get((topic['topid'], tweet.id))
                if relevant is not None:
                    (positive if relevant else negative).append(tweet.text)
            else:
                relevant = None

            print(
                topic['topid'],
                tweet.id,
                distance_to_query,
                distance_to_positive,
                distance_to_negative,
                score,
                retrieve,
                len(positive),
                len(negative),
                tweet.created_at,
                sep=',',
            )
