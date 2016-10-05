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

-- Count tweets written by users.
select
tweet#>>'{user,screen_name}' as screen_name,
count(*) as count
from tweet
group by screen_name
order by count desc;

-- Count how many times users were mentioned.
select
tweet->>'lang' as lang,
mentions->>'screen_name' as mention,
count(*) as count
from tweet, jsonb_array_elements(tweet#>'{entities,user_mentions}') mentions
group by lang, mention
order by count desc;

-- Count how many times hashtags were mentioned.
select
tweet->>'lang' as lang,
hashtags->>'text' as hashtag,
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
