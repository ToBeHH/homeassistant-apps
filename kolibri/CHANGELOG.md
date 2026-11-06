# Changelog

## 0.1.4

- AppArmor profile enforced: violations are now blocked instead of only logged.

## 0.1.3

- AppArmor profile, in complain mode for now: violations are only logged.
- Options added in later versions are optional, so saving after an update can't fail on them.

## 0.1.2

- The command `update` through `hassio.addon_stdin` starts a channel check right away.

## 0.1.1

- The log says whether the first setup ran, failed or was skipped, and why.
- No more nginx errors in the log while Kolibri is starting.

## 0.1.0

- Kolibri 0.19.5, available in the Home Assistant sidebar (ingress) and optionally on
  port 8080 in the local network. Port 8081 serves HTML5 content.
- Imports the channels from the `channels` option at start, then checks for new
  versions once a day. Nothing is downloaded without a usable storage location.
- First setup from the new options `facility_name`, `admin_username`, `admin_password`
  and `language`; without a password Kolibri shows its setup wizard.
- No statistics ping, no announcing on the network.

## 0.0.2

- Use `bashio::app.*` instead of the deprecated `bashio::addon.*` functions.

## 0.0.1

- Initial scaffold: configuration options, storage location check. Kolibri is not installed yet.
