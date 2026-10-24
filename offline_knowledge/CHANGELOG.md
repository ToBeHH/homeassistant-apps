# Changelog

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
