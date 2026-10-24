# Kolibri

> **Work in progress.** This version is a scaffold and does not run Kolibri yet.

[Kolibri](https://learningequality.org/kolibri/) is an offline learning platform by
Learning Equality. It serves courses such as Khan Academy with videos, exercises and
progress tracking, without an internet connection.

## Storage

Set **Storage location** (`data_path`) to a folder with enough free space **before** importing
channels, e.g. a folder under `/share` or on an external drive under `/media`. Content is
excluded from Home Assistant backups. A full Khan Academy channel can take tens of gigabytes.

## Configuration

| Option | Description |
| --- | --- |
| `data_path` | Folder for Kolibri content. Nothing is downloaded while this is empty or the folder does not exist. |
| `channels` | Kolibri channel IDs to import. |

## Security

This app is meant for your local network only. Do not expose it to the internet.

## Licenses

The app is MIT licensed. Kolibri is MIT licensed. Channel content keeps its own license.
