create materialized view screen_names as
select collection, tweet_id, screen_name
from tweet, jsonb_array_elements_text(features->'screen_names') screen_name
order by collection, tweet_id
with no data;

create index on screen_names (collection, tweet_id);

