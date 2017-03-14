create materialized view filtered_tweets as
SELECT tweet.tweet_id, tweet.collection
FROM tweet
--JOIN user_mention_screen_name_ratio r on r.collection = tweet.collection and r.feature_value = features#>>'{screen_names,-1}' --features#>>'{user_info,screen_name}'
-- This will join users that are not tracked (they don't have the @ sign in front of their screen_name and they don't belong to any user cluster)
LEFT JOIN user_mention_screen_name_ratio r on r.collection = tweet.collection and r.feature_value = features#>>'{user_info,screen_name}'
WHERE
  NOT features->'screen_names' ? '@@NOISE'
  AND NOT features->'user_mentions' ? '@@NOISE'
  AND (
    ((select count(*) from jsonb_array_elements_text(features->'screen_names') where value like '@%') > 0)
    OR
    (
      NOT features->'hashtags' ?| array[
          'porn', 'sex', 'nswf', 'pussy',
          'movie',
          'teamfollowback', 'ff', 'follow', 'followtrick', 'followback', 'followme', 'followmecaniff',
          'mgwv',
          'retweet', 'rt',
          'tbt',
          'nowplaying', 'np', 'soundcloud', 'music',
          'risingstar',
          'deal', 'deals', 'free', 'win', 'marketing', 'etsymntt', 'iartg',
          'gameinsight'
     ]
     AND (select count(*) from jsonb_array_elements_text(features->'hashtags') where value like 'vote%mtv' or value like 'myexandwhys%') = 0
     AND r.score < 100
    )
)
with no data;

create index on filtered_tweets (tweet_id, collection);
create index on filtered_tweets (collection);
