FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/runtime \
    PAPI_KIDS_PRIVATE_STORAGE_DIR=/data/private

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir --disable-pip-version-check -r /app/requirements.txt \
    && groupadd --system papi \
    && useradd --system --gid papi --home-dir /nonexistent --shell /usr/sbin/nologin papi \
    && mkdir -p /data/private \
    && chown -R papi:papi /data/private /app

COPY runtime /app/runtime
USER papi

EXPOSE 8000
CMD ["gunicorn", "--workers", "2", "--threads", "4", "--timeout", "120", "--bind", "0.0.0.0:8000", "papi_core.papi_kids_wsgi:app"]
