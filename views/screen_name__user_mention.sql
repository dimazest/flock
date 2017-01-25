-- drop materialized view if exists tweet_representative;
-- drop materialized view if exists collection_ublog_group_exact_matches;
-- drop index if exists idx_collection_ublog_group_retweets__tweet_id;
-- drop materialized view if exists collection_ublog_group_retweets;
-- drop materialized view if exists screen_names__user_mentions_ublog;

create materialized view screen_name__user_mention as
SELECT t.screen_name AS screen_name, t.screen_name_id, t.collection, t.count AS tweets, m.count AS mentions
FROM (
     SELECT features#>>'{user_info,screen_name_id}' screen_name_id, collection, features#>>'{user_info,screen_name}' screen_name, count(*) AS count
     FROM tweet
     GROUP BY screen_name_id, collection, screen_name
) t
JOIN (
     SELECT um->>'id' as screen_name_id, collection, count(*) AS count
     FROM tweet, jsonb_array_elements(tweet.features -> 'user_mentions_ids') um
     GROUP BY screen_name_id, collection
) m ON t.screen_name_id = m.screen_name_id and t.collection=m.collection
with no data;

-- create index idx_collection_ublog_group_retweets__tweet_id on collection_ublog_group_retweets (tweet_id);

-- create materialized view collection_ublog_group_retweets as
-- select t.tweet_id, count(*)
-- from (
--     select
--     case when features->'is_retweet' @> '"False"' then tweet_id else cast(features#>>'{retweeted_status__id,0}' as bigint) end as tweet_id
--     from tweet
--     where
--         features#>>'{user_info,screen_name_id}' in (
--             select screen_name_id
--             from screen_names__user_mentions_ublog
--             where
--             tweets < 1000
--             and mentions < 10000
--             --10 < tweets and tweets < 1000
--             --and 10 < mentions and mentions < 10000
--         )

-- ) as t
-- join tweet on tweet.tweet_id = t.tweet_id and tweet.collection = '2015-04-04.through.2014-04-10_EN'
-- where (tweet.features#>>'{filter,token_count}')::int > 2
-- group by t.tweet_id;


-- create materialized view collection_ublog_group_exact_matches as
-- select c.tweet_id, c.count as retweet_count, em.count as exact_match_count, c.count + em.count as count
-- from collection_ublog_group_retweets c
-- join (
--      select min(t.tweet_id) as tweet_id, count(*)
--      from collection_ublog_group_retweets c
--      join tweet as t on t.tweet_id = c.tweet_id and t.collection = '2015-04-04.through.2014-04-10_EN'
--      group by t.features#>'{filter,simhash}'
-- ) as em on em.tweet_id = c.tweet_id;
