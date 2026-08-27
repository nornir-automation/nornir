NAME=$(shell basename $(PWD))

NORNIR_DIRS=nornir tests docs

PYTHON:=3.10

.PHONY: docker
docker:
	docker build --build-arg PYTHON=$(PYTHON) -t $(NAME):latest -f Dockerfile .

.PHONY: wheel
wheel:
	rm -rf dist
	uv build
	uv run --no-project python tests/wheel_importability.py

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
