 create materialized view filtered_feature_counts as

-- with joined_filtered_tweets as (
--      select tweet.*
--      from filtered_tweets
--      inner join tweet on tweet.tweet_id = filtered_tweets.tweet_id and tweet.collection = filtered_tweets.collection
-- )
-- select *
-- from  (
--       select collection, 'screen_names' as feature_name, feature_value, count(*) count
--       from
--       joined_filtered_tweets,
--       jsonb_array_elements_text(features->'screen_names') feature_value
--       -- left inner join filtered_tweets on tweet.tweet_id = filtered_tweets.tweet_id and tweet.collection = filtered_tweet.collection
--       group by collection, feature_value
--       union all
--       select collection, 'hashtags' as feature_name, feature_value, count(*) count
--       from joined_filtered_tweets, jsonb_array_elements_text(features->'hashtags') feature_value
--       group by collection, feature_value
--       union all
--       select collection, 'user_mentions' as feature_name, feature_value, count(*) count
--       from joined_filtered_tweets, jsonb_array_elements_text(features->'user_mentions') feature_value
--       group by collection, feature_value
-- ) as s
-- order by count desc

select collection, 'screen_names' as feature_name, feature_value, count(*) count
from tweet, jsonb_array_elements_text(features->'screen_names') feature_value
where (tweet_id, collection) in (select * from filtered_tweets)
group by collection, feature_value
union all
select collection, 'hashtags' as feature_name, feature_value, count(*) count
from tweet, jsonb_array_elements_text(features->'hashtags') feature_value
where (tweet_id, collection) in (select * from filtered_tweets)
group by collection, feature_value
union all
select collection, 'user_mentions' as feature_name, feature_value, count(*) count
from tweet, jsonb_array_elements_text(features->'user_mentions') feature_value
where (tweet_id, collection) in (select * from filtered_tweets)
group by collection, feature_value
order by count desc

with no data;

create index on filtered_feature_counts (collection, feature_name, feature_value)
