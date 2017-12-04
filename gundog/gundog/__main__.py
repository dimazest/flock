import logging
import json
import multiprocessing as mp

import click
import click_log

from poultry import readline_dir

from . import core

logger = logging.getLogger(__name__)
click_log.basic_config(logger)


@click.group()
@click_log.simple_verbosity_option(logger=logger)
def cli():
    pass


def printer(q):
    while True:
        item = q.get()

        if item is None:
            break

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
def point(source, extract_retweets, language, ngram_length, keep_spam, topic_file, keep_retweets, qrels_file, negative_distance_threshold):
    topics = json.load(topic_file)
    #topics = [topics[-22], topics[2]]

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
            if (language is not None or t.parsed.get('lang', language) == language)
            and (keep_spam or not t.is_spam)
            and (keep_retweets or not t.parsed.get('retweeted_status'))
        )

    printer_q = mp.Queue(maxsize=100)
    printer_p = mp.Process(target=printer, args=(printer_q,))
    printer_p.start()

    workers_num = max(mp.cpu_count() - 2, 1)
    topics_by_worker = {}
    for i, topic in enumerate(topics):
        topics_by_worker.setdefault((i % workers_num), []).append(topic)

    workers = []
    for topics in topics_by_worker.values():

        in_q = mp.Queue(maxsize=100)
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
        for tweet in tweets:
            for _, in_q, _ in workers:
                in_q.put((tweet.text, tweet.id, tweet.created_at))
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
