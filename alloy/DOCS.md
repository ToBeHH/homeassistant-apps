# Grafana Alloy

This app runs [Grafana Alloy](https://grafana.com/docs/alloy/) and pushes what it collects to a
central Prometheus (`remote_write`) and Loki over HTTPS. Unlike the other apps in this repository
it is meant to talk to the internet: it sends data to the endpoints you configure, nothing else.

What it collects:

| Source | Metrics / logs |
| --- | --- |
| Alloy itself | always, gives an `up` series to detect a silent site |
| Home Assistant | `/api/prometheus` of the `prometheus` integration, through the Supervisor (no long-lived token) |
| Host journal | Home Assistant OS journal including the logs of all apps and Core |
| SNMP targets | e.g. a NAS: `if_mib` (network) and `hrStorage` (volume usage) by default |
| FRITZ!Box | TR-064 via [fritz-exporter](https://github.com/pdreker/fritz_exporter), when `fritzbox_host` is set |

## Setup

1. Enable the Prometheus integration in `configuration.yaml` and restart Home Assistant:

   ```yaml
   prometheus:
     namespace: hass
   ```

2. Set `remote_write_url`, `loki_url`, `token`, `site` and `collector` and start the app. Without
   `remote_write_url` and `token` Alloy does not start.
3. Optional: add SNMP targets and the FRITZ!Box (see below).

## Options

| Option | Meaning |
| --- | --- |
| `remote_write_url` | Prometheus remote_write endpoint, e.g. `https://example.org/api/v1/write` |
| `loki_url` | Loki push endpoint, e.g. `https://example.org/loki/api/v1/push`; empty = no logs |
| `token` | Bearer token for both endpoints |
| `site`, `collector` | External labels added to everything sent; used for alerting on silent sites |
| `home_assistant_metrics` | Scrape Home Assistant (default on) |
| `journal_logs` | Send the host journal to Loki (default on) |
| `snmp_targets` | List of `name`, `address`, optional `community` (default `public`, SNMPv2c) and `modules` (default `if_mib,hrStorage`) |
| `fritzbox_host`, `fritzbox_user`, `fritzbox_password` | FRITZ!Box address and a user with the right "FRITZ!Box settings" |

## FRITZ!Box user

In the FRITZ!Box under **System > FRITZ!Box Users** add a user (e.g. `monitoring`) with the right
**FRITZ!Box Settings** only, and enable **Home Network > Network > Network Settings > Allow access
for applications** (TR-064).

## Buffering

Alloy keeps a write-ahead log in the app's data folder and sends buffered samples once the endpoint
is reachable again. It is excluded from backups.
