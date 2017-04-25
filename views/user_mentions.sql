create materialized view user_mentions as
select collection, tweet_id, user_mention
from tweet, jsonb_array_elements_text(features->'user_mentions') user_mention
order by collection, tweet_id
with no data;

create index on user_mentions (collection, tweet_id);

