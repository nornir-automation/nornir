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
	uv run coverage run --source=nornir -m pytest -vs ${ARGS}
	uv run coverage report -m
	uv run coverage xml

.PHONY: mypy
mypy:
	uv run mypy nornir tests

.PHONY: nbval
nbval:
	uv run pytest --nbval --sanitize-with docs/nbval_sanitize.cfg \
		docs/tutorial/ \
		docs/howto/

.PHONY: ruff
ruff:
	uv run ruff check .

.PHONY: tests
tests: ruff mypy nbval pytest docs

.PHONY: docker-tests
docker-tests: docker
	docker run --name nornir-tests --rm $(NAME):latest make tests

.PHONY: docs
docs:
	uv run ./docs/build_api.sh
	uv run make -C docs clean html
