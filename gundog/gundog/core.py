import string

from itertools import chain
from collections import deque

import numpy as np


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

        return self._idf(features)

    def __getitem__(self, key):
        features = self.feature_extractor(key)
        return self._idf(features)

    def _idf(self, features):
        result = np.zeros(self.df.shape[0])
        result[features] = 1 / np.log(self.df[features] + 1)
        return result

    def distance(self, one, others, metric='cosine'):
        if isinstance(one, str):
            one = self[one]

        if isinstance(others, str):
            others = [others]

        return distances(
            one,
            list(map(self.__getitem__, others)),
            metric=metric,
        )


def distances(a, bs, metric='cosine'):
    result = np.empty(len(bs), dtype=float)
    for i, b in enumerate(bs):
        result[i] = 1 - (a @ b) / (np.sqrt(a @ a) * np.sqrt(b @ b))

    return result


def point(in_q, out_q, topics, qrels, negative_distance_threshold, ngram_length):

    feature_extractor = CharacterNGramExtractor(length=ngram_length)
    collection = Collection(feature_extractor)

    feedback = []
    retrieved_counts = {}
    for topic in topics:
        query = topic['title']
        collection.append(query)

        feedback.append((query, topic['topid'], [query], []))
        retrieved_counts[topic['topid']] = 0

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

                qrels_relevance = qrels.get((topid, tweet_id))
                if qrels_relevance is None and distance_to_positive > negative_distance_threshold:
                    continue

                distance_to_negative = collection.distance(tweet_features, negative).min() if negative else 1

                score = distance_to_positive / min(distance_to_negative, negative_distance_threshold)

                retrieve = score < 1
                if retrieve:
                    retrieved_counts[topid] += 1

                if qrels_relevance is not None:
                    if retrieve:
                        (positive if qrels_relevance else negative).append(tweet_text)

                    out_batch.append(
                        (
                            topid,
                            tweet_id,
                            distance_to_query,
                            distance_to_positive,
                            distance_to_negative,
                            score,
                            retrieve,
                            len(positive),
                            len(negative),
                            tweet_created_at,
                            retrieved_counts[topid],
                        )
                    )

                if len(out_batch) > 1:
                    out_q.put(out_batch)
                    out_batch = []

