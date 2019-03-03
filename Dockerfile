ARG PYTHON
# Stage 1 - Build and install dependencies
FROM python:${PYTHON}-slim-stretch AS builder

WORKDIR /nornir
ARG POETRY_PATH="/root/.poetry/bin/poetry"

RUN apt-get update \
    && apt-get install -yq curl git \
    && curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python \
    && python -m venv .venv \
    && ${POETRY_PATH} config settings.virtualenvs.in-project true \
    && .venv/bin/pip install --no-cache-dir -U pip setuptools

COPY pyproject.toml .
COPY poetry.lock .

# Dependencies change more often, so we break RUN to cache the previous layer
RUN ${POETRY_PATH} install --no-interaction

COPY README.md .
# Source code changes even more often, so we cache another layer
COPY nornir nornir

# Install Nornir as a package
RUN ${POETRY_PATH} install --no-interaction

# Stage 2 - Copy only necessary files to the runner stage
FROM python:${PYTHON}-slim-stretch

WORKDIR /nornir

RUN apt-get update \
    && apt-get install -yq pandoc

COPY --from=builder /nornir /nornir
COPY --from=builder /usr/bin/git /usr/bin/git

ENV PATH "/nornir/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV NORNIR_TESTS 1

COPY docs docs
COPY tests tests

COPY setup.cfg .
COPY CHANGELOG.rst .
COPY CONTRIBUTING.rst .


CMD ["/bin/bash"]