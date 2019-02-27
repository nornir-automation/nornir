ARG PYTHON
FROM python:${PYTHON}-slim-stretch AS builder

WORKDIR /nornir
ARG POETRY_PATH="/root/.poetry/bin/poetry"

RUN apt-get update \
    && apt-get install -yq curl git \
    && curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python \
    && python -m venv .venv \
    && ${POETRY_PATH} config settings.virtualenvs.in-project true

COPY pyproject.toml .
COPY poetry.lock .

# Dependencies change more often, so we break RUN to cache the previous layer
RUN ${POETRY_PATH} run pip install --no-cache-dir -U pip setuptools \
    && ${POETRY_PATH} install --no-interaction

# Source code changes even more often, so we cache another layer
COPY nornir nornir
COPY README.md README.md

# Install Nornir as a package
RUN ${POETRY_PATH} install --no-interaction

# Stage 2
FROM python:${PYTHON}-slim-stretch

WORKDIR /nornir

RUN apt-get update \
    && apt-get install -yq pandoc

COPY --from=builder /nornir/.venv .venv
COPY --from=builder /nornir/nornir.egg-info nornir.egg-info
COPY --from=builder /usr/bin/git /usr/bin/git

ENV PATH "/nornir/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV NORNIR_TESTS 1

COPY nornir nornir
COPY docs docs
COPY tests tests
COPY setup.cfg .
COPY CHANGELOG.rst .
COPY CONTRIBUTING.rst .
COPY README.md .


CMD ["/bin/bash"]