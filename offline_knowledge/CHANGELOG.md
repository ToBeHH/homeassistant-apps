# Changelog

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
