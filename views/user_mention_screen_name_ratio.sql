create materialized view user_mention_screen_name_ratio as
select sc.collection, sc.feature_value, sc.count as screen_name_count, um.count as user_mention_count, um.count::float / sc.count as score
from feature_counts as sc
join feature_counts as um on sc.collection = um.collection and um.feature_name = 'user_mentions' and sc.feature_value = um.feature_value
where sc.feature_name = 'screen_names' order by score desc

with no data;

create index on user_mention_screen_name_ratio (collection);
create index on user_mention_screen_name_ratio (collection, feature_value);
