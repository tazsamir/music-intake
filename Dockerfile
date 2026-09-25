FROM python:3.12-slim

ARG APP_VERSION=dev
LABEL org.opencontainers.image.title="music-intake" \
      org.opencontainers.image.description="Safe Beets-based music intake daemon" \
      org.opencontainers.image.version="$APP_VERSION" \
      org.opencontainers.image.licenses="MIT"

RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu libchromaprint-tools \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir . "beets[fetchart,chroma]"
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod 0755 /usr/local/bin/docker-entrypoint.sh \
    && mkdir -p /downloads /music /state

ENV DOWNLOADS_PATH=/downloads \
    LIBRARY_PATH=/music \
    STATUS_FILE=/state/status.json \
    SCAN_INTERVAL=60 \
    STABLE_OBSERVATIONS=3 \
    PUID=1000 \
    PGID=1000
VOLUME ["/downloads", "/music", "/state"]
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["music-intake"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import json,os; json.load(open(os.environ['STATUS_FILE']))" || exit 1
