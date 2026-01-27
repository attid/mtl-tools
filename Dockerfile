# syntax=docker/dockerfile:1.4

FROM python:3.12-slim AS runtime

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        libjpeg62-turbo-dev \
        zlib1g-dev \
        libfreetype6-dev \
        liblcms2-dev \
        libopenjp2-7 \
        libtiff6 \
        libwebp-dev \
        libpq-dev \
        libzbar0 \
        fonts-dejavu-core \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first (for caching)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

RUN useradd --create-home --shell /bin/bash bot
RUN mkdir -p /app/logs /app/data \
    && chown -R bot:bot /app

# Copy source code
COPY --chown=bot:bot . .

USER bot

CMD ["uv", "run", "python", "start.py"]
