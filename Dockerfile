ARG PYTHON
FROM python:${PYTHON}-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /uvx /usr/local/bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NORNIR_TESTS=1 \
    UV_PROJECT_ENVIRONMENT=/usr/local \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy

RUN apt-get update \
    && apt-get install -yq curl git pandoc make \
    && rm -rf /var/lib/apt/lists/*

ARG NAME=nornir
WORKDIR /${NAME}

COPY pyproject.toml uv.lock ./

# Dependencies change less often than code, so we break RUN to cache this layer
RUN uv sync --locked --no-install-project

COPY . .

# Install the project as a package
RUN uv sync --locked

CMD ["/bin/bash"]
