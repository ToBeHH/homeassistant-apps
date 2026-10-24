# https://developers.home-assistant.io/docs/apps/configuration#app-dockerfile
ARG BUILD_FROM=ghcr.io/home-assistant/base:3.23
FROM ${BUILD_FROM}

# Phase 1: scaffold only. Zimi, CyberChef, map viewer, downloader and MCP
# bridge are added in phase 2 (see TODO.md).

COPY rootfs /
RUN chmod a+x /etc/services.d/*/run /etc/services.d/*/finish

LABEL \
    org.opencontainers.image.title="Home Assistant App: Offline Knowledge" \
    org.opencontainers.image.description="Wikipedia and other reference works, offline maps and data tools, available without an internet connection." \
    org.opencontainers.image.source="https://github.com/ToBeHH/homeassistant-addons-public" \
    org.opencontainers.image.licenses="MIT"
