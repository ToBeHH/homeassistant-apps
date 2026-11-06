# Offline Knowledge Apps for Home Assistant

> **Status: experimental.** The apps are in daily use on one host, but expect changes. Only
> `amd64` is supported.

Keep a copy of the world's knowledge at home, running as Home Assistant apps (formerly add-ons) and
working without an internet connection: Wikipedia and other reference works, offline maps,
data tools and educational courses, plus an MCP endpoint so AI assistants can search it.

Inspired by [Project NOMAD](https://www.projectnomad.us), but built for Home Assistant OS:
each component is a regular app managed by the Supervisor, with no access to the Docker
socket and no extra containers outside of Home Assistant. This project is not affiliated
with Project NOMAD or Crosstalk Solutions.

## Apps

| App | What it bundles | Status |
| --- | --- | --- |
| [Offline Knowledge](offline_knowledge/) | [Zimi](https://github.com/epheterson/Zimi) for Kiwix ZIM archives (Wikipedia, Wiktionary, Gutenberg, …), [CyberChef](https://github.com/gchq/CyberChef), an offline map viewer for [Protomaps](https://protomaps.com) PMTiles, and an MCP server | experimental |
| [Kolibri](kolibri/) | [Kolibri](https://learningequality.org/kolibri/) learning platform (e.g. Khan Academy channels) | experimental |

## Installation

Add this repository to Home Assistant with one click:

[![Open your Home Assistant instance and show the app store with this repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_store.svg)](https://my.home-assistant.io/redirect/supervisor_store/?repository_url=https%3A%2F%2Fgithub.com%2FToBeHH%2Fhomeassistant-apps)

Or add it manually in the app store (formerly add-on store) under **⋮ → Repositories**:

```txt
https://github.com/ToBeHH/homeassistant-apps
```

## Storage

Content is large (a full Wikipedia with images is on the order of 100 GB). The apps keep
their content outside the app data folder, on a configurable path such as `/share` or an
external drive under `/media`, and exclude it from Home Assistant backups.

## Licenses

The app code in this repository is MIT licensed (see [LICENSE](LICENSE)).
Bundled or downloaded components keep their own licenses: Zimi (MIT), CyberChef (Apache-2.0),
Protomaps tools (BSD-3-Clause), Kolibri (MIT). Content such as Wikipedia (CC BY-SA) and
OpenStreetMap data (ODbL) is downloaded at runtime and is not part of this repository.

<p align="center">If you love my work, please</p>
<p><a href="https://www.buymeacoffee.com/ToBeHH" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee"  height="52" width="185" ></a></p>