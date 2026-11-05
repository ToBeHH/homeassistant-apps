# shellcheck shell=bash
# ==============================================================================
# Environment for everything that runs Zimi code: the library server and the
# MCP server must see the same library and settings.
# ==============================================================================

declare data_path
declare zim_dir=""

data_path=$(bashio::config 'data_path')
if bashio::var.has_value "${data_path}" && [[ -d "${data_path}" && -w "${data_path}" ]]; then
    zim_dir="${data_path}/zim"
fi

# The downloader owns <data_path>/zim. Zimi reads it as an extra library
# folder: watched every 30 s, never written to. Its own ZIM_DIR stays empty.
mkdir -p /var/lib/zimi/empty /data/zimi
export ZIM_DIR=/var/lib/zimi/empty
export ZIMI_DATA_DIR=/data/zimi
if bashio::var.has_value "${zim_dir}"; then
    mkdir -p "${zim_dir}"
    export ZIMI_EXTRA_ZIM_DIRS="${zim_dir}"
fi

# Nothing in Zimi talks to the internet; downloads are our own job (D3).
export ZIMI_OFFLINE=1
export ZIMI_BT=off
export ZIMI_NEARBY=off
export ZIMI_AUTO_UPDATE=0
# Without /manage there is no login, so reading must stay open. Access control
# is Home Assistant's job (ingress) and the MCP token's.
export ZIMI_MANAGE=0
export ZIMI_PUBLIC_ACCESS=open
