DOCKER_COMPOSE_FILE=docker-compose.yaml

.PHONY: start_dev_env
start_dev_env:
	docker-compose -f ${DOCKER_COMPOSE_FILE} \
		up -d \
		dev1.group_1 dev2.group_1 dev3.group_2 dev4.group_2 dev5.no_group httpbin

.PHONY: stop_dev_env
stop_dev_env:
	docker-compose -f ${DOCKER_COMPOSE_FILE} \
		down

.PHONY: build_test_container
build_test_container:
	docker-compose -f ${DOCKER_COMPOSE_FILE} \
		build nornir

.PHONY: pytest
pytest: build_test_container
	docker-compose -f ${DOCKER_COMPOSE_FILE} \
		run nornir py.test --cov=nornir --cov-report=term-missing -vs

.PHONY: black
black: build_test_container
	docker-compose -f ${DOCKER_COMPOSE_FILE} \
		run nornir black --check .

.PHONY: sphinx
sphinx: build_test_container
	# TODO REPLACE with: sphinx-build -n -E -q -N -b dummy -d docs/_build/doctrees docs asd
	docker-compose -f ${DOCKER_COMPOSE_FILE} \
		run nornir sphinx-build -W -b html -d docs/_build/doctrees docs docs/_build/html

.PHONY: pylama
pylama: build_test_container
	docker-compose -f ${DOCKER_COMPOSE_FILE} \
		run nornir pylama .

.PHONY: mypy
mypy: build_test_container
	docker-compose -f ${DOCKER_COMPOSE_FILE} \
		run nornir mypy .

.PHONY: nbval
nbval: build_test_container
	docker-compose -f ${DOCKER_COMPOSE_FILE} \
		run nornir \
			pytest --nbval \
				docs/plugins \
				docs/howto \
				docs/tutorials/intro/initializing_nornir.ipynb \
				docs/tutorials/intro/inventory.ipynb \
