# TODO – Offline Knowledge Add-ons

Plan für die Umsetzung. Erst Abschnitt 0 entscheiden, dann der Reihe nach abarbeiten.
Jede Phase endet mit einem lauffähigen, getesteten Zwischenstand.

Legende: `[ ]` offen · `[x]` erledigt · `[?]` Entscheidung nötig

---

## 0. Entscheidungen (vor dem Start)

- [x] **D1 Repository.** Neues öffentliches Repo `ToBeHH/homeassistant-apps`
  (dieses hier) oder die Add-ons ins bestehende `ToBeHH/homeassistant-addons` legen.
  *Vorschlag:* neues Repo, wie angelegt.
  --> Neues Repository
- [x] **D2 Namen.** Add-on-Slugs `offline_knowledge` („Offline Knowledge“) und `kolibri`.
  Kein „NOMAD“ im Namen, weil Project NOMAD™ eine Marke ist.
  --> Ok
- [x] **D3 Kern der Bibliothek.** Zimi statt kiwix-serve.
  *Begründung:* Bibliotheksverwaltung (Auswahl nach Sprache und Inhalt, Downloads,
  Auto-Update), deutsche Oberfläche, Such-API und MCP-Server sind eingebaut.
  *Risiko:* Ein-Personen-Projekt mit sehr schnellen Releases → Version fest pinnen,
  Updates bewusst übernehmen. *Fallback:* kiwix-serve nutzt dieselben ZIM-Dateien,
  ein Wechsel ist jederzeit ohne neue Downloads möglich.
  *Ergänzung:* Inhaltsauswahl und Downloads über einen **eigenen, engine-unabhängigen
  Downloader** (Kiwix-Katalog → ZIM-Dateien) statt über Zimis Bibliotheksverwaltung.
  Zimi liefert dann nur Oberfläche, Suche, API und MCP; ein Wechsel auf kiwix-serve
  betrifft nur noch diese Schicht.
  --> Entschieden: Zimi + eigener Downloader
- [x] **D4 MCP-Transport.** *Entschieden: (a).* Zimis MCP-Server spricht nur stdio. Optionen:
  - (a) im Container über eine stdio→HTTP-Bridge (Streamable HTTP) auf eigenem Port,
    abgesichert mit Bearer-Token. Jeder Client im Netz kann ihn nutzen
    (Claude Desktop, Open WebUI, …).
  - (b) eigener schlanker MCP-Server auf dem Client-Rechner, der Zimis REST-API abfragt.
  --> Option a
- [x] **D5 Kolibri-MCP.** Kolibri-Inhalte sind vor allem Videos und Übungen; der Nutzen
  eines MCP ist gering. *Vorschlag:* zunächst ohne, später ggf. Themen-/Kanalsuche.
  --> OK, erst einmal ohne MCP
- [x] **D6 Speicherort.** Option `data_path` pro Add-on. Start auf `/share/offline_knowledge`
  (interne Platte), später Umzug auf externe Platte unter `/media/<label>`.
  Klären, wie HAOS die USB-Platte einbindet; Alternative: NAS-Freigabe als
  HA-Netzwerkspeicher.
  --> Ja, Speicherort muss Konfigurierbar sein. Und zwar bevor der Download beginnt.
- [x] **D7 Build.** Images per GitHub Actions bauen und auf GHCR veröffentlichen
  (`image:` in `config.yaml`) statt lokal auf dem HA-Host bauen zu lassen.
  *Vorschlag:* GHCR – schnellere Updates, kein Build-Aufwand auf dem Host,
  passt zu automatischen nächtlichen Add-on-Updates.
  --> Passt.
- [x] **D8 Architektur.** Zunächst nur `amd64`; `aarch64` später, falls gewünscht.
  --> OK
- [x] **D9 Standardauswahl.** Alle Inhalte sind über die Add-on-Optionen konfigurierbar
  (Abschnitt 2.2, 2.4, 3); hier geht es nur um die Voreinstellung beim ersten Start.
  Grobe Größen (✔ = belegt, ~ = Schätzung; genaue Werte in Phase 2 nachtragen):

  | Inhalt | Größe |
  | --- | --- |
  | Wikipedia EN maxi (mit Bildern) | ✔ ca. 111 GB (Stand 08/2025) |
  | Wikipedia EN nopic | ✔ ca. 46 GB (Stand 2022), heute eher ~50 GB |
  | Wikipedia EN mini (nur Einleitungen) | ~ 10–15 GB |
  | Wikipedia DE maxi | ~ 40–50 GB |
  | Wikipedia DE nopic | ~ 15–20 GB |
  | Wikipedia DE mini | ~ 3–5 GB |
  | Wiktionary DE, WikiMed, iFixit | ~ je wenige GB |
  | Karten Welt bis Zoom 6 (Übersicht) | ✔ ca. 60 MB |
  | Karten Deutschland, volle Detailtiefe | ~ 3–5 GB |
  | Karten Europa, volle Detailtiefe | ~ 30–50 GB |
  | Karten Welt, volle Detailtiefe | ✔ ca. 120 GB |
  | Kolibri Khan Academy EN | ✔ ca. 40–55 GB (ältere Angabe) |
  | Kolibri Khan Academy DE | ~ deutlich kleiner; Teilimport einzelner Themen möglich |

  Jede Zoomstufe weniger halbiert die Kartengröße ungefähr.

  Profile als Vorschlag:
  - *Schlank* (~25–35 GB): Wikipedia DE nopic + EN mini, Wiktionary DE, WikiMed,
    Karten Welt Z6 + Deutschland
  - *Standard* (~120–150 GB): Wikipedia DE maxi + EN nopic, Extras, Karten Welt Z6 + Europa
  - *Voll* (~250–350 GB, externe Platte): Wikipedia DE + EN maxi, Extras,
    Karten Europa, Kolibri Khan Academy DE + EN
  --> Entschieden: Profile werden als Option `profile` (`slim`/`standard`/`full`/`custom`;
      englisch, weil das Repo öffentlich ist) umgesetzt und sind später umstellbar. Eigener Betrieb: externe Platte,
      Profil *Voll*, Wikipedia DE + EN.

## 1. Repo-Grundgerüst

- [x] Ordner, `repository.yaml`, `README.md`, `LICENSE` (MIT), `.gitignore`, `git init`
- [x] Gerüst je Add-on: `config.yaml`, `Dockerfile`, `README.md`, `DOCS.md`,
      `CHANGELOG.md`, `icon.png`/`logo.png`, `translations/de.yaml` + `en.yaml`,
      s6-Dienst als Platzhalter mit Speicherort-Prüfung.
      `build.yaml` entfällt: HA hat es abgekündigt, das Basis-Image steht jetzt als
      `BUILD_FROM`-Default im `Dockerfile`.
- [x] GitHub-Repo anlegen (öffentlich) und pushen
- [x] CI: Lint (`frenck/action-addon-linter`, hadolint, yamllint, shellcheck)
- [x] CI: Build & Push der Images nach GHCR mit den neuen
      `home-assistant/builder/actions/*` (D7); Images `ghcr.io/tobehh/ha-app-<name>`
- [x] Renovate-Konfiguration für Actions, Basis-Images und per `# renovate:`-Kommentar
      gepinnte Versionen (Zimi, CyberChef, pmtiles, MapLibre, Kolibri)
- [ ] Renovate-App für das Repo aktivieren (manuell auf GitHub)
- [ ] GHCR-Pakete nach dem ersten Build auf „public“ stellen (manuell auf GitHub),
      sonst kann Home Assistant die Images nicht laden
- [ ] Optional: AppArmor-Profil je App

## 2. Add-on „Offline Knowledge“

### 2.1 Basis
- [x] Basis-Image festlegen: Zimi-Image (gepinnt) erweitern vs. HA-Base-Image + Zimi
      per pip. Prüfen: libzim/libtorrent-Abhängigkeiten, Größe, bashio verfügbar.
      --> Entschieden: HA-Base-Image 3.23 (Alpine, Python 3.12) + Zimi per pip in
      `/opt/zimi` mit `--no-deps`. libzim hat musllinux-Wheels; libtorrent und zeroconf
      sind in Zimi optionale Imports und werden gar nicht installiert (kein BitTorrent,
      kein UPnP, kein Nearby möglich). Image 159 MB statt ca. 1 GB (Zimi-Image bringt
      Chromium, Node, ffmpeg, TTS mit). RAM im Leerlauf ca. 55–65 MiB.
- [x] Prozessverwaltung für mehrere Dienste (Zimi, nginx, MCP-Bridge, Update-Jobs),
      z. B. s6-overlay
      --> s6-overlay aus dem HA-Base-Image, je Dienst ein Ordner unter
      `rootfs/etc/services.d/` (erster Dienst: `zimi`)
- [x] Optionen aus `/data/options.json` lesen, Schema in `config.yaml`
      --> per `bashio::config`; Schema stand seit Phase 1
- [x] Kein Download, solange `data_path` nicht ausdrücklich gesetzt ist und der Pfad
      existiert/beschreibbar ist (D6); stattdessen Hinweis in Log und Landing-Page
      --> Log erledigt; Zimi startet dann mit leerem Ordner. Landing-Page folgt in 2.5.
- [x] `backup_exclude` für Inhalte und Indizes; Konfiguration bleibt im Backup
      --> Zimi-Daten unter `/data/zimi`, Indizes/Caches ausgeschlossen. Inhalte liegen
      in `data_path` (unter `/share` bzw. `/media`) und damit gar nicht im App-Backup;
      im vollen HA-Backup muss man den Ordner selbst abwählen (in DOCS.md vermerkt).
- [x] Watchdog/Healthcheck (Zimi `/health`)
      --> `watchdog: http://[HOST]:[PORT:8899]/health` in `config.yaml`
- [ ] Auf echtem HA-Host testen (bashio/Supervisor-API und Watchdog lassen sich lokal
      nicht prüfen; lokal getestet: Build, `/health`, Suche, Start ohne Netzwerk)

### 2.2 Bibliothek (Zimi)
- [ ] `ZIM_DIR` → `<data_path>/zim`, `ZIMI_DATA_DIR` → persistenter Pfad
- [ ] Sicherheits-Defaults: BitTorrent aus (`ZIMI_BT=off`, kein UPnP), Nearby aus,
      `ZIMI_MANAGE_PASSWORD` und `ZIMI_API_TOKEN` aus Add-on-Optionen
      (Teilweise in 2.1: `ZIMI_OFFLINE=1`, `ZIMI_BT=off`, `ZIMI_NEARBY=off`,
      `ZIMI_MANAGE=0`, `ZIMI_AUTO_UPDATE=0` gesetzt; Token/Passwort fehlen noch)
- [ ] Zimis eigene Bibliotheksverwaltung deaktivieren bzw. absichern
      (`ZIMI_MANAGE=0` prüfen), Auto-Update von Zimi aus – das übernimmt der Downloader
- [ ] Zimi nach neuen/entfernten ZIM-Dateien neu einlesen lassen (Mechanismus klären:
      Rescan-API, Signal oder Neustart des Zimi-Prozesses)

### 2.2a Downloader (eigen, engine-unabhängig)
- [ ] Kiwix-Katalog (OPDS) lesen; ZIM-Namen ohne Datum (z. B. `wikipedia_de_all_maxi`)
      auf die jeweils neueste Datei auflösen
- [ ] Optionen: `profile` (`slim`/`standard`/`full`/`custom`), `languages`
      (z. B. `de`, `en`), `zim_sources` (Zusatzliste bzw. vollständige Liste bei `custom`)
- [ ] Profile als Datei im Repo definieren (Profil × Sprache → ZIM-Namen), damit
      Anpassungen ohne Codeänderung möglich sind
- [ ] Abgleich Soll/Ist: fehlende laden, veraltete ersetzen, abgewählte entfernen
      (Entfernen nur nach Option `prune: true`)
- [ ] Download robust: fortsetzbar (HTTP Range), Prüfsumme (SHA-256/MD5 vom Mirror),
      erst in `.part`, dann atomar umbenennen; alte Version erst danach löschen
- [ ] Speicherplatz-Check vor jedem Download (Summe aller geplanten Downloads + Puffer)
- [ ] Bandbreite/Zeitfenster als Option (nachts)
- [ ] Status als JSON-Datei für Landing-Page und Log (geplant, läuft, fertig, Fehler)
- [ ] Unit-Tests für Katalog-Auflösung und Abgleich

### 2.3 CyberChef
- [ ] Release-ZIP beim Image-Build laden (Version gepinnt, Prüfsumme)
- [ ] Statisch über nginx unter `/cyberchef/` ausliefern

### 2.4 Karten (Protomaps)
- [ ] Viewer: MapLibre GL JS + pmtiles.js + Protomaps-Basemap-Stil,
      **Fonts und Sprites lokal** mitliefern (sonst nicht offline)
- [ ] Option `map_regions` (vordefinierte Regionen und/oder Bounding-Box)
- [ ] Extrakt mit `pmtiles extract` aus dem aktuellen Protomaps-Build erzeugen,
      Ablage unter `<data_path>/maps/`
- [ ] Mehrere Regionen im Viewer umschaltbar
- [ ] Optional/später: Offline-Ortssuche (Geocoding)

### 2.5 Startseite und Zugriff
- [ ] Landing-Page (nginx) mit Links zu Bibliothek, Karten, CyberChef und Status
      (Speicher, letzte Aktualisierung)
- [ ] HA-Ingress als Hauptzugang (HA-Login inklusive); relative Pfade testen.
      Prüfen, ob Zimi unter Ingress-Pfad läuft – sonst eigener Port für Zimi.
- [ ] Optionale LAN-Ports (Zimi, MCP) in `config.yaml`, standardmäßig aus
- [ ] Nicht fürs Internet gedacht: in DOCS.md deutlich dokumentieren

### 2.6 MCP-Server
- [ ] Umsetzung gemäß D4, Token-Pflicht
- [ ] Tools durchreichen: `search`, `read`, `get_chunks`, `suggest`, `list_sources`,
      `deep_search`, …
- [ ] Test mit Claude Desktop und Open WebUI
- [ ] Optional/später: Karten-Tool (Ortssuche), sobald Geocoding da ist

### 2.7 Ressourcen
- [ ] RAM/CPU im Leerlauf und bei Suche messen, Ergebnis in DOCS.md

## 3. Add-on „Kolibri“

- [ ] Image: Kolibri per pip (gepinnt) auf HA-Base-Image
- [ ] `KOLIBRI_HOME`: Datenbank unter `/data`, Inhalte unter `<data_path>/kolibri`
- [ ] Ersteinrichtung automatisieren (`provisiondevice`: Facility, Admin aus Optionen)
- [ ] Option `channels` (Channel-IDs) + Sprache; Import per
      `kolibri manage importchannel network …` / `importcontent`
- [ ] Ingress mit URL-Präfix testen (`KOLIBRI_URL_PATH_PREFIX`)
- [ ] `backup_exclude` für Inhalte
- [ ] RAM/CPU messen
- [ ] MCP gemäß D5

## 4. Update-Mechanismus

Drei Ebenen, getrennt behandelt:

- [ ] **Software (Images):** neue Version im Repo → HA zeigt das Update an;
      automatische Add-on-Updates greifen. Gepinnte Versionen via Renovate (Abschnitt 1).
- [ ] **Inhalte – Bibliothek:** eigener Downloader (2.2a), Frequenz als Option
- [ ] **Inhalte – Karten:** Update-Job (z. B. monatlich) erzeugt neuen Extrakt,
      tauscht ihn atomar aus, löscht den alten erst danach
- [ ] **Inhalte – Kolibri:** Channel-Update-Job
- [ ] Auslösung: Abgleich der Auswahl bei jedem Add-on-Start **plus** Zeitplan im
      Container (nachts, Bandbreite). Manuelles Auslösen über `hassio.addon_stdin`
      (z. B. Kommando `update`), damit es per HA-Skript/Button geht.
- [ ] Kein Download beim Start des MCP-Servers (MCP soll sofort antworten)
- [ ] Log/Status: letzte Aktualisierung und Fehler auf der Landing-Page

## 5. Integration

- [ ] MCP-Endpunkt in Claude Desktop eintragen (Zugriff über VPN, nicht öffentlich)
- [ ] MCP in Open WebUI als Tool anbinden
- [ ] Optional: HA-Sensoren (Speicher, letzte Aktualisierung) und Dashboard-Link

## 6. Test und Release

- [ ] Lokaler Test als lokales Add-on (`/addons`) auf dem HA-Host – erst nach Freigabe
- [ ] Erst mit kleinem ZIM testen, dann große Inhalte laden
- [ ] Umzug der Inhalte auf die externe Platte testen (D6)
- [ ] DOCS.md (Englisch) je Add-on, README aktualisieren
- [ ] Release v0.1.0
