FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install -e .

COPY shared ./shared
COPY content_engine ./content_engine
COPY tg_admin_bot ./tg_admin_bot
COPY tg_subscriber_bot ./tg_subscriber_bot
COPY publisher ./publisher
COPY video_factory ./video_factory
COPY payments ./payments
COPY scripts ./scripts

RUN mkdir -p /app/storage/drafts /app/storage/media /app/storage/clips

CMD ["python", "-c", "print('Specify a service command')"]
