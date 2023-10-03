NAME=$(shell basename $(PWD))

DOCKER_COMPOSE_FILE=docker-compose.yaml
DOCKER_COMPOSE=PYTHON=${PYTHON} docker-compose -f ${DOCKER_COMPOSE_FILE}
NORNIR_DIRS=nornir tests docs

PYTHON:=3.10

.PHONY: docker
docker:
	docker build --build-arg PYTHON=$(PYTHON) -t $(NAME):latest -f Dockerfile .

.PHONY: pytest
pytest:
	poetry run pytest --cov=nornir --cov-report=term-missing -vs ${ARGS}

.PHONY: black
black:
	poetry run black --check ${NORNIR_DIRS}

.PHONY: sphinx
sphinx:
	# TODO REPLACE with: sphinx-build -n -E -q -N -b dummy -d docs/_build/doctrees docs asd
	# poetry run sphinx-build -W -b html -d docs/_build/doctrees docs docs/_build/html
	echo "WARNING: sphinx needs to be added here!!!"

.PHONY: pylama
pylama:
	poetry run pylama ${NORNIR_DIRS}

.PHONY: mypy
mypy:
	poetry run mypy nornir tests

.PHONY: nbval
nbval:
	poetry run pytest --nbval --sanitize-with docs/nbval_sanitize.cfg \
		docs/tutorial/ \
		docs/howto/

.PHONY: tests
tests: black pylama mypy nbval pytest sphinx

.PHONY: docker-tests
docker-tests: docker
	docker run --name nornir-tests --rm $(NAME):latest make tests

.PHONY: docs
docs:
	./docs/build_api.sh
	make -C docs clean html
