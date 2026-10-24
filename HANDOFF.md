# Handoff – Stand 24.10.2026 (nach Phase 2.5)

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
- Dienst `rootfs/etc/services.d/zimi/run`: `ZIMI_DATA_DIR=/data/zimi`, `ZIMI_OFFLINE=1`, `ZIMI_BT=off`, `ZIMI_NEARBY=off`,
  `ZIMI_MANAGE=0`, `ZIMI_AUTO_UPDATE=0`.
- Healthcheck auf `/health`, `backup_exclude` für Zimis Indizes/Caches.
- Lokal getestet (Docker): Build 159 MB, `/health`, Suche in einer kleinen ZIM,
  Start mit `--network none`, RAM ca. 55–65 MiB. **Nicht** getestet: bashio und Healthcheck
  unter dem Supervisor – beim ersten Test auf dem HA-Host prüfen.

## Phase 2.2 – erledigt (Zimi-Konfiguration)

- `<data_path>/zim` ist für Zimi ein **zusätzlicher Bibliotheksordner**
  (`ZIMI_EXTRA_ZIM_DIRS`): alle 30 s beobachtet, nie beschrieben, Updates als Tausch
  ohne Lücke. `ZIM_DIR` ist ein leerer Ordner im Container.
- `ZIMI_MANAGE=0` schaltet `/manage/*` ganz ab (404). Deshalb **keine** Optionen für
  Passwort und API-Token, beide wirken in Zimi nur dort. Lesen offen
  (`ZIMI_PUBLIC_ACCESS=open`), Schutz über Ingress und den MCP-Token.
- `zimi.outbound.inventory()` zeigt mit unseren Einstellungen alle ausgehenden
  Verbindungen auf „off“.
- Lokal getestet: Datei beim Start, Hinzufügen, Ersetzen, Löschen.

## Phase 2.2a – erledigt (Downloader, Offline Knowledge 0.2.0)

- Python-Paket `offline_knowledge/downloader/okdl/` (nur stdlib), im Image unter
  `/opt/okdl`, s6-Dienst `downloader`. Ablauf je Durchlauf: Speicherort prüfen →
  Katalog → Plan (`plan.py`) → Platz-Check → Downloads (kleinste zuerst) → Aufräumen.
- Profile in `okdl/profiles.json`. Status in `/data/downloader/status.json`.
- Neue Optionen `download_window`, `download_limit`; optionaler Port 8899 für Zimi.
- Healthcheck jetzt als Docker-`HEALTHCHECK` (App-Linter lehnt `watchdog` ab – das war
  der rote CI-Lauf nach dem Push von 0.1.0).
- Getestet: 41 Unit-Tests (macOS Python 3.15 und Image-Python 3.12); im Image Ende-zu-
  Ende mit echtem Katalog und Mirror (`devdocs_en_bash`), Zimi übernimmt die Datei nach
  ~45 s. App-Linter-Regeln lokal nachgebaut (`uv run --with jsonschema --with pyyaml`
  mit `src/lint.py` und `src/config.schema.json` aus `frenck/action-addon-linter`).

## Phase 2.5 – erledigt (Startseite/Ingress, Offline Knowledge 0.3.0)

- Zimi kann nicht unter dem Ingress-Präfix laufen (absolute Pfade überall). Ingress
  zeigt eine eigene Startseite (nginx, Port 8099), Zimi bleibt auf dem optionalen Port
  8899; die Startseite verlinkt `http://<host>:<port>/`, wenn der Port gesetzt ist.
- Startseite: Status je Quelle mit Fortschritt, Speicherplatz, Bibliotheksgröße,
  Hinweis bei fehlendem Speicherort. Lokal im Browser geprüft (Desktop und 400 px).
- Lokal bestätigt: Ohne die 60 s Wartezeit im `downloader`-Dienst fällt eine Datei in
  Zimis Startlücke – die Wartezeit ist also nötig.

## Nächster Schritt: Test auf dem HA-Host

Test über das GHCR-Image:
1. Repo in HA hinzufügen, App installieren.
2. `data_path` auf einen existierenden Ordner (z. B. auf der externen Platte unter
   `/media/…`), Profil `custom`, `zim_sources: [devdocs_en_bash]`, unter Netzwerk einen
   Port für 8899 setzen.
3. Prüfen: Startseite in der Seitenleiste, Log beider Dienste, Healthcheck, Link
   „Open library“, dann Profil `slim` mit Zeitfenster/Limit.

Offen danach: CyberChef (2.3), Karten (2.4), MCP (2.6), `addon_stdin` für manuelles
Update (4).

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
- Neue/entfernte ZIM-Dateien: Watcher für `ZIMI_EXTRA_ZIM_DIRS` (siehe Phase 2.2)

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
