# Handoff – Stand 24.10.2026

Übergabe aus der Claude-Chat-Sitzung an die Weiterarbeit in VS Code (mit Claude Code).
Projektregeln stehen in [CLAUDE.md](CLAUDE.md), der Plan in [TODO.md](TODO.md).

## Wo wir stehen

- **Phase 0 (Entscheidungen D1–D9):** komplett entschieden, siehe TODO.md.
- **Phase 1 (Repo-Grundgerüst):** fertig.
  - `4328a7c` Initiales Gerüst (beide Apps, CI, Renovate) – gepusht
  - `797f1b8` Repo-Name `homeassistant-apps`, Build-Bedingung, Lint-Fixes – **noch nicht gepusht**
  - Handoff-Commit (CLAUDE.md, HANDOFF.md) – **noch nicht gepusht**
- Lokaler Ordner heißt jetzt `~/Dev/ToBeHH/homeassistant-apps` (vorher
  `homeassistant-addons-public`).

## Sofort erledigen

1. `git push`
2. CI prüfen: **Lint** muss grün sein, **Builder** muss diesmal wirklich bauen und pushen.
   Der erste Builder-Lauf war grün, hat aber nichts gebaut (Bedingung prüfte auf einen
   falschen Repo-Namen; mit `797f1b8` behoben). ShellCheck-Ergebnis des ersten Laufs ist
   unbekannt.
3. GitHub → Packages: `ha-app-offline-knowledge` und `ha-app-kolibri` auf **public** stellen.
4. Optional: Renovate-App für das Repo aktivieren.

## Nächster Schritt: Phase 2.1 – Basis-Image für „Offline Knowledge“

Zu entscheiden: Zimi-Image (`epheterson/zimi`, gepinnt) erweitern **oder** HA-Base-Image
(`ghcr.io/home-assistant/base:3.23`, Alpine) + Zimi per pip.

Prüfen:
- Läuft Zimi auf Alpine/musl? (libzim- und libtorrent-Wheels; BitTorrent brauchen wir nicht)
- bashio und s6-overlay sind im HA-Base-Image enthalten, im Zimi-Image nicht
- Image-Größe, RAM im Leerlauf (Zielhost hat nur wenige GB RAM frei)

Danach 2.2 (Zimi-Konfiguration) und 2.2a (eigener Downloader).

## Wissen aus der Recherche

**Zimi** (https://github.com/epheterson/Zimi, MIT, Ein-Personen-Projekt, häufige Releases;
Stand Okt. 2026: 1.13.3)
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
