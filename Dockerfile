ARG PYTHON
FROM python:${PYTHON}-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /uvx /usr/local/bin/

# Node.js builds the Docusaurus documentation site (`make docs`). Only the node binary and npm
# are copied so the Python install under /usr/local is left untouched.
COPY --from=node:22-bookworm-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=node:22-bookworm-slim /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/npm
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NORNIR_TESTS=1 \
    UV_PROJECT_ENVIRONMENT=/usr/local \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy

RUN apt-get update \
    && apt-get install -yq git make \
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
