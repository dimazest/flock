PRODUCE = bin/python src/produce/produce

insert:
	 ${PRODUCE} $(patsubst tweets/share/%.txt,tweets/db/%.inserted,$(wildcard tweets/share/lv/*))
	 ${PRODUCE} $(patsubst tweets/share/%.txt,tweets/db/%.inserted,$(wildcard tweets/share/koninginnedag2012/*))
	 ${PRODUCE} $(patsubst tweets/share/%.txt,tweets/db/%.inserted,$(wildcard tweets/share/uefa_euro2012/*))

share:
	${PRODUCE} $(patsubst tweets/select/%.gz,tweets/share/%.txt,$(wildcard tweets/select/*/*))

clean:
	rm tweets/{hydrate,db}/*

cleandb:
	rm tweets/db/*

pginit:
	initdb -D 'parts/postgres/data'

# Start DB
createdb:
	createdb tweets

get_user_ids:
	bin/flock config query_user_ids --poultry-config parts/etc/poultry.cfg
