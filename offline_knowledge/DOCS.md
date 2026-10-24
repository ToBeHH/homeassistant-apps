# Offline Knowledge

> **Work in progress.** The library server runs, but there is no downloader, web access
> or MCP endpoint yet. ZIM files you put into `<data_path>/zim` yourself are picked up.

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

ZIM files live in `<data_path>/zim`.

| Profile | Approximate size |
| --- | --- |
| `slim` | 30 GB |
| `standard` | 150 GB |
| `full` | 300 GB |
| `custom` | depends on `zim_sources` |

During updates the old and the new version of a file exist side by side for a short time,
so keep some spare space.

## Configuration

| Option | Description |
| --- | --- |
| `data_path` | Folder for all content. Nothing is downloaded while this is empty or the folder does not exist. |
| `profile` | `slim`, `standard`, `full` or `custom`. |
| `languages` | Language codes, e.g. `de`, `en`. |
| `zim_sources` | Extra ZIM names without date, e.g. `wikipedia_de_all_maxi`. For `custom`, the complete list. |
| `prune` | Delete content that is no longer selected (default: off). |

## Security

This app is meant for your local network only. Do not expose it to the internet.

## Licenses

The app is MIT licensed. Bundled tools keep their own licenses. Downloaded content keeps its
own license, e.g. Wikipedia (CC BY-SA) and OpenStreetMap (ODbL).
