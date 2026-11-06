# Changelog

## 0.8.0

- The map viewer shows the world map under the selected region, so the map no longer ends at
  the region's edge. Needs `world` in `map_regions`.
- A map that needs more memory than is free now says so (state "Not enough memory") instead
  of `pmtiles extract failed (-9)`. It is tried again at the next regular check or with
  **Check now**, not every hour: each attempt brought the whole host to its memory limit.
- Map downloads need less memory (for `asia` about 4.4 GB instead of 6.4 GB) and, if memory
  runs out anyway, the system stops the map download rather than another app.
- AppArmor profile enforced: violations are now blocked instead of only logged.
- Documentation: resource use measured with a large library.

## 0.7.0

- Offline place search, off by default (`place_search`): towns, mountains, rivers and postal
  codes from GeoNames, streets and points of interest from your map regions. A search field
  in the map viewer jumps there, and the new MCP tool `find_place` answers assistants.
- AppArmor profile, in complain mode for now: violations are only logged.
- Fixes saving the configuration after an update ("Missing option 'update_interval_days'"):
  options added in later versions are now optional.

## 0.6.1

- New map regions for all continents: `africa`, `antarctica`, `asia`, `north_america`,
  `oceania`, `south_america`.
- `europe` now uses zoom 15 (49 GB) instead of 14 (25 GB), like the other regions. An
  existing Europe map is downloaded again; use `europe:14` to keep it.
- The map viewer zooms to level 20.

## 0.6.0

- The MCP token is now created by the app. The start page shows it with the address, can
  copy it and can recreate it. The `mcp_token` option is gone.
- The MCP server only runs when a host port is set for 8900/tcp.
- Content updates: new option `update_interval_days` (default 7, was fixed at one day),
  **Check now** on the start page, and the command `update` through `hassio.addon_stdin`.

## 0.5.1

- Map downloads show their real progress. They showed 100 % right from the start,
  because `pmtiles` creates the file at full size up front.

## 0.5.0

- MCP endpoint: AI assistants can search and read the library at port 8900, path `/mcp`
  (Streamable HTTP). Off until `mcp_token` is set and a host port is opened.
- New options `mcp_token` and `mcp_tools` (`full` or `lean`).

## 0.4.1

- Removed WikEM from the `full` profile; it is no longer in the Kiwix catalog.
- Use `bashio::app.*` instead of the deprecated `bashio::addon.*` functions.
- The downloader's user agent reports the current app version.

## 0.4.0

- Offline maps: regions are cut out of the current Protomaps planet build with
  `pmtiles extract` and shown in a map viewer (MapLibre, Protomaps basemap style) under
  the start page. Fonts and icons are served locally, so the maps work without internet.
- New options `map_regions` (predefined `world`, `germany`, `dach`, `europe`, a zoom
  override like `germany:12`, or your own bounding box) and `map_update_days`.
- CyberChef 11.5.0, served under the start page.
- Library and map downloads share one queue, smallest first.

## 0.3.0

- Start page in the Home Assistant sidebar (ingress): download status per source with
  progress, free space on the storage location, size of the library and a link to it.
- Shows a clear notice while no usable storage location is set.
- Download progress is updated every few seconds; the log shows 10 % steps.
- The library itself still opens on its own port (8899): Zimi builds absolute URLs and
  can't run under the ingress path.

## 0.2.0

- Own content downloader: reads the Kiwix catalog, resolves each ZIM name to its newest
  file and keeps `<data_path>/zim` in line with `profile`, `languages` and
  `zim_sources`. Downloads resume after interruptions, are checked against the
  published SHA-256 and only appear under their final name when complete. The old
  edition is deleted after the new one is in place.
- Checks for updates at start and then once a day.
- New options `download_window` (e.g. `01:00-06:00`) and `download_limit` (KB/s).
- Optional port 8899 for the library web interface, off by default.
- Health check moved from the `watchdog` option to a Docker `HEALTHCHECK`.

## 0.1.0

- Zimi 1.14.1 library server, installed from PyPI on the Home Assistant base image.
- BitTorrent, UPnP and Nearby are not installed; Zimi runs in offline mode with its
  own library management and auto-update turned off.
- ZIM files are read from `<data_path>/zim`, which Zimi watches as an extra library
  folder: files added, replaced or removed there show up within about a minute,
  without a restart. Without a valid storage location Zimi starts with an empty library.
- Zimi's admin interface (`/manage`) is disabled; reading is open, access control is
  left to Home Assistant.
- Watchdog on Zimi's `/health` endpoint.
- Zimi's indexes and caches are excluded from backups.

## 0.0.1

- Initial scaffold: configuration options, storage location check. No content yet.
