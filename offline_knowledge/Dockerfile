# https://developers.home-assistant.io/docs/apps/configuration#app-dockerfile
ARG BUILD_FROM=ghcr.io/home-assistant/base:3.23
FROM ${BUILD_FROM}

# Zimi is installed from PyPI into a venv on the HA base image (bashio and
# s6-overlay included) instead of extending the upstream Zimi image, which
# carries Chromium, Node, ffmpeg and TTS engines (about 1 GB) we don't use.
#
# --no-deps on purpose: libtorrent and zeroconf are optional imports in Zimi.
# Leaving them out makes BitTorrent, UPnP and Nearby impossible, not just off.

# renovate: datasource=pypi depName=zimi
ARG ZIMI_VERSION=1.14.1
# renovate: datasource=pypi depName=libzim
ARG LIBZIM_VERSION=3.13.1
# renovate: datasource=pypi depName=certifi
ARG CERTIFI_VERSION=2026.10.23

ENV PATH="/opt/zimi/bin:${PATH}"

RUN apk add --no-cache \
        libstdc++ \
        python3 \
    && python3 -m venv /opt/zimi \
    && pip install --no-cache-dir --no-deps \
        "zimi==${ZIMI_VERSION}" \
        "libzim==${LIBZIM_VERSION}" \
        "certifi==${CERTIFI_VERSION}" \
    && python3 -c "import libzim, zimi.server" \
    && find /opt/zimi -name '__pycache__' -prune -exec rm -rf {} +

# Own content downloader (stdlib only), runs in the same venv.
COPY downloader/okdl /opt/okdl/okdl

COPY rootfs /
RUN chmod a+x /etc/services.d/*/run /etc/services.d/*/finish

# The first start may build title indexes for every ZIM, hence the long grace.
HEALTHCHECK --interval=60s --timeout=10s --start-period=15m --retries=3 \
    CMD ["curl", "-fsS", "-o", "/dev/null", "http://127.0.0.1:8899/health"]

LABEL \
    org.opencontainers.image.title="Home Assistant App: Offline Knowledge" \
    org.opencontainers.image.description="Wikipedia and other reference works, offline maps and data tools, available without an internet connection." \
    org.opencontainers.image.source="https://github.com/ToBeHH/homeassistant-apps" \
    org.opencontainers.image.licenses="MIT"
