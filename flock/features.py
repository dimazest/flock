from itertools import chain
from urllib.parse import urlparse


def basic_features(tweets, user_labels):

    for tweet in tweets:

        features = dict()

        features['screen_names'] = sorted(
            user_labels.get(tweet.parsed['user']['id'], [tweet.screen_name])
        )

        features['user_info'] = {
             'screen_name': tweet.screen_name,
             'screen_name_id': tweet.parsed['user']['id']
         }

        features['user_mentions'] = sorted(
            chain.from_iterable(
                user_labels.get(mention['id'], [mention['screen_name']])
                for mention in tweet.parsed['entities']['user_mentions']
            )
        )

        features['user_mentions_ids'] = [
            {
                'id': mention['id'],
                'screen_name': mention['screen_name'],
                'tracked': mention['id'] in user_labels,
            }
            for mention in tweet.parsed['entities']['user_mentions']
        ]

        features['urls'] = [
            url['expanded_url'] for url in tweet.parsed['entities']['urls']
        ]

        features['hostnames'] = [
            urlparse(url).hostname for url in features['urls']
        ]

        features['hashtags'] = sorted(
            ht['text'].lower()
            for ht in tweet.parsed['entities']['hashtags']
        )

        if 'lang' in tweet.parsed:
            features['languages'] = [tweet.parsed['lang']]

        retweeted_status = tweet.parsed.get('retweeted_status', None)
        features['is_retweet'] = [str(bool(retweeted_status))]
        if retweeted_status:
            retweeted_status__user = retweeted_status['user']
            features['retweeted_status__user__screen_names'] = sorted(
                user_labels.get(retweeted_status__user['id'], [retweeted_status__user['screen_name']])
            )
            features['retweeted_status__id'] = [retweeted_status['id']]

        in_reply_to_user_id = tweet.parsed.get('in_reply_to_user_id', None)
        if in_reply_to_user_id:
            features['in_reply_to_screen_names'] = sorted(
                user_labels.get(in_reply_to_user_id, [tweet.parsed['in_reply_to_screen_name']])
            )

        features['repr'] = {
            'text': tweet.parsed['text'],
            'user__name': tweet.parsed['user']['screen_name'],
            'user__screen_name': tweet.parsed['user']['screen_name'],
            'lang': tweet.parsed.get('lang', None),
        }

        row = {
            'tweet_id': tweet.id,
            'text': tweet.parsed['text'],
            'features': features,
            'created_at': tweet.created_at,
        }

        yield row, tweet


def tokenizer_features(features_tweets):
    import sys
    sys.path.append('src/ark-twokenize-py')

    from twokenize import tokenizeRawTweetText

    for row, tweet in features_tweets:
        row['features']['tokenizer'] = {
            'tokens': tokenizeRawTweetText(tweet.parsed['text'].lower()),
            'tokens_without_entities': tokenizeRawTweetText(tweet.text_without_entities.lower()),
        }

        yield row, tweet


def filter_features(features_tweets):
    """Extract features that are used to filter out useless tweets."""
    from simhash import Simhash

    for row, tweet in features_tweets:

        row['features']['filter'] = {
            'token_count': len(row['features']['tokenizer']['tokens']),
            'token_without_entities_count': len(row['features']['tokenizer']['tokens_without_entities']),
            'simhash': Simhash(row['features']['tokenizer']['tokens_without_entities']).value,
            'is_retweet': bool(tweet.parsed.get('retweeted_status', False)),
            **{
                '{}_count'.format(entity): len(tweet.parsed['entities'][entity]) for entity in ('hashtags', 'urls', 'user_mentions')
            }
        }

        row['features']['simhash'] = [str(row['features']['filter']['simhash'])]

        yield row, tweet


def doc2vec_features(features_tweets):
    for row, tweet in features_tweets:

        row['features']['doc2vec'] = {
            'words': row['features']['tokenizer']['tokens'],
            'tags': [
                'id:{}'.format(row['tweet_id']),
                *['@{}'.format(n) for n in row['features']['user_mentions']],
                *['#{}'.format(ht) for ht in row['features']['hashtags']],
            ]
        }

        yield row, tweet


def lv_features(features_tweets):
    for row, tweet in features_tweets:
        label = tweet.parsed.get('lang', None)

        if label not in ('lv', 'ru', 'en'):
            continue

        row['label'] = label

        yield row, tweet
