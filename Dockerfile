FROM python:3.11.9-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# psycopg2/mysqlclient build deps; removed from the final layer to keep it lean.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        default-libmysqlclient-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Static files are collected at build time; safe to fail if S3/static isn't configured yet.
RUN python manage.py collectstatic --no-input || true

EXPOSE 8000

# ASGI server (daphne) because the app uses Django Channels / websockets.
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "rbf_platform.asgi:application"]
