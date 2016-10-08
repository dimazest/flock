select lower(mention#>>'{}') as m, count(*)
from tweet, jsonb_array_elements(features->'user_mentions') mention
where lower(mention#>>'{}') not like '@%'
group by m
order by count(*) desc;
