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
        text = text.lower()

        features = filter(None, (self.feature_map.get(f) for f in text))
        features = chain(features, [0] * (self.length - 1))

        window = deque([0] * (self.length - 1), self.length)
        for current in features:
            window.append(current)
            reversed_window = tuple(reversed(window))
            for w in [reversed_window]:
                yield sum(f * self.feature_map_len ** i for i, f in enumerate(w))

    def __call__(self, text):
        return np.fromiter(set(self.features(text)), int)


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
        if isinstance(others, str):
            others = [others]

        return distances(
            self[one],
            list(map(self.__getitem__, others)),
            metric=metric,
        )


def distances(a, bs, metric='cosine'):
    result = np.empty_like(bs, dtype=float)
    for i, b in enumerate(bs):
        result[i] = (a @ b) / (np.sqrt(a @ a) * np.sqrt(b @ b))

    return result


def point(in_q, out_q, topics, qrels, negative_distance_threshold, ngram_length):

    feature_extractor = CharacterNGramExtractor(length=ngram_length)
    collection = Collection(feature_extractor)

    queries = []
    feedback = []
    for topic in topics:
        query = topic['title']
        queries.append(query)
        collection.append(query)

        feedback.append((topic['topid'], [query], []))

    while True:
        batch = in_q.get()

        if batch is None:
            break


        for tweet_text, tweet_id, tweet_created_at in batch:
            out_batch = []

            collection.append(tweet_text)

            distance_to_queries = collection.distance(tweet_text, queries, metric='cosine').flatten()
            for (topid, positive, negative), distance_to_query in zip(feedback, distance_to_queries):

                distance_to_positive = collection.distance(tweet_text, positive).min()
                distance_to_negative = collection.distance(tweet_text, negative).min() if negative else negative_distance_threshold

                if distance_to_negative > 0:
                    score = min(distance_to_positive / min(distance_to_negative, negative_distance_threshold), 2)
                else:
                    score = 2

                retrieve = score < 1
                if retrieve:
                    relevant = qrels.get((topid, tweet_id))
                    if relevant is not None:
                        (positive if relevant else negative).append(tweet_text)
                else:
                    relevant = None

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
                    )
                )

            out_q.put(out_batch)
