import logging
import json
import sys
import random
import multiprocessing as mp

import click
import click_log

from . import core

logger = logging.getLogger(__name__)
click_log.basic_config(logger)


@click.group()
@click_log.simple_verbosity_option(logger=logger)
def cli():
    pass


def printer(q):
    while True:
        batch = q.get()

        if batch is None:
            break

        for item in batch:
            print(*item, sep=',')


@cli.command()
@click.option('--source', default=None, help='Tweet source.')
@click.option('--topic-file', type=click.File(), default='topics.json')
@click.option('--ngram-length', default=3)
@click.option('--keep-spam', is_flag=True)
@click.option('--language', default=None, type=str)
@click.option('--extract-retweets', is_flag=True)
@click.option('--keep-retweets', is_flag=True)
@click.option('--qrels-file', type=click.File())
@click.option('--negative-distance-threshold', default=0.8)
@click.option('--sample', default=1.0)
def point(source, extract_retweets, language, ngram_length, keep_spam, topic_file, keep_retweets, qrels_file, negative_distance_threshold, sample):
    topics = json.load(topic_file)
    #topics = [topics[-22], topics[2]]

    assert keep_spam

    judged_tweets = set()
    qrels = {}
    for line in qrels_file:
        rts_id, _, tweet_id, judgment = line.split()
        tweet_id = int(tweet_id)
        judgment = int(judgment)

        if judgment >= 0:
            judged_tweets.add(tweet_id)
            qrels[rts_id, tweet_id] = judgment

    tweets = map(json.loads, sys.stdin)

    tweets = (
        t for t in tweets
        if 'id' in t and (
            t['id'] in judged_tweets or (
                (t.get('lang', language) == language)
                and (keep_spam or not t.is_spam)
                and (keep_retweets or not t.get('retweeted_status'))
                and (random.random() < sample)
            )
        )
    )

    printer_q = mp.Queue(maxsize=1)
    printer_p = mp.Process(target=printer, args=(printer_q,))
    printer_p.start()

    workers_num = max(mp.cpu_count() - 2, 1)
    topics_by_worker = {}
    for i, topic in enumerate(topics):
        topics_by_worker.setdefault((i % workers_num), []).append(topic)

    workers = []
    for topics in topics_by_worker.values():

        in_q = mp.Queue(maxsize=1)
        worker = mp.Process(
            target=core.point,
            kwargs=dict(
                in_q=in_q,
                out_q=printer_q,
                topics=topics,
                qrels=qrels,
                negative_distance_threshold=negative_distance_threshold,
                ngram_length=ngram_length,
            ),
        )
        worker.start()

        workers.append((topic['topid'], in_q, worker))

    try:
        batch = []
        for tweet in tweets:

            task = tweet.get('long_text') or tweet['text'], tweet['id'], tweet['created_at']
            batch.append(task)

            if len(batch) > 1000:
                for _, in_q, _ in workers:
                    in_q.put(batch)

                batch = []
        else:
            if batch:
                for _, in_q, _ in workers:
                    in_q.put(batch)

    finally:
        for _, in_q, w in workers:
            in_q.put(None)
            in_q.close()
            in_q.join_thread()

            w.join()

        printer_q.put(None)
        printer_q.close()
        printer_q.join_thread()

        printer_p.join()
