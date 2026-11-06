# https://developers.home-assistant.io/docs/apps/configuration#app-dockerfile
ARG BUILD_FROM=ghcr.io/home-assistant/base:3.23
FROM ${BUILD_FROM}

# renovate: datasource=pypi depName=kolibri
ARG KOLIBRI_VERSION=0.19.5

ENV PATH="/opt/kolibri/bin:${PATH}"

# dist/cext holds optional glibc binaries, of no use on Alpine (165 MB).

RUN apk add --no-cache \
        libstdc++ \
        nginx \
        python3 \
    && python3 -m venv /opt/kolibri \
    && pip install --no-cache-dir "kolibri==${KOLIBRI_VERSION}" \
    && rm -rf /opt/kolibri/lib/python3*/site-packages/kolibri/dist/cext \
    && find /opt/kolibri -name '__pycache__' -prune -exec rm -rf {} +

# Imports the channels from the options (stdlib only), runs in the same venv.
COPY channel_sync/kbsync /opt/kbsync/kbsync

COPY rootfs /
RUN chmod a+x /etc/services.d/*/run /etc/services.d/*/finish \
    /etc/cont-init.d/* \
    /usr/local/bin/stdin-commands

# Through nginx, which adds the path prefix. The first start migrates databases.
HEALTHCHECK --interval=60s --timeout=10s --start-period=15m --retries=3 \
    CMD ["curl", "-fsS", "-o", "/dev/null", "http://127.0.0.1:8099/api/public/info/"]

# With s6-overlay only the main command gets the container's stdin.
CMD ["/usr/local/bin/stdin-commands"]

LABEL \
    org.opencontainers.image.title="Home Assistant App: Kolibri" \
    org.opencontainers.image.description="Kolibri offline learning platform, available without an internet connection." \
    org.opencontainers.image.source="https://github.com/ToBeHH/homeassistant-apps" \
    org.opencontainers.image.licenses="MIT"
