create materialized view hashtags as
select collection, tweet_id, hashtag
from tweet, jsonb_array_elements_text(features->'hashtags') hashtag
order by collection, tweet_id
with no data;

create index on hashtags (collection, tweet_id);

