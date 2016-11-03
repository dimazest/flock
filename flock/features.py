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
                'tracked': mention['screen_name'] in user_labels,
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
            features['retweeted_status__user__screen_names'] = sorted(
                user_labels.get(in_reply_to_user_id, [retweeted_status['id']])
            )
            features['retweeted_status__id'] = [retweeted_status['id']]

        in_reply_to_user_id = tweet.parsed.get('in_reply_to_user_id', None)
        if in_reply_to_user_id:
            features['in_reply_to_screen_names'] = sorted(
                user_labels.get(in_reply_to_user_id, [tweet.parsed['in_reply_to_screen_name']])
            )

        row = {
            'tweet_id': tweet.id,
            'label': '_{}'.format(tweet.id % 3),
            'features': features,
            'created_at': tweet.created_at,
        }

        yield row, tweet


def lv_features(features_tweets):
    for row, tweet in features_tweets:
        label = tweet.parsed.get('lang', None)

        if label not in ('lv', 'ru', 'en'):
            continue

        row['label'] = label

        yield row, tweet
