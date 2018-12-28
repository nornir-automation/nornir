ifeq ($(PYTHON), )
override PYTHON=3.6
endif

DOCKER_COMPOSE_FILE=docker-compose.yaml
DOCKER_COMPOSE=PYTHON=${PYTHON} docker-compose -f ${DOCKER_COMPOSE_FILE}

.PHONY: start_dev_env
start_dev_env:
	${DOCKER_COMPOSE} \
		up -d \
		dev1.group_1 dev2.group_1 dev3.group_2 dev4.group_2 dev5.no_group httpbin

.PHONY: stop_dev_env
stop_dev_env:
	${DOCKER_COMPOSE} \
		down

.PHONY: build_test_container
build_test_container:
	${DOCKER_COMPOSE} \
		build nornir

.PHONY: enter-container
enter-container: build_test_container
	${DOCKER_COMPOSE} \
		run nornir bash

.PHONY: pytest
pytest: build_test_container
	${DOCKER_COMPOSE} \
		run nornir py.test --cov=nornir --cov-report=term-missing -vs ${ARGS}

.PHONY: black
black: build_test_container
	${DOCKER_COMPOSE} \
		run nornir black --check .

.PHONY: sphinx
sphinx: build_test_container
	# TODO REPLACE with: sphinx-build -n -E -q -N -b dummy -d docs/_build/doctrees docs asd
	${DOCKER_COMPOSE} \
		run nornir sphinx-build -W -b html -d docs/_build/doctrees docs docs/_build/html

.PHONY: pylama
pylama: build_test_container
	${DOCKER_COMPOSE} \
		run nornir pylama .

.PHONY: mypy
mypy: build_test_container
	${DOCKER_COMPOSE} \
		run nornir mypy .

.PHONY: nbval
nbval: build_test_container
	${DOCKER_COMPOSE} \
		run nornir \
			pytest --nbval \
				docs/plugins \
				docs/howto \
				docs/tutorials/intro/initializing_nornir.ipynb \
				docs/tutorials/intro/inventory.ipynb \
