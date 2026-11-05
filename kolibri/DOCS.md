# Kolibri

[Kolibri](https://learningequality.org/kolibri/) is an offline learning platform by
Learning Equality. It serves courses such as Khan Academy with videos, exercises and
progress tracking, without an internet connection.

## First steps

1. Create a folder with enough free space and set it as **Storage location** (`data_path`).
2. Set `admin_password` for the first setup, or leave it empty and use Kolibri's setup
   wizard. If you set it later, save and restart the app before finishing the wizard. Once
   Kolibri is set up, `facility_name`, `admin_username`, `admin_password` and `language` have
   no effect anymore; change these in Kolibri itself.
3. Add channel IDs to `channels` and start the app.
4. Open Kolibri from the sidebar. For games and simulations also set a host port for
   `8081/tcp` under **Network**, see [Access](#access).

## Storage

Content goes to `<data_path>/kolibri`; accounts and learning progress stay in the app's
own data and in its backup. Nothing is downloaded while `data_path` is empty or the folder
does not exist.

Downloaded content is not part of the app's backup. `/share` and `/media` are separate
folders in a full Home Assistant backup, so leave your storage folder out there.

## Channels

Channel IDs have 32 hexadecimal characters. The public channels are listed at
<https://studio.learningequality.org/api/public/v1/channels>, and Kolibri's own channel
page (**Device → Channels → Import**) shows them too.

| Channel | ID | Size (11/2026) |
| --- | --- | --- |
| Khan Academy (English, US curriculum) | `c9d7f950ab6b5a1199e3d6c10d7f0103` | 68 GB |
| Khan Academy (Español) | `c1f2b7e6ac9f56a2bb44fa7a48b66dce` | 39 GB |
| Khan Academy (Français) | `878ec2e6f88c5c268b1be6f202833cd4` | 23 GB |
| Blockly Games, good for a first test | `e409b964366a59219c148f2aaa741f43` | 0.3 GB |

There is currently no public German Khan Academy channel.

The app imports new channels at start and checks once a day for new versions. Before a new
channel it checks the free space (channel size plus a reserve of 2 GB or 2 %, whichever is
larger). Imports start right away; there is no download window. Progress is in the log.

A Home Assistant script or button can start a check right away with the action
`hassio.addon_stdin` and the input `update`.

Removing an ID from `channels` does not delete the channel. Use
**Device → Channels** in Kolibri for that.

## Configuration

| Option | Description |
| --- | --- |
| `data_path` | Folder for Kolibri content. |
| `channels` | Kolibri channel IDs to import. |
| `facility_name` | Name of the facility. First setup only. |
| `admin_username` | Name of the admin account. First setup only. |
| `admin_password` | Password of the admin account. First setup only; change it in Kolibri afterwards. Empty: Kolibri shows its setup wizard. |
| `language` | Default language, e.g. `de`, `en`. First setup only. |

## Access

- **Sidebar:** the **Kolibri** entry, or *Open Web UI*.
- **Local network:** set a host port for `8080/tcp` under **Network**. Learners can then
  open Kolibri without a Home Assistant account, using `http://<host>:<port>/`.
- **HTML5 content:** games and simulations load from a second address, directly from the
  browser. Set a host port for `8081/tcp` under **Network**. Any free port works, e.g. 8085,
  except 8080, 8099 and 18080.
  Videos and exercises work without it.

If you reach Home Assistant through HTTPS, browsers block HTML5 content from the plain HTTP
port. Use the port 8080 address for it.

## Security

This app is meant for your local network only. Do not forward its ports on your router or
expose them to the internet; they use plain HTTP. Kolibri has its own accounts. Its
statistics ping and network announcements are off.

## Licenses

The app is MIT licensed. Kolibri is MIT licensed. Channel content keeps its own license.

## Support

<p align="center">If you love my work, please</p>
<p><a href="https://www.buymeacoffee.com/ToBeHH" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a></p>