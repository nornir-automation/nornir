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

.PHONY: mypy
mypy:
	poetry run mypy nornir tests

.PHONY: nbval
nbval:
	poetry run pytest --nbval --sanitize-with docs/nbval_sanitize.cfg \
		docs/tutorial/ \
		docs/howto/

.PHONY: ruff
ruff:
	poetry run ruff check .

.PHONY: tests
tests: ruff mypy nbval pytest sphinx

.PHONY: docker-tests
docker-tests: docker
	docker run --name nornir-tests --rm $(NAME):latest make tests

.PHONY: docs
docs:
	poetry run ./docs/build_api.sh
	poetry run make -C docs clean html
