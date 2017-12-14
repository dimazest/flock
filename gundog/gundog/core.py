import string
import logging

from itertools import chain
from collections import deque

import numpy as np


logger = logging.getLogger(__name__)


class CharacterNGramExtractor:

    def __init__(self, features=string.ascii_lowercase + string.digits, length=3):
        self.all_features = set(features)
        self.all_features.add('')
        self.feature_map = {f: i for i, f in enumerate(features, start=1)}
        self.feature_map[''] = 0
        self.feature_map_len = len(self.feature_map)

        self.length = length

    def features(self, text):
        text = list(text.lower()) + [''] * (self.length - 1)

        window = np.zeros(self.length)
        result = np.zeros(len(text), dtype=np.int_)
        for i, char in enumerate(text):
            feature = self.feature_map.get(char)

            if feature is None:
                continue

            window = np.roll(window, 1)
            window[0] = feature

            result[i] = sum(f * self.feature_map_len ** i for i, f in enumerate(window))

        return result

    def __call__(self, text):
        return np.unique(self.features(text))


class Collection:

    def __init__(self, feature_extractor):
        self.feature_extractor = feature_extractor
        self.df = np.zeros(feature_extractor.feature_map_len ** feature_extractor.length, dtype=np.uint64)

    def append(self, text):
        features = self.feature_extractor(text)
        self.df[features] += 1

        return features

    def _idf(self, features):
        result = 1 / np.log1p(self.df[features])
        return result

    def distance(self, one, others, metric='cosine'):
        features = np.unique(np.concatenate((one, *others)))
        idf = self._idf(features)

        zeros = np.zeros_like(idf)
        one_idf = np.choose(np.isin(features, one), [zeros, idf])
        other_idfs = [np.choose(np.isin(features, other), [zeros, idf]) for other in others]

        return distances(one_idf, other_idfs, metric=metric)


def distances(a, bs, metric='cosine'):
    result = np.ones(len(bs), dtype=float)
    sqrt_a_a = np.sqrt(a @ a)
    for i, b in enumerate(bs):
        a_b = a @ b
        if a_b > 0:
            result[i] -= a_b / (sqrt_a_a * np.sqrt(b @ b))

    return result


def point(in_q, out_q, topics, qrels, negative_distance_threshold, ngram_length, pattern):

    feature_extractor = CharacterNGramExtractor(length=ngram_length)
    collection = Collection(feature_extractor)

    feedback = []
    retrieved_counts = {}
    position_in_pattern = {}
    last_missing_position = {}
    for topic in topics:
        query = topic['title']
        query_features  = collection.append(query)

        topid = topic['topid']
        feedback.append((query, topid, [query_features], []))
        retrieved_counts[topid] = 0
        position_in_pattern[topid] = 0
        last_missing_position[topid] = 0

    out_batch = []
    while True:
        batch = in_q.get()

        if batch is None:

            if out_batch:
                out_q.put(out_batch)

            break

        for tweet_text, tweet_id, tweet_created_at in batch:

            tweet_features = collection.append(tweet_text)

            for query, topid, positive, negative in feedback:

                distances_to_positive = collection.distance(tweet_features, positive)
                distance_to_query = distances_to_positive[0]
                distance_to_positive = distances_to_positive.min()

                distance_to_negative = collection.distance(tweet_features, negative).min() if negative else 1

                score = distance_to_positive / min(distance_to_negative, negative_distance_threshold)

                qrels_relevance = qrels.get((topid, tweet_id))
                retrieve = score < 1

                in_pattern = pattern is None or retrieved_counts[topid] + 1 in pattern.get(topid, set())
                if retrieve:
                    retrieved_counts[topid] += 1

                    if qrels_relevance is not None and in_pattern:
                        (positive if qrels_relevance else negative).append(tweet_features)

                    if pattern is not None and in_pattern:
                        position_in_pattern[topid] += 1
                        if qrels_relevance is None:
                            last_missing_position[topid] += 1
                            logger.warn(
                                'Missing judgment #%s (%s/%s in a pattern of %s) for topic %s, tweet %s.',
                                retrieved_counts[topid], last_missing_position[topid], position_in_pattern[topid], len(pattern[topid]), topid, tweet_id)
                        else:
                            logger.debug('Provided feedback for topic %s, tweet %s', topid, tweet_id)

                if retrieve or qrels_relevance is not None:
                    out_batch.append(
                        (
                            topid,
                            tweet_id,
                            distance_to_query,
                            distance_to_positive,
                            distance_to_negative,
                            score,
                            retrieve,
                            qrels_relevance,
                            len(positive),
                            len(negative),
                            tweet_created_at,
                            retrieved_counts[topid],
                        )
                    )

                if len(out_batch) > 1:
                    out_q.put(out_batch)
                    out_batch = []

