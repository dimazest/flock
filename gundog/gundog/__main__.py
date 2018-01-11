import logging
import json
import sys
import random
import multiprocessing as mp
import datetime as dt

import click
import click_log

import zmq

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

        sys.stdout.flush()


def is_spam(tweet, spam_filter):
    if spam_filter is None or spam_filter == 'none':
        return False
    else:
        assert spam_filter == 'basic'

        text = tweet.get('long_text') or tweet.get('text')

        if text is None or len(text) < 30:
            return False

        tokens = text.split()

        entities = tweet.get('entities', {})
        hashtags = entities.get('hashtags', [])
        user_mentions = entities.get('user_mentions', [])
        urls = entities.get('urls', [])

        return (
            len(tokens) < 10 and
            len(hashtags) > 3 and
            len(user_mentions) > 2 and
            len(urls) > 1
        )


def parse_tweet_json(sample=1, spam_filter=None):
    for line in sys.stdin:
        try:
            tweet = json.loads(line)
        except json.JSONDecodeError:
            pass
        else:

            if random.random() > sample:
                continue

            if is_spam(tweet, spam_filter=spam_filter):
                continue

            yield tweet



@cli.command()
@click.option('--source', default=None, help='Tweet source.')
@click.option('--topic-file', type=click.File(), default='topics.json')
@click.option('--ngram-length', default=3)
@click.option('--spam-filter', type=str)
@click.option('--language', default=None, type=str)
@click.option('--extract-retweets', is_flag=True)
@click.option('--keep-retweets', is_flag=True)
@click.option('--feedback-file')
@click.option('--negative-distance-threshold', default=0.8)
@click.option('--sample', default=1.0)
@click.option('--topic-filter', type=click.File())
@click.option('--workers', '-j', default=max(mp.cpu_count() - 2, 1), envvar='GUNDOG_WORKERS')
@click.option('--pattern-file', type=click.File())
@click.option('--pattern-mode', type=click.Choice(['exact', 'amount']), default='exact')
def point(source, extract_retweets, language, ngram_length, spam_filter, topic_file, keep_retweets, feedback_file, negative_distance_threshold, sample, topic_filter, workers, pattern_file, pattern_mode):
    random.seed(30)

    topic_filter = set(l.strip() for l in topic_filter)
    topics = [t for t in json.load(topic_file) if t['topid'] in topic_filter]

    pattern = {} if pattern_file is not None else None
    if pattern is not None:
        for line in pattern_file:
            rts_id, _, _, _, _, _, retrieve, qrels_relevance, _, _, _, position = line.split(',')
            retrieve = retrieve == 'True'
            position = int(position)

            if retrieve and qrels_relevance != 'None':
                pattern.setdefault(rts_id, set()).add(position)

    if '://' in feedback_file:
        qrels = feedback_file
    else:
        with open(feedback_file) as f:
            qrels = {}
            for line in f:
                rts_id, _, tweet_id, judgment, timestamp = line.split()
                tweet_id = int(tweet_id)
                judgment = int(judgment)
                timestamp = int(timestamp)

                if judgment >= 0:
                    qrels[rts_id, tweet_id] = 1 <= judgment <= 2

    tweets = (
        t for t in parse_tweet_json(sample=sample, spam_filter=spam_filter)
        if 'id' in t and (
            (
                (t.get('lang', language) == language)
                and (keep_retweets or not t.get('retweeted_status'))
            )
        )
    )

    printer_q = mp.Queue(maxsize=1)
    printer_p = mp.Process(target=printer, args=(printer_q,))
    printer_p.start()

    workers_num = max(workers, 1)
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
                pattern=pattern,
                pattern_mode=pattern_mode,
            ),
        )
        worker.start()

        workers.append((topic['topid'], in_q, worker))

    try:
        batch = []
        for tweet in tweets:

            task = tweet.get('long_text') or tweet['text'], tweet['id'], dt.datetime.strptime(tweet['created_at'], '%a %b %d %H:%M:%S %z %Y').isoformat()
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

@cli.command('prepare-feedback')
@click.option('--feedback-file', type=click.File())
@click.option('--complete-file', type=click.File())
@click.option('--mode', type=click.Choice(['majority', 'some', 'all']))
@click.option('--equivalence-file', type=click.File())
def prepare_feedback(feedback_file, mode, complete_file, equivalence_file):
    feedback = {}

    tweet_ids = set()
    for line in complete_file:
        topic, _, tweet_id = line.split()[:3]
        tweet_id = int(tweet_id)
        tweet_ids.add((topic, tweet_id))


    tweet_cluster = {}
    cluster_tweet = {}
    if equivalence_file is not None:
        for line in equivalence_file:
            topic, cluster, tweet_id = line.split()
            tweet_id = int(tweet_id)

            tweet_cluster[topic, tweet_id] = cluster
            cluster_tweet.setdefault(cluster, []).append(tweet_id)

    cluster_judgments = {}
    for line in feedback_file:
        values = line.split()

        if len(values) == 5:
            topic, user, tweet_id, judgment, timestamp = values
        else:
            topic, user, tweet_id, judgment = values
            timestamp = 0

        tweet_id = int(tweet_id)
        judgment = int(judgment)
        timestamp = int(timestamp)

        if (topic, tweet_id) in tweet_ids:
            feedback.setdefault(topic, {}).setdefault(tweet_id, []).append((user, judgment, timestamp))

            cluster = tweet_cluster.get((topic, tweet_id))
            if cluster is not None:
                cluster_judgments.setdefault(cluster, []).append((user, judgment, timestamp))

                for t in cluster_tweet[cluster]:
                    feedback[topic].setdefault(t, [])

    for topic, topic_data in feedback.items():
        for tweet_id, judgments  in topic_data.items():

            relevant = 0
            non_relevant = 0

            cluster = tweet_cluster.get((topic, tweet_id))
            if cluster is not None:
                judgments = cluster_judgments[cluster]

            for _, j, _ in judgments:
                if j == 0:
                    non_relevant += 1
                elif 1 <= j <= 2:
                    relevant += 1

            if not relevant and not non_relevant:
                continue

            judgment = None
            if mode == 'majority' and relevant != non_relevant:
                judgment = 1 if relevant > non_relevant else 0
            elif mode == 'all':
                judgment = 1 if not non_relevant else 0
            elif mode == 'some':
                judgment = 1 if relevant else 0

            if judgment is not None:
                print(topic, mode, tweet_id, judgment, 0)


@cli.command()
@click.option('--address', default='ipc://gundog')
@click.option('--qrels-file', type=click.File('r+'))
def hunter(address, qrels_file):

    qrels = {}
    for line in qrels_file:
        topid, _, tweet_id, relevance = line.split()
        tweet_id = int(tweet_id)
        relevance = int(relevance)

        qrels[topid, tweet_id] = relevance

    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(address)

    while True:
        message = socket.recv_json()

        topic = message['topic']
        tweet = message['tweet']

        topid = topic['topid']
        tweet_id = tweet['id']

        score = message['score']['score']
        distance_to_query = message['score']['distance_to_query']

        print(
            f'{topic["narrative"]}',
            f'{topic["description"]}',
            '',
            f'{topid}: {topic["title"]}',
            f'({distance_to_query:.3f}, {score:.3f}) {tweet["text"]}',
            sep='\n'
        )

        relevance = qrels.get((topic['topid'], tweet['id']))
        if relevance is None:
            relevance = input('Your reply: ').lower() not in ('', ' ', '0', 'f', 'n')
            qrels[topid, tweet_id] = relevance

            print(topid, 'Q0', tweet_id, 1 if relevance else 0, file=qrels_file)
            qrels_file.flush()
        else:
            print('Your recorded reply: {}'.format(relevance))

        result = {
            'topid': topic['topid'],
            'tweet_id': tweet['id'],
            'relevance': bool(relevance),
        }

        socket.send_json(result)
