# CLAUDE.md

Guidance for Claude Code (and humans) working in this repository.

## What this is

A Home Assistant **app repository** (Home Assistant renamed "add-ons" to "apps" in 2026).
Two apps bring offline knowledge to a Home Assistant OS host, inspired by Project NOMAD
but built as regular Supervisor-managed apps:

- `offline_knowledge/` – Zimi (Kiwix ZIM library), CyberChef, Protomaps map viewer,
  own content downloader, MCP endpoint
- `kolibri/` – Kolibri learning platform

The plan lives in **[TODO.md](TODO.md)** (German). Work through it phase by phase and tick
items off there. Current state and next steps: **[HANDOFF.md](HANDOFF.md)**.

## Hard constraints

- **Home Assistant OS only.** No Docker socket, no containers outside the Supervisor, no
  privileged mounts of the host filesystem. Everything runs inside the app container.
- **No download before storage is configured.** Nothing is fetched while `data_path` is
  empty, missing or not writable.
- **Content never goes into git or images.** ZIM files, PMTiles, Kolibri channels are
  downloaded at runtime into `data_path` and excluded from HA backups (`backup_exclude`).
- **Local network only.** No telemetry. Zimi's BitTorrent, UPnP and "Nearby" stay off.
- **Public repo.** No IP addresses, host names, VPN details, tokens or personal data in
  commits.

## Conventions

- Code, config, DOCS/README/CHANGELOG: English. TODO.md and HANDOFF.md: German.
- App layout follows the official example (https://github.com/home-assistant/apps-example):
  `config.yaml`, `Dockerfile` with `ARG BUILD_FROM=…` default (no `build.yaml`, it is
  deprecated), `rootfs/` with s6 services under `etc/services.d/`, `translations/{en,de}.yaml`,
  `DOCS.md`, `README.md`, `CHANGELOG.md`, `icon.png` (128×128), `logo.png` (250×100).
- Every change that affects an app image: bump `version` in its `config.yaml` **and** add a
  `CHANGELOG.md` entry, otherwise Home Assistant offers no update.
- Pin third-party versions as `ARG <NAME>_VERSION=…` with a `# renovate: datasource=… depName=…`
  comment on the line above, so Renovate can update them.
- Only `amd64` for now (decision D8).
- Profile values are English: `slim`, `standard`, `full`, `custom`.

## Checks (CI runs the same)

```bash
yamllint --strict .
find . -path '*/rootfs/etc/services.d/*' -type f -print0 | xargs -0 shellcheck -x
hadolint -c .hadolint.yaml offline_knowledge/Dockerfile kolibri/Dockerfile
docker build -t test/offline_knowledge ./offline_knowledge
```

The app linter (`frenck/action-addon-linter`) only runs in CI.

## CI / release

- `.github/workflows/lint.yaml` – app linter, hadolint, yamllint, shellcheck
- `.github/workflows/builder.yaml` + `build-app.yaml` – build changed apps on PRs, build and
  publish to GHCR on push to `main` (`ghcr.io/tobehh/ha-app-<name>`), using
  `home-assistant/builder/actions/*`
- Renovate config in `.github/renovate.json`
