create materialized view tweet_representative as
--EXPLAIN (ANALYZE, COSTS, VERBOSE, BUFFERS, FORMAT JSON)
--EXPLAIN
with recursive search_relation(tweet_id, collection, head_tweet_id, relation, depth, path, cycle) AS (
          SELECT r.tweet_id, r.collection, r.head_tweet_id, array[r.relation], 1, ARRAY[r.tweet_id], false
          FROM (
               select tweet_id, collection, relation, head_tweet_id from relation
               union all
               select tweet_id, collection, 'retweet', (features#>>'{retweeted_status__id,0}')::bigint
               from tweet
               where features#>'{filter,is_retweet}' = 'true'
               union all
               select t1.tweet_id, t1.collection, 'exact_match', t2.tweet_id
               from tweet t1, tweet t2
               where t1.features#>'{filter,simhash}' = t2.features#>'{filter,simhash}' and t1.collection = t2.collection and t1.created_at < t2.created_at
          ) r
          --WHERE collection = 'hour'
        UNION ALL
        SELECT r.tweet_id, r.collection, r.head_tweet_id,
          sr.relation || r.relation,
          sr.depth + 1,
          path || r.tweet_id,
          r.tweet_id = ANY(path)
        FROM relation r, search_relation sr
        WHERE r.tweet_id = sr.head_tweet_id AND r.collection = sr.collection AND NOT cycle
)
SELECT
path[1] as tweet_id, collection, min(head_tweet_id) as representative_tweet_id
FROM search_relation o
group by path[1], collection
with no data;

create index on tweet_representative (representative_tweet_id, collection);
