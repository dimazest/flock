create materialized view feature_counts as
select *
from  (
      select tweet.collection, 'screen_names' as feature_name, feature_value, count(*) count
      from tweet, jsonb_array_elements_text(features->'screen_names') feature_value
      group by collection, feature_value
      union
      select tweet.collection, 'hashtags' as feature_name, feature_value, count(*) count
      from tweet, jsonb_array_elements_text(features->'hashtags') feature_value
      group by collection, feature_value
      union
      select tweet.collection, 'user_mentions' as feature_name, feature_value, count(*) count
      from tweet, jsonb_array_elements_text(features->'user_mentions') feature_value
      group by collection, feature_value
      union
      select tweet.collection, 'languages' as feature_name, feature_value, count(*) count
      from tweet, jsonb_array_elements_text(features->'languages') feature_value
      group by collection, feature_value
) as s
order by count desc
with no data;

create index on feature_counts (collection, feature_name, feature_value);
create index on feature_counts (feature_name);
