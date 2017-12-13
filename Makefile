.PHONY: start_inventory_containers
start_nsot:
	docker run -v $(PWD)/tests/inventory_data/nsot/nsot.sqlite3:/nsot.sqlite3 -p 8990:8990 -d --name=nsot nsot/nsot start --noinput

.PHONY: stop_inventory_containers
stop_nsot:
	docker rm -f nsot
