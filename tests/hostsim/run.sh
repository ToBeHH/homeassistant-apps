#!/usr/bin/env bash
# ==============================================================================
# Starts an app image with its real s6 init and bashio next to a fake Supervisor
# and ingress proxy, as on a Home Assistant host, and checks that it comes up.
#
#   tests/hostsim/run.sh <app> <image> [apparmor profile]
#
# Leaves the containers running with KEEP=1; ingress is then on localhost:28123.
# OPTIONS=<file> replaces the app options. PUBLISH="-p 1:2" adds docker run flags.
# ==============================================================================
set -euo pipefail

app=$1
image=$2
profile=${3:-}
here=$(cd "$(dirname "$0")" && pwd)
work=$(mktemp -d)
timeout=${TIMEOUT:-300}

cleanup() {
    if [[ -z "${KEEP:-}" ]]; then
        docker rm -f hostsim-app hostsim-sup >/dev/null 2>&1 || true
        docker network rm hostsim >/dev/null 2>&1 || true
        rm -rf "${work}" 2>/dev/null || true
    fi
}
trap cleanup EXIT
docker rm -f hostsim-app hostsim-sup >/dev/null 2>&1 || true
docker network rm hostsim >/dev/null 2>&1 || true

mkdir -p "${work}/data" "${work}/share/sim"
options=${OPTIONS:-${here}/${app}/options.json}
cp "${options}" "${work}/data/options.json"

# Apps with ingress bring nginx and python3, so the fake Supervisor runs in their image. Apps
# without ingress (marker file no-ingress) get a plain Python image and no ingress check.
ingress=1
sup_image=${image}
sup_cmd='nginx -c /ingress.conf; exec python3 /fake_supervisor.py'
if [[ -f "${here}/${app}/no-ingress" ]]; then
    ingress=0
    sup_image=${SUP_IMAGE:-python:3.13-alpine}
    sup_cmd='exec python3 /fake_supervisor.py'
fi

docker network create --subnet 172.30.32.0/24 --gateway 172.30.32.254 hostsim >/dev/null
docker run -d --name hostsim-sup --network hostsim --ip 172.30.32.2 \
    --network-alias supervisor -p 28123:8123 \
    -v "${here}/fake_supervisor.py:/fake_supervisor.py:ro" \
    -v "${here}/ingress.conf:/ingress.conf:ro" \
    -v "${here}/${app}/info.json:/sim/info.json:ro" \
    -v "${options}:/sim/options.json:ro" \
    --entrypoint sh "${sup_image}" \
    -c "${sup_cmd}" >/dev/null

# The app asks the Supervisor right at start; wait until the fake one answers.
for _ in $(seq 1 30); do
    docker exec hostsim-sup python3 -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1/info")' \
        >/dev/null 2>&1 && break
    sleep 1
done

security=()
if [[ -n "${profile}" ]]; then
    security=(--security-opt "apparmor=${profile}")
fi
# PUBLISH is meant to split into flags.
# shellcheck disable=SC2086
docker run -d --name hostsim-app --network hostsim --ip 172.30.32.3 \
    -e SUPERVISOR_TOKEN=sim -e TZ=Europe/Berlin ${security[@]+"${security[@]}"} \
    ${PUBLISH:-} \
    -v "${work}/data:/data" -v "${work}/share:/share" "${image}" >/dev/null

logs() {
    docker logs hostsim-app 2>&1 | sed 's/\x1b\[[0-9;]*m//g'
}

deadline=$((SECONDS + timeout))
while :; do
    missing=0
    # Not "logs | grep -q": with pipefail the pipe breaks as soon as grep has its match.
    current=$(logs)
    while IFS= read -r line; do
        grep -qF "${line}" <<< "${current}" || missing=1
    done < "${here}/${app}/expect.txt"
    if [[ "${missing}" == 0 ]]; then
        break
    fi
    if ((SECONDS > deadline)) || [[ "$(docker inspect -f '{{.State.Running}}' hostsim-app)" != "true" ]]; then
        logs | tail -40
        echo "FAILED: expected log lines did not appear" >&2
        exit 1
    fi
    sleep 5
done

if [[ "${ingress}" == 1 ]]; then
    docker exec hostsim-app curl -fsS -o /dev/null http://127.0.0.1:8099/
    code=$(curl -sL -o /dev/null -w '%{http_code}' http://localhost:28123/api/hassio_ingress/TOK/)
    if [[ "${code}" != "200" ]]; then
        logs | tail -40
        echo "FAILED: ingress answered ${code}" >&2
        exit 1
    fi
fi
logs | grep -E "Traceback|Halt app" && {
    echo "FAILED: errors in the log" >&2
    exit 1
}
if [[ "${ingress}" == 1 ]]; then
    echo "OK: ${app} is up, ingress answers"
else
    echo "OK: ${app} is up"
fi
