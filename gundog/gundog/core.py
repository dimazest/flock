import string

from itertools import chain
from collections import deque

import numpy as np

from sklearn.metrics.pairwise import pairwise_distances


class CharacterNGramExtractor:

    def __init__(self, features=string.ascii_lowercase + string.digits, length=3):
        self.all_features = set(features)
        self.all_features.add('')
        self.feature_map = {f: i for i, f in enumerate(features, start=1)}
        self.feature_map[''] = 0

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
                yield sum(f * len(self.feature_map) ** i for i, f in enumerate(w))

    def __call__(self, text):
        return np.fromiter(set(self.features(text)), int)


class Collection:

    def __init__(self, feature_extractor):
        self.feature_extractor = feature_extractor
        self.df = np.zeros(len(feature_extractor.feature_map) ** feature_extractor.length, dtype=np.uint64)

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

    def distance(self, one, another, metric='cosine'):
        if isinstance(one, str):
            one = [one]
        if isinstance(another, str):
            another = [another]

        return pairwise_distances(
            list(map(self.__getitem__, one)),
            list(map(self.__getitem__, another)),
            metric=metric,
        )


def point(in_q, out_q, topic, feedback, negative_distance_threshold, ngram_length):

    feature_extractor = CharacterNGramExtractor(length=ngram_length)
    collection = Collection(feature_extractor)

    query = topic['title']
    collection.append(query)

    positive, negative = [query], []

    while True:
        task = in_q.get()

        if task is None:
            #out_q.put((None, topic['topid']))
            break

        tweet_text, tweet_id, tweet_created_at = task

        collection.append(tweet_text)

        distance_to_query = np.asscalar(collection.distance(tweet_text, query, metric='cosine'))
        distance_to_positive = collection.distance(tweet_text, positive).min()
        distance_to_negative = collection.distance(tweet_text, negative).min() if negative else negative_distance_threshold

        score = distance_to_positive / min(distance_to_negative, negative_distance_threshold)

        retrieve = score < 1
        if retrieve:
            relevant = feedback.get(tweet_id)
            if relevant is not None:
                (positive if relevant else negative).append(tweet_text)
        else:
            relevant = None

        out_q.put(
            (
                topic['topid'],
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
