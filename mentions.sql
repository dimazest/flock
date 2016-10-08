-- Count user mentions
select *,
COALESCE(en, 0) + COALESCE(lv, 0) + COALESCE(ru, 0) as total,
round(
        0.5 - abs(
	        (
	            (COALESCE(ru, 0) + 0.0) /
	            (
	                COALESCE(lv, 0.00001) +
	                COALESCE(ru, 0.00001)
	            )
	        )
            - 0.5
    ),
    2
) as score
from crosstab(
    $$
	select
	user_mention#>>'{}',
	tweet->>'lang' as lang,
	count(*) as count
	from tweet, jsonb_array_elements(features->'user_mentions') user_mention
	group by user_mention, lang
    order by 1
    $$,
    $$
    select distinct tweet->>'lang' from tweet order by 1
    $$
)
as final_result(user_mention text, en bigint, lv bigint, ru bigint)
order by score desc, total desc, user_mention;
