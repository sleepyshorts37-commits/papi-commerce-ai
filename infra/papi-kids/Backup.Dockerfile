FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/runtime \
    PAPI_KIDS_BACKUP_DIRECTORY=/data/backups

RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client rclone \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 papi \
    && useradd --uid 10001 --gid papi --home-dir /nonexistent --shell /usr/sbin/nologin papi \
    && mkdir -p /data/backups /app \
    && chown -R papi:papi /data/backups /app \
    && chmod 0700 /data/backups

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir --disable-pip-version-check -r /app/requirements.txt

COPY runtime /app/runtime
USER papi
CMD ["python", "-m", "papi_core.papi_kids_backup_runner"]
