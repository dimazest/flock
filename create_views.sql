-- Number of tweets by language
create or replace view language_usage as
select tweet->>'lang' as language, count(*)
from tweet
where features->>'from_riga' like 'true'
group by language
order by count desc;

-- Tweets written by users
create or replace view screen_name as
select
screen_name,
COALESCE(lv, 0) as lv,
COALESCE(ru, 0) as ru,
COALESCE(en, 0) as en,
COALESCE(lv, 0) + COALESCE(ru, 0) + COALESCE(en, 0) as total,
round(
    0.5 - abs(
        (
            (COALESCE(lv, 0) + 0.0) / (COALESCE(lv, 0)  + COALESCE(ru, 0) + 0.00001)
        )
        - 0.5
    ),
    2
) as score
from crosstab(
    $$
	select
	screen_name#>>'{}',
	tweet->>'lang' as lang,
	count(*) as count
	from tweet, jsonb_array_elements(features->'screen_names') screen_name
	group by screen_name, lang
	order by 1;
    $$,
    $$
    select distinct tweet->>'lang' from tweet where tweet->>'lang' in ('en', 'ru', 'lv')
 order by 1
    $$
)
as final_result(screen_name text, en bigint, lv bigint, ru bigint)
order by score desc, total desc, screen_name;


-- Count user mentions
create or replace view user_mention as
select
user_mention,
COALESCE(lv, 0) as lv,
COALESCE(ru, 0) as ru,
COALESCE(en, 0) as en,
COALESCE(lv, 0) + COALESCE(ru, 0) + COALESCE(en, 0) as total,
round(
    0.5 - abs(
        (
            (COALESCE(lv, 0) + 0.0) / (COALESCE(lv, 0)  + COALESCE(ru, 0) + 0.00001)
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
    where tweet->>'lang' in ('en', 'ru', 'lv')
	group by user_mention, lang
    order by 1
    $$,
    $$
    select distinct tweet->>'lang' from tweet where tweet->>'lang' in ('en', 'ru', 'lv') order by 1
    $$
)
as final_result(user_mention text, en bigint, lv bigint, ru bigint)
order by score desc, total desc, user_mention;
