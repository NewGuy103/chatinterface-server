FROM python:3.12

LABEL org.opencontainers.image.source=https://github.com/newguy103/chatinterface-server
LABEL org.opencontainers.image.licenses=MPL-2.0

ENV PYTHONUNBUFFERED=1
WORKDIR /app/

# Install uv
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#installing-uv
COPY --from=ghcr.io/astral-sh/uv:0.7.2 /uv /uvx /bin/

# Place executables in the environment at the front of the path
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#using-the-environment
ENV PATH="/app/.venv/bin:$PATH"

# Compile bytecode
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#compiling-bytecode
ENV UV_COMPILE_BYTECODE=1

# uv Cache
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#caching
ENV UV_LINK_MODE=copy

# Install dependencies
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#intermediate-layers
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project

ENV PYTHONPATH=/app

COPY ./pyproject.toml ./uv.lock ./alembic.ini /app/
COPY ./app /app/app

COPY ./static/ /app/static
COPY ./templates/ /app/templates

COPY ./migrations/ /app/migrations
COPY ./scripts/ /app/scripts

# Also add scripts to $PATH
ENV PATH="/app/scripts:$PATH"

# Sync the project
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#intermediate-layers
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync

VOLUME [ "/app/chatinterface-server_config" ]
EXPOSE 8000

ENTRYPOINT [ "fastapi", "run", "app/main.py" ]
CMD [ "--host", "0.0.0.0", "--port", "8000" ]
