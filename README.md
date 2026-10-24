# Offline Knowledge Add-ons for Home Assistant

> **Status: work in progress.** Nothing here is ready to install yet; see [TODO.md](TODO.md) for the plan.

Keep a copy of the world's knowledge at home, running as Home Assistant add-ons and
working without an internet connection: Wikipedia and other reference works, offline maps,
data tools and educational courses, plus an MCP endpoint so AI assistants can search it.

Inspired by [Project NOMAD](https://www.projectnomad.us), but built for Home Assistant OS:
each component is a regular add-on managed by the Supervisor, with no access to the Docker
socket and no extra containers outside of Home Assistant. This project is not affiliated
with Project NOMAD or Crosstalk Solutions.

## Add-ons

| Add-on | What it bundles | Status |
| --- | --- | --- |
| [Offline Knowledge](offline_knowledge/) | [Zimi](https://github.com/epheterson/Zimi) for Kiwix ZIM archives (Wikipedia, Wiktionary, Gutenberg, …), [CyberChef](https://github.com/gchq/CyberChef), an offline map viewer for [Protomaps](https://protomaps.com) PMTiles, and an MCP server | planned |
| [Kolibri](kolibri/) | [Kolibri](https://learningequality.org/kolibri/) learning platform (e.g. Khan Academy channels) | planned |

## Installation

Once released, add this repository to Home Assistant with one click:

[![Open your Home Assistant instance and show the app store with this repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_store.svg)](https://my.home-assistant.io/redirect/supervisor_store/?repository_url=https%3A%2F%2Fgithub.com%2FToBeHH%2Fhomeassistant-addons-public)

Or add it manually in the app store (formerly add-on store) under **⋮ → Repositories**:

```txt
https://github.com/ToBeHH/homeassistant-addons-public
```

## Storage

Content is large (a full Wikipedia with images is on the order of 100 GB). The add-ons keep
their content outside the add-on data folder, on a configurable path such as `/share` or an
external drive under `/media`, and exclude it from Home Assistant backups.

## Licenses

The add-on code in this repository is MIT licensed (see [LICENSE](LICENSE)).
Bundled or downloaded components keep their own licenses: Zimi (MIT), CyberChef (Apache-2.0),
Protomaps tools (BSD-3-Clause), Kolibri (MIT). Content such as Wikipedia (CC BY-SA) and
OpenStreetMap data (ODbL) is downloaded at runtime and is not part of this repository.
