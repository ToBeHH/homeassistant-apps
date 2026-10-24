# Offline Knowledge

> **Work in progress.** Library, maps, CyberChef and the start page work. The MCP
> endpoint is still missing.

Offline Knowledge keeps a copy of the world's knowledge on your Home Assistant host so it
stays available without an internet connection:

- **Library:** Wikipedia, Wiktionary, Project Gutenberg, medical references and other
  [Kiwix](https://kiwix.org) ZIM archives, served by [Zimi](https://github.com/epheterson/Zimi)
- **Maps:** offline maps from [Protomaps](https://protomaps.com) (OpenStreetMap data)
- **Data tools:** [CyberChef](https://github.com/gchq/CyberChef)
- **MCP endpoint:** lets AI assistants search and read the library

## Storage

Content is large. Choose a folder with enough free space and set it as **Storage location**
(`data_path`) **before** anything is downloaded. Good choices are a folder under `/share`
or a folder on an external drive mounted under `/media`. Content is excluded from
Home Assistant backups of this app.

Note: `/share` and `/media` are separate folders in a full Home Assistant backup. If your
storage location is there, leave that folder out of your backups, or the backup will
contain all downloaded content.

ZIM files live in `<data_path>/zim`. The library checks this folder every 30 seconds;
new, replaced or removed files show up within about a minute. If you copy files in by
hand, copy them under a name ending in `.tmp` and rename them when the copy is complete.
Names ending in `.zim.part` belong to the downloader.

## Content

The downloader looks up every selected source in the [Kiwix catalog](https://library.kiwix.org)
and keeps the newest edition in `<data_path>/zim`. It runs at start and then once a day.
What each profile contains is defined per language in
[`profiles.json`](https://github.com/ToBeHH/homeassistant-apps/blob/main/offline_knowledge/downloader/okdl/profiles.json).

| Profile | `de` | `en` | other languages |
| --- | --- | --- | --- |
| `slim` | Wikipedia without pictures, Wiktionary, Wikivoyage (about 20 GB) | Wikipedia intro sections only, Wiktionary, Wikivoyage, WikiMed (about 25 GB) | Wikipedia intros, Wiktionary, Wikivoyage |
| `standard` | Wikipedia with pictures, Wiktionary, Wikivoyage, Wikibooks, iFixit (about 58 GB) | Wikipedia without pictures, Wiktionary, Wikivoyage, Wikibooks, WikiMed, iFixit (about 72 GB) | Wikipedia without pictures, Wiktionary, Wikivoyage |
| `full` | `standard` plus Wikiquote, Wikisource, Wikiversity, Project Gutenberg (about 73 GB) | Wikipedia with pictures, Wiktionary, Wikivoyage, Wikibooks, Wikiquote, WikiMed, WikEM, iFixit (about 150 GB) | Wikipedia with pictures, Wiktionary, Wikivoyage |
| `custom` | only `zim_sources` | | |

Sizes as of October 2026. Sources a language does not have are skipped (see the log).

Downloads resume after an interruption, are checked against the published SHA-256
checksum and appear under their final name only when complete. Before each download the
downloader checks the free space (download plus a reserve of 2 GB or 2 %, whichever is
larger) and skips what does not fit.

The current state is shown on the start page.

## Maps

Maps are cut out of the [Protomaps](https://protomaps.com) planet build (OpenStreetMap
data); only the selected area is downloaded. They are stored in `<data_path>/maps` and
shown under **Open maps** on the start page.

| `map_regions` entry | Area | Size (10/2026) |
| --- | --- | --- |
| `world` | whole world, zoom 0–6 (countries, big cities, main roads) | 45 MB |
| `germany` | Germany, full detail (zoom 15) | 7.4 GB |
| `dach` | Germany, Austria, Switzerland, full detail | 10 GB |
| `europe` | Europe, zoom 14 | 25 GB |
| `germany:12` | any of the above with a lower maximum zoom; each level less roughly halves the size | |
| `home=9.7,53.4,10.3,53.7:15` | your own area: name, then min_lon,min_lat,max_lon,max_lat and optionally the zoom (default 14) | |

`map_update_days` (default 30) renews a map once it is that old and a newer build exists;
`0` keeps maps as they are. A renewed map replaces the old one only when it is complete.

Maps are not paused by `download_window` once they have started, and `download_limit`
does not apply to them.

## CyberChef

[CyberChef](https://github.com/gchq/CyberChef) runs completely in your browser and is
opened from the start page. Nothing you enter leaves your device.

To try the app with very little data, use the `custom` profile with
`zim_sources: [devdocs_en_bash]` (0.5 MB).

During updates the old and the new version of a file exist side by side for a short time,
so keep some spare space.

## Configuration

| Option | Description |
| --- | --- |
| `data_path` | Folder for all content. Nothing is downloaded while this is empty or the folder does not exist. |
| `profile` | `slim`, `standard`, `full` or `custom`. |
| `languages` | Language codes, e.g. `de`, `en`. |
| `zim_sources` | Extra ZIM names without date, e.g. `wikipedia_de_all_maxi`. For `custom`, the complete list. |
| `prune` | Delete content that is no longer selected (default: off). Older editions of selected content are always replaced. |
| `download_window` | Only download in this daily window, e.g. `01:00-06:00`. A running download pauses outside it and resumes later. Empty: any time. |
| `download_limit` | Maximum download speed in KB/s, `0` for no limit. Library downloads only. |
| `map_regions` | Map regions, see [Maps](#maps). Default: `world`. |
| `map_update_days` | Renew maps after this many days, `0` for never. |

## Access

- **Start page:** *Open Web UI* or the **Offline Knowledge** entry in the sidebar. It
  shows the download status and the free space, and opens the library, the maps and
  CyberChef. Home Assistant takes care of the login.
- **Library:** opens on its own port, because the library server can't run inside the
  Home Assistant sidebar. Set a host port for `8899/tcp` under **Network** in the app
  settings; the start page then links to it. The library has **no login of its own** –
  anyone who can reach the port can read it.

## Network

| Port | Description |
| --- | --- |
| 8899/tcp | Library web interface and API. Off by default. Set a host port under **Network** to use it in your local network. |

## Security

This app is meant for your local network only.

- Do **not** forward port 8899 (or the MCP port, once there is one) on your router or
  expose it through a reverse proxy to the internet. It has no login.
- Use a VPN if you want to reach the library from outside.
- The start page in the sidebar is protected by the Home Assistant login.

## Licenses

The app is MIT licensed. Bundled tools keep their own licenses: Zimi (MIT), CyberChef
(Apache 2.0), MapLibre GL JS, PMTiles and the Protomaps basemap (BSD 3-Clause), Noto Sans
fonts (OFL). Downloaded content keeps its own license, e.g. Wikipedia (CC BY-SA) and
OpenStreetMap (ODbL).
