# Offline Knowledge

> **Work in progress.** Library, maps, CyberChef, the start page and the MCP endpoint work.

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
and keeps the newest edition in `<data_path>/zim`. It runs at every start of the app, then
every `update_interval_days` days, and when you press **Check now** on the start page. A
Home Assistant script or button can also start it:

```yaml
action: hassio.addon_stdin
data:
  addon: <slug of this app>
  input: update
```

What each profile contains is defined per language in
[`profiles.json`](https://github.com/ToBeHH/homeassistant-apps/blob/main/offline_knowledge/downloader/okdl/profiles.json).

| Profile | `de` | `en` | other languages |
| --- | --- | --- | --- |
| `slim` | Wikipedia without pictures, Wiktionary, Wikivoyage (about 20 GB) | Wikipedia intro sections only, Wiktionary, Wikivoyage, WikiMed (about 25 GB) | Wikipedia intros, Wiktionary, Wikivoyage |
| `standard` | Wikipedia with pictures, Wiktionary, Wikivoyage, Wikibooks, iFixit (about 58 GB) | Wikipedia without pictures, Wiktionary, Wikivoyage, Wikibooks, WikiMed, iFixit (about 72 GB) | Wikipedia without pictures, Wiktionary, Wikivoyage |
| `full` | `standard` plus Wikiquote, Wikisource, Wikiversity, Project Gutenberg (about 73 GB) | Wikipedia with pictures, Wiktionary, Wikivoyage, Wikibooks, Wikiquote, WikiMed, iFixit (about 150 GB) | Wikipedia with pictures, Wiktionary, Wikivoyage |
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

| `map_regions` entry | Area | Size (11/2026) |
| --- | --- | --- |
| `world` | whole world, zoom 0–6 (countries, big cities, main roads) | 45 MB |
| `germany` | Germany | 7.4 GB |
| `dach` | Germany, Austria, Switzerland | 10 GB |
| `africa` | Africa | 15 GB |
| `antarctica` | Antarctica | 0.4 GB |
| `asia` | Asia | 45 GB |
| `europe` | Europe | 49 GB |
| `north_america` | North America, Central America, Greenland | 37 GB |
| `oceania` | Australia, New Zealand, western Pacific | 4 GB |
| `south_america` | South America | 9 GB |
| `germany:12` | any of the above with a lower maximum zoom | each level less roughly halves the size |
| `home=9.7,53.4,10.3,53.7:15` | your own area: name, then min_lon,min_lat,max_lon,max_lat and optionally the zoom (default 14) | |

All regions except `world` use zoom 15, the most detailed level of the Protomaps data. The
viewer zooms on to level 20: these are vector maps, so lines and labels stay sharp, but they
show no more objects than at level 15. Regions can overlap. A region can't cross the 180th
meridian, so islands east of it (e.g. Samoa, Hawaii in `oceania`) need an own entry
such as `hawaii=-161,18,-154,23:15`.

Maps are not paused by `download_window` once they have started, and `download_limit`
does not apply to them.

Some file systems of external drives (e.g. exFAT) don't allow measuring the progress of a
map download; the log says so, and the percentage stays at 0 until the map is finished.

`map_update_days` (default 30) renews a map once it is that old and a newer build exists;
`0` keeps maps as they are. A renewed map replaces the old one only when it is complete.

Maps are not paused by `download_window` once they have started, and `download_limit`
does not apply to them.

### Place search

With `place_search` on, the search field in the map viewer and the MCP tool `find_place` find
places offline:

- **Towns, regions, mountains, rivers, postal codes** worldwide, from
  [GeoNames](https://www.geonames.org) (CC BY 4.0). The app downloads about 450 MB once and
  renews them every `map_update_days` days. The index takes about 2.5 GB.
- **Streets and points of interest** from your map regions at zoom 13 or above, each with the
  nearest town, so you can search for `Hauptstraße Kiel`. House numbers can't be searched.

Building the index from a map takes time, because every tile is read: under an hour
for `germany`, about half a day for `europe`. It runs with low priority after the downloads,
and starts over if the app restarts; the progress is on the start page. The index for a map is
rebuilt when the map is renewed.

## CyberChef

[CyberChef](https://github.com/gchq/CyberChef) runs completely in your browser and is
opened from the start page. Nothing you enter leaves your device.

To try the app with very little data, use the `custom` profile with
`zim_sources: [devdocs_en_bash]` (0.5 MB).

During updates the old and the new version of a file exist side by side for a short time,
so keep some spare space.

## MCP endpoint

AI assistants can search and read the library through the
[Model Context Protocol](https://modelcontextprotocol.io). To turn it on:

1. Set a host port for `8900/tcp` under **Network** in the app settings.
2. Restart the app and open the start page. Its **AI assistants (MCP)** section shows the
   address and the token, and copies a ready-made command for Claude Code.

Clients connect with Streamable HTTP to `http://<host>:<port>/mcp` and send the header
`Authorization: Bearer <token>`.

The app creates the token itself. **Recreate token** on the start page replaces it at once;
connected assistants then need the new one. Without a host port the MCP server does not run.

`mcp_tools` selects the tools. `lean` offers `search`, `read` and `read_section`, which
suits small models. `find_place` is always there. `full` (default) offers all of Zimi's tools, including some that
change the library's collections and favorites (`manage_collection`,
`manage_favorites`) or start index builds (`build_index`).

The MCP server needs about 100 MB of RAM on top of the library. New files show up about
a minute after they arrive.

## Configuration

| Option | Description |
| --- | --- |
| `data_path` | Folder for all content. Nothing is downloaded while this is empty or the folder does not exist. |
| `profile` | `slim`, `standard`, `full` or `custom`. |
| `languages` | Language codes, e.g. `de`, `en`. |
| `zim_sources` | Extra ZIM names without date, e.g. `wikipedia_de_all_maxi`. For `custom`, the complete list. |
| `prune` | Delete content that is no longer selected (default: off). Older editions of selected content are always replaced. |
| `download_window` | Only download in this daily window, e.g. `01:00-06:00`. A running download pauses outside it and resumes later. Empty: any time. |
| `update_interval_days` | Look for new editions of the library every this many days (default 7). |
| `download_limit` | Maximum download speed in KB/s, `0` for no limit. Library downloads only. |
| `map_regions` | Map regions, see [Maps](#maps). Default: `world`. |
| `map_update_days` | Renew maps after this many days, `0` for never. |
| `place_search` | Offline place search, see [Place search](#place-search). Default: off. |
| `mcp_tools` | `full` or `lean`, see [MCP endpoint](#mcp-endpoint). |

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
| 8900/tcp | MCP endpoint. Off by default; the MCP server only runs with a port. |

## Security

This app is meant for your local network only.

- Do **not** forward port 8899 or 8900 on your router or expose them through a reverse
  proxy to the internet. Port 8899 has no login, and port 8900 uses plain HTTP, so its
  token is not encrypted on the way.
- Use a VPN if you want to reach the library from outside.
- The start page in the sidebar is protected by the Home Assistant login.

## Licenses

The app is MIT licensed. Bundled tools keep their own licenses: Zimi (MIT), CyberChef
(Apache 2.0), MapLibre GL JS, PMTiles and the Protomaps basemap (BSD 3-Clause), Noto Sans
fonts (OFL). Downloaded content keeps its own license, e.g. Wikipedia (CC BY-SA) and
OpenStreetMap (ODbL).

## Support

<p align="center">If you love my work, please</p>
<p><a href="https://www.buymeacoffee.com/ToBeHH" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a></p>