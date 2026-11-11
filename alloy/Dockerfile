# https://developers.home-assistant.io/docs/apps/configuration#app-dockerfile
# Debian, not Alpine: the Alloy release binary is linked against glibc.
ARG BUILD_FROM=ghcr.io/home-assistant/base-debian:trixie-2026.10.3

# renovate: datasource=docker depName=grafana/alloy
ARG ALLOY_VERSION=v1.21.3
# renovate: datasource=docker depName=ghcr.io/astral-sh/uv
ARG UV_VERSION=0.13.5

FROM grafana/alloy:${ALLOY_VERSION} AS alloy
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM ${BUILD_FROM}

# renovate: datasource=pypi depName=fritz-exporter
ARG FRITZ_EXPORTER_VERSION=4.0.3

ENV UV_PYTHON_INSTALL_DIR=/opt/python \
    UV_TOOL_DIR=/opt/uv-tools \
    UV_TOOL_BIN_DIR=/usr/local/bin \
    UV_NO_CACHE=1

COPY --from=alloy /bin/alloy /usr/local/bin/alloy
COPY --from=uv /uv /usr/local/bin/uv

# libsystemd0: Alloy loads it at runtime to read the journal.
# fritz-exporter needs Python >= 3.14, newer than Debian's; uv brings its own interpreter.
# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends libsystemd0 ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && uv tool install --python 3.14 "fritz-exporter==${FRITZ_EXPORTER_VERSION}" \
    && rm /usr/local/bin/uv

COPY rootfs /
RUN chmod a+x /etc/services.d/*/run /etc/services.d/*/finish \
    /etc/cont-init.d/* \
    /usr/local/bin/alloy-config

HEALTHCHECK --interval=60s --timeout=10s --start-period=2m --retries=3 \
    CMD ["sh", "-c", "[ ! -f /run/alloy/config.alloy ] || curl -fsS -o /dev/null http://127.0.0.1:12345/-/ready"]

LABEL \
    org.opencontainers.image.title="Home Assistant App: Grafana Alloy" \
    org.opencontainers.image.description="Sends Home Assistant metrics and logs to Prometheus remote_write and Loki." \
    org.opencontainers.image.source="https://github.com/ToBeHH/homeassistant-apps" \
    org.opencontainers.image.licenses="MIT"
