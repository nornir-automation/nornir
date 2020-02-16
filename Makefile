DOCKER_COMPOSE_FILE=docker-compose.yaml
DOCKER_COMPOSE=PYTHON=${PYTHON} docker-compose -f ${DOCKER_COMPOSE_FILE}
NORNIR_DIRS=nornir tests docs

.PHONY: start_dev_env
start_dev_env:
	${DOCKER_COMPOSE} \
		up -d

.PHONY: stop_dev_env
stop_dev_env:
	${DOCKER_COMPOSE} \
		down

.PHONY: pytest
pytest:
	poetry run pytest --cov=nornir --cov-report=term-missing -vs ${ARGS}

.PHONY: black
black:
	poetry run black --check ${NORNIR_DIRS}

.PHONY: sphinx
sphinx:
	# TODO REPLACE with: sphinx-build -n -E -q -N -b dummy -d docs/_build/doctrees docs asd
	poetry run sphinx-build -W -b html -d docs/_build/doctrees docs docs/_build/html

.PHONY: pylama
pylama:
	poetry run pylama ${NORNIR_DIRS}

.PHONY: mypy
mypy:
	poetry run mypy nornir tests

.PHONY: nbval
nbval:
	poetry run pytest --nbval --sanitize-with docs/nbval_sanitize.cfg \
		docs/plugins \
		docs/howto \
		docs/tutorials/intro/initializing_nornir.ipynb \
		docs/tutorials/intro/inventory.ipynb

.PHONY: tests
tests: stop_dev_env start_dev_env black sphinx pylama mypy nbval pytest
