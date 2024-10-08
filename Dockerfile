FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

COPY pyproject.toml uv.lock README.md src/ ./
RUN /bin/uv sync --frozen --no-cache

CMD ["/bin/uv", "run", "cli", "jellbrid"]