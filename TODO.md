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
  --> Update 24.10.: Seit Supervisor 2026.10.1 bindet HA lokale Platten (auch USB)
      offiziell ein: *Einstellungen → System → Speicher → Speicher hinzufügen →
      Lokale Festplatte*, Nutzung „Share“ → erscheint als `/share/<name>`.
      Platte muss vorher formatiert sein (ext4 empfohlen), HA formatiert nicht.
      Keine udev-Regel und kein NAS-Umweg nötig.
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
- [x] Renovate-App für das Repo aktivieren (manuell auf GitHub)
      --> Entschieden: Renovate statt Dependabot, das unsere `ARG`-Pins nicht versteht.
      Installation nur für dieses Repo vorbereitet, Passkey-Bestätigung steht aus.
- [x] GHCR-Pakete nach dem ersten Build auf „public“ stellen (manuell auf GitHub),
      sonst kann Home Assistant die Images nicht laden
- [x] AppArmor-Profil je App
      --> `apparmor.txt` je App, vorerst `complain` (Verstöße werden nur geloggt). CI-Job
      lädt sie im erzwingenden Modus und startet die App über `tests/hostsim`.
- [x] AppArmor scharf schalten: `complain` entfernen, sobald CI und ein echter Host sauber sind
      --> Offline Knowledge 0.8.0, Kolibri 0.1.4. CI lief vorher schon im Enforce-Modus grün.
      **Nicht geprüft:** das Audit-Log des Hosts. `ha host logs` zeigt die Meldungen nicht (ein
      absichtlich ausgelöstes Ereignis kam dort nicht an). Nach dem Update Start, Downloads und
      Ortssuche auf dem Host beobachten; bei Problemen `,complain` wieder eintragen.

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
      --> Docker-`HEALTHCHECK` im Dockerfile (der App-Linter lehnt `watchdog` als
      veraltet ab)
- [x] Auf echtem HA-Host testen (bashio/Supervisor-API und Watchdog lassen sich lokal
      nicht prüfen; lokal getestet: Build, `/health`, Suche, Start ohne Netzwerk)
      --> 0.4.0 aus dem Repo installiert: Status „healthy“; ohne Speicherort kein
      Download, Hinweis in Log und auf der Startseite; `prune` entfernt abgewählte Datei.
- [x] Im Browser prüfen: Startseite und Karten-Viewer über Ingress (Range-Anfragen durch
      den Ingress-Proxy), Zimi über Port 8899 im LAN

### 2.2 Bibliothek (Zimi)
- [x] `ZIM_DIR` → `<data_path>/zim`, `ZIMI_DATA_DIR` → persistenter Pfad
      --> `<data_path>/zim` als `ZIMI_EXTRA_ZIM_DIRS` (s. Rescan), `ZIM_DIR` ist ein
      leerer Ordner im Container, `ZIMI_DATA_DIR=/data/zimi`
- [x] Sicherheits-Defaults: BitTorrent aus (`ZIMI_BT=off`, kein UPnP), Nearby aus,
      `ZIMI_MANAGE_PASSWORD` und `ZIMI_API_TOKEN` aus Add-on-Optionen
      --> `ZIMI_OFFLINE=1`, `ZIMI_BT=off`, `ZIMI_NEARBY=off`. Zimis eigene Liste der
      ausgehenden Verbindungen (`zimi.outbound.inventory()`) zeigt damit alles auf „off“.
      **Abweichung:** Passwort und API-Token entfallen als Optionen. Beide schützen in Zimi
      nur `/manage/*`, und das ist mit `ZIMI_MANAGE=0` ganz abgeschaltet (404). Lesen
      bleibt offen (`ZIMI_PUBLIC_ACCESS=open`); Zugriffsschutz über HA-Ingress (2.5) und
      den Token der MCP-Bridge (2.6).
- [x] Zimis eigene Bibliotheksverwaltung deaktivieren bzw. absichern
      (`ZIMI_MANAGE=0` prüfen), Auto-Update von Zimi aus – das übernimmt der Downloader
      --> `ZIMI_MANAGE=0`: alle `/manage/*`-Pfade liefern 404; `ZIMI_AUTO_UPDATE=0`
- [x] Zimi nach neuen/entfernten ZIM-Dateien neu einlesen lassen (Mechanismus klären:
      Rescan-API, Signal oder Neustart des Zimi-Prozesses)
      --> Kein Signal; `/manage/refresh` gibt es nur mit `ZIMI_MANAGE=1`. Stattdessen:
      Zimi beobachtet Ordner aus `ZIMI_EXTRA_ZIM_DIRS` alle 30 s (`zimi/libfolders.py`),
      schreibt dort nie, übernimmt eine neue Datei erst bei stabiler Größe und tauscht
      eine neue Ausgabe gegen die alte ohne Lücke. Lokal getestet: Hinzufügen, Ersetzen
      (neue Datei rein, alte löschen) und Löschen werden nach 30–60 s übernommen.
      **Lücke:** Was zwischen Start und erstem Watcher-Durchlauf (~30 s) dazukommt, wird
      erst beim nächsten Start erkannt → Regel für den Downloader (2.2a).

### 2.2a Downloader (eigen, engine-unabhängig)

Umgesetzt in Python (nur Standardbibliothek) unter `offline_knowledge/downloader/okdl/`,
Tests unter `offline_knowledge/downloader/tests/` (laufen in CI, Python 3.12 wie im Image).
Eigener s6-Dienst `downloader`, Abgleich beim Start und dann alle 24 h (nach Fehlern
stündlich).

- [x] Kiwix-Katalog (OPDS) lesen; ZIM-Namen ohne Datum (z. B. `wikipedia_de_all_maxi`)
      auf die jeweils neueste Datei auflösen
      --> Gesamtkatalog `…/catalog/v2/entries?count=-1` (4,4 MB, ~3700 Einträge),
      Schlüssel = `name` + `_` + `flavour`; letzte Kopie als Fallback in
      `/data/downloader/catalog.xml`
- [x] Optionen: `profile` (`slim`/`standard`/`full`/`custom`), `languages`
      (z. B. `de`, `en`), `zim_sources` (Zusatzliste bzw. vollständige Liste bei `custom`)
- [x] Profile als Datei im Repo definieren (Profil × Sprache → ZIM-Namen), damit
      Anpassungen ohne Codeänderung möglich sind
      --> `okdl/profiles.json`: je Profil eine Liste pro Sprache, `*` als Vorlage mit
      `{lang}` für alle übrigen Sprachen. Größen (10/2026): slim de 20 / en 25 GB,
      standard de 58 / en 72 GB, full de 73 / en 150 GB. Ausgelassen wegen Größe:
      `gutenberg_en_all` (221 GB).
- [x] Abgleich Soll/Ist: fehlende laden, veraltete ersetzen, abgewählte entfernen
      (Entfernen nur nach Option `prune: true`)
      --> Eine lokal neuere Ausgabe wird nicht durch eine ältere ersetzt. Namen, die
      der Katalog nicht kennt, werden übersprungen und lokal nicht angefasst.
- [x] Download robust: fortsetzbar (HTTP Range), Prüfsumme (SHA-256/MD5 vom Mirror),
      erst in `.part`, dann atomar umbenennen; alte Version erst danach löschen
      (Name muss `<datei>.zim.part` sein, also nicht auf `.zim` enden, sonst sieht Zimi
      die halbe Datei)
      --> Mirrors aus der `.meta4` nach Priorität (nur https), Fallback auf die
      Download-URL; Abbruch mitten im Download → nächster Mirror setzt fort;
      falsche Prüfsumme → `.part` weg, nächster Mirror
- [x] Startlücke des Zimi-Watchers abfangen: in den ersten 60 s nach Zimi-Start nichts
      in `<data_path>/zim` umbenennen, oder nach dem Umbenennen über `/list` prüfen und
      Zimi bei Bedarf neu starten
      --> Dienst `downloader` wartet auf `/health` und dann 60 s
- [x] Speicherplatz-Check vor jedem Download (Summe aller geplanten Downloads + Puffer)
      --> Puffer max(2 GB, 2 %); Gesamtsumme nur als Warnung, je Download wird geprüft
      und übersprungen, was nicht passt (kleinste zuerst)
- [x] Bandbreite/Zeitfenster als Option (nachts)
      --> `download_limit` (KB/s), `download_window` (`HH:MM-HH:MM`, auch über
      Mitternacht); laufender Download pausiert außerhalb und setzt später fort
- [x] Status als JSON-Datei für Landing-Page und Log (geplant, läuft, fertig, Fehler)
      --> `/data/downloader/status.json`
- [x] Unit-Tests für Katalog-Auflösung und Abgleich
      --> 41 Tests inkl. lokalem HTTP-Server mit Range (Fortsetzen, Mirror-Wechsel,
      Prüfsumme, Zeitfenster, Platzmangel, kein Speicherort → keine Anfrage)
- [x] Manuelles Auslösen per `hassio.addon_stdin` (siehe Abschnitt 4)

### 2.3 CyberChef
- [x] Release-ZIP beim Image-Build laden (Version gepinnt, Prüfsumme)
      --> 11.5.0, eigene Build-Stufe `assets` im Dockerfile; SHA-256 aus den
      GitHub-Release-Daten. Der Dateiname enthält einen Commit-Hash, deshalb bei
      Renovate-Updates Dateiname **und** Prüfsumme von Hand nachziehen (Build schlägt
      sonst fehl – gewollt).
- [x] Statisch über nginx unter `/cyberchef/` ausliefern
      --> über Ingress (relative Pfade gehen); `.br` entfernt, `.gz` per `gzip_static`

### 2.4 Karten (Protomaps)
- [x] Viewer: MapLibre GL JS + pmtiles.js + Protomaps-Basemap-Stil,
      **Fonts und Sprites lokal** mitliefern (sonst nicht offline)
      --> `rootfs/var/www/landing/maps/` (über Ingress). MapLibre 6.13 (nur noch ES-Module,
      Worker liegt daneben), pmtiles.js 4.5, basemaps 5.7.2, Noto Sans Regular/Medium/
      Italic + Sprites v4 aus `protomaps/basemaps-assets` (Commit gepinnt). Hell/Dunkel
      nach System, Beschriftung nach Browsersprache. Achtung: Glyph-URL nicht mit
      `new URL()` bauen, das kodiert `{fontstack}`/`{range}`.
- [x] Option `map_regions` (vordefinierte Regionen und/oder Bounding-Box)
      --> `world`, `germany`, `dach`, `europe` (`okdl/regions.json`), Zoom-Override
      `germany:12`, eigener Ausschnitt `name=min_lon,min_lat,max_lon,max_lat[:zoom]`.
      Vorgabe `[world]` (45 MB).
- [x] Extrakt mit `pmtiles extract` aus dem aktuellen Protomaps-Build erzeugen,
      Ablage unter `<data_path>/maps/`
      --> go-pmtiles 1.31.2 (statisch, läuft unter musl). Neuester Build aus
      `build-metadata.protomaps.dev/builds.json`; Größe vorab per `--dry-run`
      (Platz-Check), Extrakt nach `<region>.pmtiles.part`, `pmtiles verify`, dann
      umbenennen; `index.json` beschreibt die Regionen für Viewer und nächsten Lauf.
      Größen (Build 2026-10-24): world z6 45 MB, germany z15 7,4 GB, dach z15 10 GB,
      europe z14 25 GB, europe z15 49 GB.
- [x] Mehrere Regionen im Viewer umschaltbar
      --> Auswahlfeld, detaillierteste Region zuerst, letzte Wahl gemerkt
- [x] Viewer: Welt-Übersicht unter Detailregionen legen (jetzt immer nur eine Quelle)
      --> Zweite Quelle `world` mit eigenem Ebenensatz (`world-*`) unter der Region; deren
      `background` entfällt. Land und Wasser der Region sind deckend. Nur wenn `world` da ist.
- [x] Alle Kontinente in `regions.json`, Zoom 15 als Vorgabe (auch `europe`, vorher 14).
      Größen in DOCS.md. Viewer bis Zoom 20: Vektorkarten bleiben scharf, zeigen aber nicht
      mehr Objekte als bei 15. Höher gehen die Protomaps-Daten nicht.
- [x] Gebäude: direkt von OSM? --> Nicht nötig. Am Rathausmarkt zeigt eine Kachel in Zoom 15
      936 Gebäude-Einträge (inkl. Teile, Hausnummern, Höhen), OSM dort 376 Gebäudeflächen.
      Zoom 14 fasst sie zusammen (79 auf vierfacher Fläche); das war das Problem bei `europe`.
- [x] Optional/später: Offline-Ortssuche (Geocoding)
      --> `okdl/geocode.py`, `okdl/pmread.py`, Option `place_search` (Vorgabe aus).
      `geonames.sqlite` (Orte, PLZ, 2,3 GB, nativ 3,5 min) und `map-<region>.sqlite` (Straßen,
      POIs aus den PMTiles ab Zoom 13, ca. 440 Kacheln/s in dichter Stadt). Zeilen nach
      Wichtigkeit gespeichert, Suche im echten Index meist unter 100 ms. Suchfeld im Viewer.
      Hausnummern nicht: dafür Photon/Nominatim, zu schwer für den Host.

### 2.5 Startseite und Zugriff
- [x] Landing-Page (nginx) mit Links zu Bibliothek, Karten, CyberChef und Status
      (Speicher, letzte Aktualisierung)
      --> `rootfs/var/www/landing/` (statisch, nur relative Pfade), nginx auf 8099 liefert
      `status.json` (Downloader), `info.json` (Version, Host-Port für Zimi, vom
      `run`-Skript per bashio geschrieben) und `library/list`/`library/health` (Zimi).
      Karten/CyberChef als Platzhalter-Karten, Links kommen mit 2.3/2.4.
- [x] HA-Ingress als Hauptzugang (HA-Login inklusive); relative Pfade testen.
      Prüfen, ob Zimi unter Ingress-Pfad läuft – sonst eigener Port für Zimi.
      --> **Zimi läuft nicht unter Ingress:** keine Präfix-Unterstützung, Hunderte
      absolute Pfade im JavaScript (`/search`, `/w/…`, `/static/…`). Umschreiben per
      `sub_filter`/Service-Worker wäre bei Zimis Release-Tempo zu zerbrechlich.
      Ingress zeigt deshalb die Startseite; Zimi über eigenen Port, die Startseite
      verlinkt ihn. nginx lässt nur `172.30.32.2` (Ingress-Gateway) und localhost zu.
- [x] Optionale LAN-Ports (Zimi, MCP) in `config.yaml`, standardmäßig aus
      --> Zimi 8899, MCP 8900
- [x] Nicht fürs Internet gedacht: in DOCS.md deutlich dokumentieren
- [x] Zimi-Login für den offenen Port? --> Entschieden: nein. Die Bibliothek muss nur
      im lokalen Netz erreichbar sein, nicht über externe Dienste.

### 2.6 MCP-Server
- [x] Umsetzung gemäß D4, Token-Pflicht
      --> Seit 0.6.0 erzeugt die App das Token selbst (`/data/mcp_token`, im Backup), die
      Startseite zeigt es und kann es neu erzeugen; Option `mcp_token` entfällt, weil
      optionale Felder in HA schwer zu finden sind. MCP läuft nur mit Host-Port. Die Knöpfe
      gehen über `okdl/control.py` (nur `127.0.0.1:8098`, davor nginx/Ingress).
      --> **Abweichung von D4 (a):** keine stdio→HTTP-Bridge. Zimis MCP-Server baut auf
      FastMCP, das Streamable HTTP selbst kann. `offline_knowledge/mcp_server/okmcp/`
      startet `zimi.mcp_server.build()` mit `streamable_http_app()` und eigener
      Bearer-Prüfung, s6-Dienst `mcp`, Port 8900, Pfad `/mcp`. DNS-Rebinding-Schutz von FastMCP
      aus, weil er nur `localhost` als Host zulässt; das Token schützt hier.
- [x] Tools durchreichen: `search`, `read`, `get_chunks`, `suggest`, `list_sources`,
      `deep_search`, …
      --> Option `mcp_tools`: `full` (Vorgabe, 19 Tools) oder `lean` (3 Tools). `full`
      enthält auch `manage_collection`, `manage_favorites` und `build_index`.
- [x] Test mit Claude Desktop und Open WebUI
      (lokal getestet: echter MCP-Client aus dem `mcp`-Paket im Container)
- [x] Optional/später: Karten-Tool (Ortssuche), sobald Geocoding da ist
      --> MCP-Tool `find_place`, in `full` und `lean`

### 2.7 Ressourcen
- [x] RAM/CPU im Leerlauf und bei Suche messen, Ergebnis in DOCS.md
      --> 06.11., 0.7.0 auf dem HA-Host, 16 ZIM-Dateien (222 GB), MCP und Ortssuche an, kein
      Download. Leerlauf (5 min): 0,36 % eines Kerns, 397 MiB Prozessspeicher (anon + Swap;
      Zimi 232, Downloader 93, MCP 67), 31 MiB Page-Cache. Suche nacheinander: 5 % im Schnitt,
      Prozessspeicher unverändert (369–397 MiB), Page-Cache bis 912 MiB (freigebbar). 4 Clients
      parallel: 36 %. Antwortzeit: erste Suche 28 s, neue dann ca. 1,3 s, Wiederholung aus dem
      Cache sofort. Einschränkung: Host stand unter hoher Fremdlast (ca. 90 % CPU, Swap voll),
      Antwortzeiten sind daher eher zu hoch; bei den 4 Clients überlappen sich die Suchbegriffe.
- [x] Karten: Speicherbedarf von `pmtiles` begrenzen und OOM-Kills (Exit `-9`) klar melden,
      nicht stündlich wiederholen
      --> 0.8.0: `GOMEMLIMIT=2500MiB`, `oom_score_adj=1000` für `pmtiles`, Status `no_memory`,
      nächster Versuch beim regulären Lauf oder per „Check now“. `asia` selbst fehlt auf dem
      Host weiter, bis genug Speicher frei ist.
      --> `asia` scheitert auf dem Host per OOM-Kill schon im Dry-Run (`oom_kill 8` im cgroup =
      4 Läufe × Dry-Run + Extrakt). Lokal gemessen im Dry-Run: `asia` 3,9 GB RSS / 6,4 GB
      Footprint, `europe` 1,3 / 2,5 GB. Größenschätzung fehlt dadurch ebenfalls.
      Go-GC hilft nur begrenzt (`asia`): `GOGC=25` 3,6 / 5,1 GB, `GOMEMLIMIT=2500MiB` 3,3 / 4,4 GB,
      Laufzeit unverändert. Der echte Extrakt ist auf dem Host noch nicht gemessen.

## 3. Add-on „Kolibri“

- [x] Image: Kolibri per pip (gepinnt) auf HA-Base-Image
      --> 0.19.5; `dist/cext` (glibc-Binärdateien, 165 MB) entfernt, läuft rein in Python.
      Image 192 MB.
- [x] `KOLIBRI_HOME`: Datenbank unter `/data`, Inhalte unter `<data_path>/kolibri`
      --> `/data/kolibri`; `KOLIBRI_CONTENT_DIR` nur bei nutzbarem Speicherort.
      `KOLIBRI_DISABLE_PING=true`, `KOLIBRI_ZEROCONF_ENABLED=false`. Ohne `TZ` startet
      Kolibri nicht, daher Rückfall auf UTC.
- [x] Ersteinrichtung automatisieren (`provisiondevice`: Facility, Admin aus Optionen)
      --> `facility_name`, `admin_username`, `admin_password`, `language`, Preset
      `nonformal`, einmalig (Marker `.provisioned`). Ohne Passwort: Assistent von Kolibri.
- [x] Option `channels` (Channel-IDs) + Sprache; Import per
      `kolibri manage importchannel network …` / `importcontent`
      --> `kolibri/channel_sync/kbsync/`, s6-Dienst `channels`, läuft neben dem Server
      (`--skip-update`). Version und Größe aus der Studio-API, Stand in
      `/data/channel_sync.json`. Abgewählte Kanäle bleiben; kein Zeitfenster.
- [x] Ingress mit URL-Präfix testen (`KOLIBRI_URL_PATH_PREFIX`)
      --> Funktioniert: nginx setzt das vom Ingress entfernte Präfix wieder davor und
      entfernt `X-Frame-Options: DENY`. HTML5-Inhalte kommen vom ZIP-Port; `ZIP_CONTENT_ORIGIN`
      mit Portnummer lässt Kolibri 0.19 in der CSP abstürzen (500), deshalb lauscht Kolibri
      auf der Nummer des Host-Ports und nginx leitet 8081 weiter. Optionale Ports 8080, 8081.
      Getestet mit echtem s6/bashio gegen nachgebauten Supervisor/Ingress, nicht auf dem Host.
- [x] `backup_exclude` für Inhalte
- [x] RAM/CPU messen
      Bisher lokal, nur RAM: Kolibri ca. 95–125 MB, Import-Dienst ca. 20 MB.
- [x] MCP gemäß D5 --> keins
- [x] Auf dem HA-Host testen, inklusive echtem Ingress und HTML5-Inhalten
- [x] D9: Auf Studio gibt es keinen öffentlichen Kanal mit Hauptsprache Deutsch, auch kein
      Khan Academy DE. --> Entschieden: Khan Academy EN (US, 68 GB),
      `c9d7f950ab6b5a1199e3d6c10d7f0103` in `channels` eintragen.

## 4. Update-Mechanismus

Drei Ebenen, getrennt behandelt:

- [x] **Software (Images):** neue Version im Repo → HA zeigt das Update an;
      automatische Add-on-Updates greifen. Gepinnte Versionen via Renovate (Abschnitt 1).
      --> HA zeigt Updates an (auf dem Host gesehen). Offen: automatische Updates ungetestet,
      Renovate-App noch nicht aktiviert (Abschnitt 1). Bei Offline Knowledge startet ein
      Update laufende Kartenextrakte neu, sie können nicht fortsetzen.
- [x] **Inhalte – Bibliothek:** eigener Downloader (2.2a), Frequenz als Option
      --> `update_interval_days`, Vorgabe 7 (vorher fest täglich)
- [x] **Inhalte – Karten:** Update-Job (z. B. monatlich) erzeugt neuen Extrakt,
      tauscht ihn atomar aus, löscht den alten erst danach
      --> Option `map_update_days` (Vorgabe 30), Prüfung im täglichen Downloader-Lauf
- [x] **Inhalte – Kolibri:** Channel-Update-Job
      --> Dienst `channels` prüft täglich die Version auf Studio
- [x] Auslösung: Abgleich der Auswahl bei jedem Add-on-Start **plus** Zeitplan im
      Container (nachts, Bandbreite). Manuelles Auslösen über `hassio.addon_stdin`
      (z. B. Kommando `update`), damit es per HA-Skript/Button geht.
      --> Beide Apps: `stdin: true`, Kommando `update`. Das Skript `stdin-commands` läuft als
      Docker-`CMD`, denn unter s6 bekommt nur der Hauptbefehl das stdin; ohne stdin schläft
      es, weil sein Ende die App stoppen würde. Offline Knowledge zusätzlich: Knopf
      „Check now“ auf der Startseite. Lokal mit `docker run -i` getestet, nicht mit
      echtem `hassio.addon_stdin`.
- [x] Kein Download beim Start des MCP-Servers (MCP soll sofort antworten)
      --> MCP lädt nichts, das macht nur der Dienst `downloader`
- [x] Log/Status: letzte Aktualisierung und Fehler auf der Landing-Page
      --> Offline Knowledge seit 0.3.0. Kolibri: nur im Log und in Kolibri selbst.

## 5. Integration

- [x] MCP-Endpunkt in Claude Desktop eintragen (Zugriff über VPN, nicht öffentlich)
- [x] MCP in Open WebUI als Tool anbinden
- [ ] Optional: HA-Sensoren (Speicher, letzte Aktualisierung) und Dashboard-Link

## 6. Test und Release

- [ ] Lokaler Test als lokales Add-on (`/addons`) auf dem HA-Host – erst nach Freigabe
- [x] Erst mit kleinem ZIM testen, dann große Inhalte laden
      --> Eine ZIM-Datei + Weltkarte: geladen, geprüft, Zimi übernimmt nach ca. 40 s
      ohne Neustart, Suche funktioniert.
- [x] Umzug der Inhalte auf die externe Platte testen (D6)
- [x] DOCS.md (Englisch) je Add-on, README aktualisieren
- [ ] Release v1.0.0
