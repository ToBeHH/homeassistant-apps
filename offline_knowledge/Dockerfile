# https://developers.home-assistant.io/docs/apps/configuration#app-dockerfile
ARG BUILD_FROM=ghcr.io/home-assistant/base:3.23

# ------------------------------------------------------------------------------
# Static assets and tools, fetched and checked against SHA-256 at build time.
# When Renovate bumps one of these versions, the matching checksum (and for
# CyberChef the file name) must be updated by hand; the build fails until then.
# ------------------------------------------------------------------------------
FROM ${BUILD_FROM} AS assets
SHELL ["/bin/ash", "-eo", "pipefail", "-c"]
WORKDIR /build

# renovate: datasource=github-releases depName=gchq/CyberChef
ARG CYBERCHEF_VERSION=v11.5.0
ARG CYBERCHEF_ASSET=CyberChef_8cd426dd4f40f1423912d5fad91b578a86a65112.zip
ARG CYBERCHEF_SHA256=f6478925d3eaa16ec08626a85f5b85eed10d531a5e18700615fed7ecb024cccf
# renovate: datasource=github-releases depName=protomaps/go-pmtiles
ARG PMTILES_VERSION=1.31.2
ARG PMTILES_SHA256=3ed7dbf4ec2e6dfe5e25b6f70d1ffc932729f93c86db353bf514dd71010a312f
# renovate: datasource=npm depName=maplibre-gl
ARG MAPLIBRE_VERSION=6.13.0
ARG MAPLIBRE_SHA256=fa47c3d6e150e22d4e5af1a238b4b13dadbeab7dd0770efa902d512a87034e48
# renovate: datasource=npm depName=pmtiles
ARG PMTILES_JS_VERSION=4.5.0
ARG PMTILES_JS_SHA256=23ae7c575578ad24cd579377d69c46550631da219e6f179997ec2cf3b8c937e5
# renovate: datasource=npm depName=@protomaps/basemaps
ARG BASEMAPS_VERSION=5.7.2
ARG BASEMAPS_SHA256=2d5d41b29cdd2364f7092ad439bd9d170b4f38cbec8858cefbe84d0f98125ce6
# Fonts and sprites have no releases, so they are pinned to a commit.
ARG BASEMAPS_ASSETS_COMMIT=028c18f713baecad011301ff7a69acc39bcc2ae7
ARG BASEMAPS_ASSETS_SHA256=57e40e8c512bd8042d0a3a251f19d0d1c8523ad963c666c3c6643bada4dc92d0

RUN fetch() { curl -fsSL -o "$2" "$1"; echo "$3  $2" | sha256sum -c -; } \
    && fetch "https://github.com/gchq/CyberChef/releases/download/${CYBERCHEF_VERSION}/${CYBERCHEF_ASSET}" \
        cyberchef.zip "${CYBERCHEF_SHA256}" \
    && fetch "https://github.com/protomaps/go-pmtiles/releases/download/v${PMTILES_VERSION}/go-pmtiles_${PMTILES_VERSION}_Linux_x86_64.tar.gz" \
        pmtiles.tar.gz "${PMTILES_SHA256}" \
    && fetch "https://registry.npmjs.org/maplibre-gl/-/maplibre-gl-${MAPLIBRE_VERSION}.tgz" \
        maplibre.tgz "${MAPLIBRE_SHA256}" \
    && fetch "https://registry.npmjs.org/pmtiles/-/pmtiles-${PMTILES_JS_VERSION}.tgz" \
        pmtiles-js.tgz "${PMTILES_JS_SHA256}" \
    && fetch "https://registry.npmjs.org/@protomaps/basemaps/-/basemaps-${BASEMAPS_VERSION}.tgz" \
        basemaps.tgz "${BASEMAPS_SHA256}" \
    && fetch "https://github.com/protomaps/basemaps-assets/archive/${BASEMAPS_ASSETS_COMMIT}.tar.gz" \
        basemaps-assets.tar.gz "${BASEMAPS_ASSETS_SHA256}" \
    \
    && mkdir -p /out/bin /out/cyberchef /out/maps/lib /out/maps/fonts /out/maps/sprites \
    && unzip -q cyberchef.zip -d /out/cyberchef \
    && mv /out/cyberchef/CyberChef_*.html /out/cyberchef/index.html \
    && find /out/cyberchef -name '*.br' -delete \
    && tar -xzf pmtiles.tar.gz -C /out/bin pmtiles \
    && mkdir maplibre pmtiles-js basemaps basemaps-assets \
    && tar -xzf maplibre.tgz -C maplibre \
    && tar -xzf pmtiles-js.tgz -C pmtiles-js \
    && tar -xzf basemaps.tgz -C basemaps \
    && tar -xzf basemaps-assets.tar.gz -C basemaps-assets --strip-components=1 \
    && cp maplibre/package/dist/maplibre-gl.mjs \
        maplibre/package/dist/maplibre-gl-worker.mjs \
        maplibre/package/dist/maplibre-gl-shared.mjs \
        maplibre/package/dist/maplibre-gl.css \
        maplibre/package/LICENSE.txt \
        pmtiles-js/package/dist/pmtiles.js \
        basemaps/package/dist/basemaps.js \
        /out/maps/lib/ \
    && cp -r "basemaps-assets/fonts/Noto Sans Regular" \
        "basemaps-assets/fonts/Noto Sans Medium" \
        "basemaps-assets/fonts/Noto Sans Italic" \
        basemaps-assets/fonts/OFL.txt \
        /out/maps/fonts/ \
    && cp -r basemaps-assets/sprites/v4 /out/maps/sprites/

# ------------------------------------------------------------------------------
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
        nginx \
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

COPY --from=assets /out/bin/pmtiles /usr/local/bin/pmtiles
COPY --from=assets /out/cyberchef /var/www/landing/cyberchef
COPY --from=assets /out/maps /var/www/landing/maps

# The first start may build title indexes for every ZIM, hence the long grace.
HEALTHCHECK --interval=60s --timeout=10s --start-period=15m --retries=3 \
    CMD ["curl", "-fsS", "-o", "/dev/null", "http://127.0.0.1:8899/health"]

LABEL \
    org.opencontainers.image.title="Home Assistant App: Offline Knowledge" \
    org.opencontainers.image.description="Wikipedia and other reference works, offline maps and data tools, available without an internet connection." \
    org.opencontainers.image.source="https://github.com/ToBeHH/homeassistant-apps" \
    org.opencontainers.image.licenses="MIT"
