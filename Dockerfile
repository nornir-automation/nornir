ARG PYTHON
FROM python:${PYTHON}-slim-stretch

WORKDIR /nornir
ENV PATH="/root/.poetry/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NORNIR_TESTS=1

RUN apt-get update \
    && apt-get install -yq curl git pandoc \
    && curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py | python \
    && poetry config virtualenvs.create false

COPY pyproject.toml .
COPY poetry.lock .

# Dependencies change more often, so we break RUN to cache the previous layer
RUN poetry install --no-interaction

COPY . .

# Install the project as a package
RUN poetry install --no-interaction

CMD ["/bin/bash"]