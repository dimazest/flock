PRODUCE = bin/python src/produce/produce
POULTRY = bin/poultry

UBLOG_15_APRIL = tweets/hydrate/2015-04-04.through.2014-04-10
UBLOG_15_APRIL_EN = ${UBLOG_15_APRIL}_EN

.PHONY: insert hydrate share ger_user_ids ublogen

insert: $(patsubst tweets/hydrate/%.gz,tweets/db/%.inserted,$(wildcard tweets/hydrate/*/*.gz))

hydrate: $(patsubst tweets/share/%.txt,tweets/hydrate/%.gz,$(wildcard tweets/share/*/*.txt))

share-lv: $(patsubst tweets/select/%.gz,tweets/share/%.txt,$(wildcard tweets/select/lv/*))

get_user_ids:
	bin/flock config query_user_ids --poultry-config parts/etc/poultry.cfg --clusters $F

${UBLOG_15_APRIL_EN}/%:
	zcat $(patsubst ${UBLOG_15_APRIL_EN}/%,${UBLOG_15_APRIL}/%,$@) |\
	${POULTRY} filter \
	--config filters/en.cfg \
	--filters filter:en |\
	gzip > $@

# Filters the English tweets from the Ublog 2015 April collection into a separate collection.
ublogen: $(patsubst ${UBLOG_15_APRIL}/%,${UBLOG_15_APRIL_EN}/%,$(wildcard ${UBLOG_15_APRIL}/*.gz))

tweets/%:
	time ${PRODUCE} $@
