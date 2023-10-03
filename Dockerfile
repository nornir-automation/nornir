ARG PYTHON
FROM python:${PYTHON}-slim-bookworm

ENV PATH="/root/.local/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NORNIR_TESTS=1

RUN apt-get update \
    && apt-get install -yq curl git pandoc make \
    && curl -sSL https://install.python-poetry.org  | python3 - \
    && poetry config virtualenvs.create false

COPY pyproject.toml .
COPY poetry.lock .

# Dependencies change more often, so we break RUN to cache the previous layer
RUN poetry install --no-interaction

ARG NAME=nornir
WORKDIR /${NAME}

COPY . .

# Install the project as a package
RUN poetry install --no-interaction

CMD ["/bin/bash"]

