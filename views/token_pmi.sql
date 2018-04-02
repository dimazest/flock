drop materialized view if exists token_pmi;
drop materialized view if exists topic_token_counts;
drop materialized view if exists token_counts;

create materialized view token_counts as
select
  collection, token, count(*) n_word
from tweet,
jsonb_array_elements_text(features#>'{tokenizer,tokens}') token
group by collection, token
--with no data
;

create index on token_counts(collection, token);

create materialized view topic_token_counts as
select * from (
  select
    i.*,
    rank() over (partition by collection, eval_topic_rts_id, judgment order by n_topic_word desc) rank
  from (
     select distinct
      j.collection, j.eval_topic_rts_id, j.judgment, token,
      count(*) over (partition by j.collection, j.eval_topic_rts_id, j.judgment) n_topic,
      count(*) over (partition by j.collection, j.eval_topic_rts_id, j.judgment, token) n_topic_word
    from eval_relevance_judgment j
    join tweet t using (collection, tweet_id),
    jsonb_array_elements_text(features#>'{tokenizer,tokens}') token
  ) i
) ii
order by eval_topic_rts_id, n_topic_word desc
--with no data
;

create index on topic_token_counts(collection, eval_topic_rts_id, token);

create materialized view token_pmi as
select
  r.collection, r.eval_topic_rts_id, r.token,
  log(r.n_topic_word) - log(r.n_topic) - log(n_word) pmi,
  n_word - r.n_topic_word - i.n_topic_word - m.n_topic_word gain
from topic_token_counts r
join token_counts using (collection, token)
join topic_token_counts i using (collection, eval_topic_rts_id, token)
join topic_token_counts m using (collection, eval_topic_rts_id, token)
where r.judgment > 0 and i.judgment = 0 and m.judgment is NULL
order by pmi desc, gain desc
--with no data
;

