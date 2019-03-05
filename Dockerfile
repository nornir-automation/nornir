ARG PYTHON
# Stage 1 - Build and install dependencies
FROM python:${PYTHON}-slim-stretch AS builder

WORKDIR /nornir
ENV PATH="/root/.poetry/bin:$PATH"

RUN apt-get update \
    && apt-get install -yq curl git \
    && curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python \
    && python -m venv .venv \
    && poetry config settings.virtualenvs.in-project true \
    && .venv/bin/pip install --no-cache-dir -U pip setuptools

COPY pyproject.toml .
COPY poetry.lock .

# Dependencies change more often, so we break RUN to cache the previous layer
RUN poetry install --no-interaction

COPY . .

# Install the project as a package
RUN poetry install --no-interaction

# Stage 2 - Copy only necessary files to the runner stage
FROM python:${PYTHON}-slim-stretch

WORKDIR /nornir

RUN apt-get update && apt-get install -yq pandoc

COPY --from=builder /usr/bin/git /usr/bin/git
COPY --from=builder /nornir /nornir

ENV PATH="/nornir/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NORNIR_TESTS=1


CMD ["/bin/bash"]