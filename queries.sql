-- Number of tweets by language
select tweet->>'lang' as language, count(*)
from tweet
group by language;

-- Group tweets by hour and language.
select
tweet->>'lang' as lang,
date_trunc(
	'hour',
    to_timestamp(tweet->>'created_at', 'Dy Mon DD HH24:MI:SS +0000 YYYY')
) as created_at,
count(*)
from tweet
group by lang, created_at
order by created_at, lang;

-- The used apps
select tweet->>'source', count(*) count
from tweet
group by tweet->>'source'
order by count desc;

-- Count tweets written by users.
select
tweet#>>'{user,screen_name}' as screen_name,
tweet->>'lang' as lang,
count(*) as count
from tweet
group by screen_name, lang
order by count desc;

-- Crosstab the query above
select *,
COALESCE(lv, 0) + COALESCE(ru, 0) as total,
round (
        0.5 - abs(
        (
            (COALESCE(lv, 0) + 0.0) /
            (
                COALESCE(lv, 0) +
                COALESCE(ru, 0)
            )
        )
            - 0.5
    ),
    2
) as score
from crosstab(
    $$
    select
    tweet#>>'{user,screen_name}' as screen_name,
    tweet->>'lang' as lang,
    count(*) as count
    from tweet
    group by screen_name, lang
    order by 1
    $$,
    $$
    select distinct tweet->>'lang' from tweet order by 1
    $$
)
as final_result(screen_name text, lv bigint, ru bigint)
order by score desc, total desc

-- Count how many times users were mentioned.
select
mentions->>'screen_name' as mention,
tweet->>'lang' as lang,
count(*) as count
from tweet, jsonb_array_elements(tweet#>'{entities,user_mentions}') mentions
group by mention, lang
order by count desc;

-- Crosstab the query above
select *,
COALESCE(lv, 0) + COALESCE(ru, 0) as total,
round (
        0.5 - abs(
	        (
	            (COALESCE(ru, 0) + 0.0) /
	            (
	                COALESCE(lv, 0) +
	                COALESCE(ru, 0)
	            )
	        )
            - 0.5
    ),
    4
) as score
from crosstab(
    $$
	select
	mentions->>'screen_name' as mention,
	tweet->>'lang' as lang,
	count(*) as count
	from tweet, jsonb_array_elements(tweet#>'{entities,user_mentions}') mentions
	group by mention, lang
    order by 1
    $$,
    $$
    select distinct tweet->>'lang' from tweet order by 1
    $$
)
as final_result(mention text, lv bigint, ru bigint)
order by score desc, total desc;

-- Count how many times hashtags were mentioned.
select
hashtags->>'text' as hashtag,
tweet->>'lang' as lang,
count(*) as count
from tweet, jsonb_array_elements(tweet#>'{entities,hashtags}') hashtags
group by lang, hashtag
order by count desc;

-- Count how many times urls were mentioned.
select
tweet->>'lang' as lang,
urls->>'expanded_url' as url,
count(*) as count
from tweet, jsonb_array_elements(tweet#>'{entities,urls}') urls
group by lang, url
order by count desc;
