# Handoff – Stand 24.10.2026 (nach Phase 2.1)

Übergabe aus der Claude-Chat-Sitzung an die Weiterarbeit in VS Code (mit Claude Code).
Projektregeln stehen in [CLAUDE.md](CLAUDE.md), der Plan in [TODO.md](TODO.md).

## Wo wir stehen

- **Phase 0 (Entscheidungen D1–D9):** komplett entschieden, siehe TODO.md.
- **Phase 1 (Repo-Grundgerüst):** fertig.
  - `4328a7c` Initiales Gerüst (beide Apps, CI, Renovate) – gepusht
  - `797f1b8` Repo-Name `homeassistant-apps`, Build-Bedingung, Lint-Fixes – gepusht
  - `04ce004` Handoff-Commit (CLAUDE.md, HANDOFF.md) – gepusht; Lint und Builder grün
- Lokaler Ordner heißt jetzt `~/Dev/ToBeHH/homeassistant-apps` (vorher
  `homeassistant-addons-public`).

## Sofort erledigen

1. ~~`git push`~~ erledigt
2. ~~CI prüfen~~ erledigt: Lauf zu `04ce004` – Lint grün, Builder grün und hat gebaut.
3. GitHub → Packages: `ha-app-offline-knowledge` und `ha-app-kolibri` auf **public** stellen.
4. Optional: Renovate-App für das Repo aktivieren.

## Phase 2.1 – erledigt (Offline Knowledge 0.1.0)

Entscheidung: **HA-Base-Image + Zimi per pip** (Details in TODO.md 2.1).
- `pip install --no-deps zimi libzim certifi` in `/opt/zimi`; libtorrent/zeroconf fehlen
  absichtlich (in Zimi optionale Imports).
- Dienst `rootfs/etc/services.d/zimi/run`: setzt `ZIM_DIR=<data_path>/zim` (sonst leerer
  Ordner), `ZIMI_DATA_DIR=/data/zimi`, `ZIMI_OFFLINE=1`, `ZIMI_BT=off`, `ZIMI_NEARBY=off`,
  `ZIMI_MANAGE=0`, `ZIMI_AUTO_UPDATE=0`.
- Watchdog auf `/health`, `backup_exclude` für Zimis Indizes/Caches.
- Lokal getestet (Docker): Build 159 MB, `/health`, Suche in einer kleinen ZIM,
  Start mit `--network none`, RAM ca. 55–65 MiB. **Nicht** getestet: bashio und Watchdog
  unter dem Supervisor – beim ersten Test auf dem HA-Host prüfen.

## Nächster Schritt: Phase 2.2 – Zimi-Konfiguration

- `ZIMI_API_TOKEN` (und ggf. `ZIMI_MANAGE_PASSWORD`) als App-Optionen
- Rescan klären: Zimi hat interne Funktionen „register/unregister without a library
  rescan“ (`zimi/server.py`, ca. Zeile 4100–4480) – prüfen, ob es dafür einen
  HTTP-Endpunkt gibt (OpenAPI unter `/openapi.json`), sonst Neustart des Dienstes
- Zimi kennt `ZIMI_TRUSTED_PROXIES` – für Ingress (2.5) relevant
- Danach 2.2a (eigener Downloader). Katalog: `https://library.kiwix.org/catalog/v2/entries`
  (leitet um, `curl -L`); Einträge haben `<name>` und `.meta4`-Links.

## Wissen aus der Recherche

**Zimi** (https://github.com/epheterson/Zimi, MIT, Ein-Personen-Projekt, häufige Releases;
Stand 24.10.2026: 1.14.1)
- Docker: `epheterson/zimi`, Port 8899, `/zims` (ZIM-Dateien), `/config` (Cache, Indizes,
  Einstellungen)
- Wichtige Env-Variablen: `ZIM_DIR`, `ZIMI_DATA_DIR`, `ZIMI_BT` (Standard **an** →
  `off` setzen), `ZIMI_NEARBY` (Standard aus), `ZIMI_MANAGE` (`0` = Bibliotheksverwaltung
  aus), `ZIMI_MANAGE_PASSWORD`, `ZIMI_API_TOKEN`, `ZIMI_AUTO_UPDATE` (aus lassen, das macht
  unser Downloader), `ZIMI_RATE_LIMIT`
- API u. a.: `/search`, `/read`, `/chunks`, `/suggest`, `/list`, `/health`, `/openapi.json`
- MCP: nur stdio, `python3 -m zimi.mcp_server`; Tools u. a. `search`, `read`, `get_chunks`,
  `suggest`, `list_sources`, `deep_search`. → Für D4 eine stdio→Streamable-HTTP-Bridge
  mit Bearer-Token im Container.
- Offen: Wie liest Zimi neue/entfernte ZIM-Dateien ein (Rescan-API, Signal, Neustart)?

**Kiwix-Inhalte**
- Varianten: `maxi` (voll), `nopic` (ohne Bilder, ca. 75 % kleiner), `mini` (nur
  Einleitung + Infobox, ca. 95 % kleiner)
- Größen: Wikipedia EN maxi ca. 111 GB (08/2025), EN nopic ca. 46 GB (2022); DE geschätzt
  40–50 GB maxi. Weitere Größen in TODO.md (D9).
- `download.kiwix.org` blockt automatisierte Abrufe per robots.txt für Web-Crawler; der
  Downloader nutzt den OPDS-Katalog (`library.kiwix.org`) und die Mirror-Links. Prüfsummen
  und `.torrent` liegen neben den Dateien.

**Protomaps**
- Planet-Datei ca. 120 GB (Zoom 0–15); `pmtiles extract <planet-url> out.pmtiles
  --bbox=… --maxzoom=…` lädt nur den Ausschnitt. Jede Zoomstufe weniger halbiert ungefähr
  die Größe; Welt bis Zoom 6 ca. 60 MB.
- Viewer offline: MapLibre GL JS + pmtiles.js + Protomaps-Basemap-Stil; **Fonts und
  Sprites lokal** mitliefern.

**Kolibri**
- Import per `kolibri manage importchannel network <id>` / `importcontent`;
  `KOLIBRI_HOME` für Daten; `KOLIBRI_URL_PATH_PREFIX` für Ingress testen.
- Khan Academy EN ca. 40–55 GB (ältere Angabe).

**Home Assistant Apps**
- Referenz: https://github.com/home-assistant/apps-example und
  https://developers.home-assistant.io/docs/apps/
- `build.yaml` ist abgekündigt; Basis-Image als `BUILD_FROM`-Default im Dockerfile.
- Fremde Container neben dem Supervisor machen HAOS „unsupported“ – deshalb alles in
  den Apps.

## Bewusste Abweichungen vom ursprünglichen Plan

- Repo heißt `ToBeHH/homeassistant-apps` (nicht `homeassistant-addons-public`).
- Profilwerte englisch (`slim`/`standard`/`full`/`custom`); öffentliche Vorgabe `slim`
  mit `en`. Eigener Betrieb: `full`, `de` + `en`, externe Platte.
- Kein `build.yaml` (s. o.).

## Lokal testen

Kein HA-Host nötig für Build und Lint (siehe CLAUDE.md). Für einen echten Test als lokale
App: Ordner nach `/addons` auf den HA-Host kopieren und in `config.yaml` die Zeile `image:`
vorübergehend entfernen, damit HA lokal baut (TODO 6). Alternativ der Devcontainer aus
dem apps-example-Repo.
