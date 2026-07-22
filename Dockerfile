# syntax=docker/dockerfile:1

# ---- builder: install locked dependencies and the project into a venv ----
FROM python:3.14-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.8 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies first (cached independently of source changes), without the project itself.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Then the project source and the shipped Semgrep rules.
COPY src ./src
COPY resources ./resources
COPY README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---- runtime: minimal, non-root ----
FROM python:3.14-slim AS runtime

COPY --from=ghcr.io/astral-sh/uv:0.11.8 /uv /uvx /bin/

# Deterministic scanners installed as ISOLATED tools (kept out of the app venv to avoid dependency
# conflicts), with their CLIs exposed on PATH for all users. Disable via BICHO_SCANNER__*_ENABLED
# to run without them.
ENV UV_TOOL_DIR=/opt/uv/tools \
    UV_TOOL_BIN_DIR=/usr/local/bin \
    UV_PYTHON_DOWNLOADS=never
RUN --mount=type=cache,target=/root/.cache/uv \
    uv tool install "semgrep==1.170.1" && \
    uv tool install "pip-audit"

RUN groupadd --system bicho && useradd --system --gid bicho --home-dir /app bicho

WORKDIR /app
COPY --from=builder --chown=bicho:bicho /app /app

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    BICHO_ENVIRONMENT=production \
    PORT=8000

USER bicho
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/healthz')"

# Railway overrides this via railway.toml startCommand; kept here for local/other runtimes.
CMD ["sh", "-c", "uvicorn bicho.api.app:create_app --factory --host 0.0.0.0 --port ${PORT:-8000}"]
