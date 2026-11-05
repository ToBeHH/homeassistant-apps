# shellcheck shell=bash
# ==============================================================================
# Environment for everything that runs Kolibri code.
# ==============================================================================

declare data_path
declare zip_host_port
declare zip_internal_port=18081

# Kolibri refuses to start without a time zone.
export TZ="${TZ:-UTC}"

export KOLIBRI_HOME=/data/kolibri
mkdir -p "${KOLIBRI_HOME}"

# Local network only: no statistics ping, no announcing on the network.
export KOLIBRI_DISABLE_PING=true
export KOLIBRI_ZEROCONF_ENABLED=false

KOLIBRI_URL_PATH_PREFIX="$(bashio::app.ingress_entry)/"
export KOLIBRI_URL_PATH_PREFIX

# HTML5 content comes from a second origin, reached directly by the browser on
# the port Kolibri itself listens on. So Kolibri must use the number of the host
# port; nginx forwards the container's 8081 to it. (ZIP_CONTENT_ORIGIN would be
# made for this, but a port number there crashes Kolibri 0.19 in its CSP code.)
zip_host_port=$(bashio::app.port "8081/tcp")
case "${zip_host_port}" in
    "" | null) ;;
    8080 | 8099 | 18080)
        bashio::log.warning "Port ${zip_host_port} can't be used for 8081/tcp, please choose another one."
        ;;
    *) zip_internal_port="${zip_host_port}" ;;
esac

data_path=$(bashio::config 'data_path')
if bashio::var.has_value "${data_path}" && [[ -d "${data_path}" && -w "${data_path}" ]]; then
    mkdir -p "${data_path}/kolibri"
    export KOLIBRI_CONTENT_DIR="${data_path}/kolibri"
fi

export PYTHONUNBUFFERED=1
cd "${KOLIBRI_HOME}" || bashio::exit.nok "Cannot enter ${KOLIBRI_HOME}"
