# Changelog

## 0.1.0

- Zimi 1.14.1 library server, installed from PyPI on the Home Assistant base image.
- BitTorrent, UPnP and Nearby are not installed; Zimi runs in offline mode with its
  own library management and auto-update turned off.
- ZIM files are read from `<data_path>/zim`; without a valid storage location Zimi
  starts with an empty library.
- Watchdog on Zimi's `/health` endpoint.
- Zimi's indexes and caches are excluded from backups.

## 0.0.1

- Initial scaffold: configuration options, storage location check. No content yet.
