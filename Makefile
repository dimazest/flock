PRODUCE = bin/python src/produce/produce

.PHONY: insert hydrate share ger_user_ids

insert: $(patsubst tweets/hydrate/%.gz,tweets/db/%.inserted,$(wildcard tweets/hydrate/*/*.gz))

hydrate: $(patsubst tweets/share/%.txt,tweets/hydrate/%.gz,$(wildcard tweets/share/*/*.txt))

share: $(patsubst tweets/select/%.gz,tweets/share/%.txt,$(wildcard tweets/select/*/*))

get_user_ids:
	bin/flock config query_user_ids --poultry-config parts/etc/poultry.cfg --clusters clusters/lv.cfg

tweets/%:
	${PRODUCE} $@

