filter:
	bin/python src/produce/produce $$(for name in `ls tweets/select`; do echo tweets/filter/{riga,media,грипп,дождь,lv,ru}/$$name; done)

clean:
	rm tweets/filter/*/*
	rm tweets/hydrate/*
