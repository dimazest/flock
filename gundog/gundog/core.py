import string
import math

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

        window = (0, ) * self.length
        result = [0] * len(text)
        for i, char in enumerate(text):
            feature = self.feature_map.get(char)

            if feature is None:
                continue

            window = feature, *window[:-1]

            result[i] = sum(f * self.feature_map_len ** i for i, f in enumerate(window))

        return result

    def __call__(self, text):
        return set(self.features(text))


class Collection:

    def __init__(self, feature_extractor):
        self.feature_extractor = feature_extractor
        self.df = [0] * feature_extractor.feature_map_len ** feature_extractor.length

    def append(self, text):
        features = self.feature_extractor(text)
        for feature in features:
            self.df[feature] += 1

        return features

    def __getitem__(self, key):
        features = self.feature_extractor(key)
        return self._idf(features)

    def _idf(self, features):
        result = [0] * len(self.df)
        for feature in features:
            result[feature] = 1 / math.log(self.df[feature] + 1)
        return result

    def distance(self, one, others, metric='cosine'):
        return distances(self._idf(one), [self._idf(o) for o in others], metric=metric)


def dot(A, B):
    assert len(A) == len(B)
    return sum(a * b for a, b in zip(A, B))


def distances(a, bs, metric='cosine'):
    result = [0.0] * len(bs)
    for i, b in enumerate(bs):
        result[i] = 1 - (dot(a, b)) / (math.sqrt(dot(a, a)) * math.sqrt(dot(b, b)))

    return result


def point(in_q, out_q, topics, qrels, negative_distance_threshold, ngram_length):

    feature_extractor = CharacterNGramExtractor(length=ngram_length)
    collection = Collection(feature_extractor)

    feedback = []
    retrieved_counts = {}
    for topic in topics:
        query = topic['title']
        query_features  = collection.append(query)

        feedback.append((query, topic['topid'], [query_features], []))
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
                distance_to_positive = min(distances_to_positive)

                distance_to_negative = min(collection.distance(tweet_features, negative)) if negative else 1

                score = distance_to_positive / min(distance_to_negative, negative_distance_threshold)

                qrels_relevance = qrels.get((topid, tweet_id))
                retrieve = score < 1
                if retrieve:
                    retrieved_counts[topid] += 1

                    if qrels_relevance is not None:
                        (positive if qrels_relevance else negative).append(tweet_features)

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

