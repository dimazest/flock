ALTER TABLE public.topic
    ADD COLUMN eval_topic_rts_id character varying;
ALTER TABLE public.topic
    ADD COLUMN eval_topic_collection character varying;

ALTER TABLE public.topic
    ADD CONSTRAINT topic_eval_topic_fkey FOREIGN KEY (eval_topic_rts_id, eval_topic_collection, user_id)
    REFERENCES public.eval_topic (rts_id, collection, user_id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION;
CREATE INDEX fki_topic_eval_topic_fkey
    ON public.topic(eval_topic_rts_id, eval_topic_collection, user_id);

ALTER TABLE public.eval_relevance_judgment
    ADD COLUMN from_dev boolean NOT NULL DEFAULT False;
