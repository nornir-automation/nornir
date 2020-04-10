DOCKER_COMPOSE_FILE=docker-compose.yaml
DOCKER_COMPOSE=PYTHON=${PYTHON} docker-compose -f ${DOCKER_COMPOSE_FILE}
NORNIR_DIRS=nornir tests docs

PYTHON:=3.7

.PHONY: docker
docker:
	docker build --build-arg PYTHON=$(PYTHON) -t nornir-dev:latest -f Dockerfile .

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
		docs/howto \
		docs/tutorials/intro/initializing_nornir.ipynb \
		docs/tutorials/intro/inventory.ipynb

.PHONY: tests
tests: black sphinx pylama mypy nbval pytest

.PHONY: docker-tests
docker-tests: docker
	docker run --name nornir-tests --rm nornir-dev:latest make tests
