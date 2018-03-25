.PHONY: start_nsot
start_nsot:
	cp $(PWD)/tests/inventory_data/nsot/nsot.sqlite3 $(PWD)/tests/inventory_data/nsot/nsot-docker.sqlite3
	docker run -v $(PWD)/tests/inventory_data/nsot/nsot-docker.sqlite3:/nsot.sqlite3 -p 8990:8990 -d --name=nsot nsot/nsot start --noinput

.PHONY: stop_nsot
stop_nsot:
	docker rm -f nsot
