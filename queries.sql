-- Number of tweets by language
select tweet->>'lang' as language, count(*)
from tweet
where features->>'from_riga' like 'true'
group by language
order by count;

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
screen_name,
tweet->>'lang' as lang,
count(*) as count
from tweet, jsonb_array_elements(features->'screen_names') screen_name
group by screen_name, lang
order by count desc;

-- Count how many times users were mentioned.
select
user_mention,
tweet->>'lang' as lang,
count(*) as count
from tweet, jsonb_array_elements(features->'user_mentions') user_mention
group by user_mention, lang
order by count desc;

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
