FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/backend

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        curl \
        docker.io \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

COPY backend/requirements.txt /app/backend/requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r /app/backend/requirements.txt

COPY backend/alembic.ini /app/backend/alembic.ini
COPY backend/scripts /app/backend/scripts
COPY backend/app /app/backend/app

RUN chmod +x /app/backend/scripts/docker-start.sh

EXPOSE 8000

CMD ["/app/backend/scripts/docker-start.sh"]
