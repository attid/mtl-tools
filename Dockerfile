# syntax=docker/dockerfile:1.4

FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

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

COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

RUN useradd --create-home --shell /bin/bash bot
RUN mkdir -p /app/logs /app/data \
    && chown -R bot:bot /app

COPY --chown=bot:bot . .

USER bot

CMD ["python", "start.py"]
