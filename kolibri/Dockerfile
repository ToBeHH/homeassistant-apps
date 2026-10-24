# https://developers.home-assistant.io/docs/apps/configuration#app-dockerfile
ARG BUILD_FROM=ghcr.io/home-assistant/base:3.23
FROM ${BUILD_FROM}

# Phase 1: scaffold only. Kolibri itself is added in phase 3 (see TODO.md).

COPY rootfs /
RUN chmod a+x /etc/services.d/*/run /etc/services.d/*/finish

LABEL \
    org.opencontainers.image.title="Home Assistant App: Kolibri" \
    org.opencontainers.image.description="Kolibri offline learning platform, available without an internet connection." \
    org.opencontainers.image.source="https://github.com/ToBeHH/homeassistant-addons-public" \
    org.opencontainers.image.licenses="MIT"
