FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_DEFAULT_INDEX=https://mirrors.aliyun.com/pypi/simple/

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY vendor ./vendor
RUN uv sync --frozen --no-dev

COPY alembic.ini ./
COPY migrations ./migrations
COPY src ./src

EXPOSE 8000

CMD ["uv", "run", "--frozen", "--no-dev", "uvicorn", "risktrace.main:app", "--host", "0.0.0.0", "--port", "8000"]
