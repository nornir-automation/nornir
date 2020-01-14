ARG PYTHON
FROM python:${PYTHON}-slim-buster

WORKDIR /nornir
ENV PATH="/nornir/.venv/bin:/root/.poetry/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NORNIR_TESTS=1

RUN apt-get update \
    && apt-get install -yq curl git pandoc \
    && curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python \
    && poetry config virtualenvs.in-project true

COPY pyproject.toml .
COPY poetry.lock .

# Dependencies change more often, so we break RUN to cache the previous layer
RUN poetry install --no-interaction

COPY . .

# Install the project as a package
RUN poetry install --no-interaction

CMD ["/bin/bash"]