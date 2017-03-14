create materialized view feature_scores as
select l.*, g.count as global_count, log(l.count) - log(g.count) + log(4343027) - log(3296212) as score
from filtered_feature_counts l
join feature_counts g on l.collection = g.collection and l.feature_name = g.feature_name and l.feature_value = g.feature_value
order by score desc, l.count desc
with no data;

create index on feature_scores (collection, feature_name, feature_value)
