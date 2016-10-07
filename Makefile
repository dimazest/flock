PRODUCE = bin/python src/produce/produce

report: insert
	psql -d twitter < user_names.sql > user_names.sql.txt
	psql -d twitter < mentions.sql > mentions.sql.txt

insert:
	 ${PRODUCE} $(patsubst tweets/share/%.txt,tweets/db/%.inserted,$(wildcard tweets/share/*))

share:
	${PRODUCE} $(patsubst tweets/select/%.gz,tweets/share/%.txt,$(wildcard tweets/select/*))

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
