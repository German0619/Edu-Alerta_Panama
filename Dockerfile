# EDU-ALERTA Panamá - imagen única para app, pipeline, scheduler y pruebas
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src \
    TZ=America/Panama

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements.txt -r requirements-dev.txt

COPY . .
RUN sed -i 's/\r$//' docker/entrypoint.sh && chmod +x docker/entrypoint.sh \
    && useradd --create-home --uid 1000 edu \
    && mkdir -p /app/data/db /app/data/incoming /app/data/raw /app/data/demo \
    && chown -R edu:edu /app

USER edu

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fs http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["app"]
