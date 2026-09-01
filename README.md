# andering/overlay

Gentoo overlay containing:

- `app-accessibility/voxtype-bin`
- `net-vpn/cloudflared-openrc`
- `x11-misc/eitype`

## Keyword Acceptance

`app-accessibility/voxtype-bin` is keyworded `~amd64`. Add exactly this atom line before installing:

```text
app-accessibility/voxtype-bin ~amd64
```

If `/etc/portage/package.accept_keywords/` is a directory, edit the package-specific file:

```sh
sudoedit /etc/portage/package.accept_keywords/voxtype
```

Locate an existing `app-accessibility/voxtype-bin` atom line and replace it with the line above; if it is absent, add that line. This preserves unrelated entries and comments.

If `/etc/portage/package.accept_keywords` is a regular file, edit it instead:

```sh
sudoedit /etc/portage/package.accept_keywords
```

Locate an existing `app-accessibility/voxtype-bin` atom line and replace it with the line above; if it is absent, add that line. This preserves unrelated entries and comments.

## Installation

Add the overlay with `eselect`:

```sh
sudo eselect repository add overlay git https://github.com/andering/overlay.git
sudo emaint sync -r overlay
```

Alternatively, create `/etc/portage/repos.conf/overlay.conf`:

```ini
[overlay]
location = /var/db/repos/overlay
sync-type = git
sync-uri = https://github.com/andering/overlay.git
masters = gentoo
auto-sync = yes
```

Clone the repository into the configured location, then sync it:

```sh
sudo git clone https://github.com/andering/overlay.git /var/db/repos/overlay
sudo emaint sync -r overlay
```

Install the CPU package with:

```sh
sudo emerge --ask app-accessibility/voxtype-bin
```

The CPU binary is the default installation. Both the CPU and Vulkan upstream binaries require x86-64-v3 CPUs with AVX2 support and are keyworded `~amd64`.

## Per-Machine Configuration

Choose one final configuration state for each machine:

```text
# CPU default: no app-accessibility/voxtype-bin entry
# Vulkan
app-accessibility/voxtype-bin vulkan
# KDE autostart CPU
app-accessibility/voxtype-bin autostart
# Vulkan with KDE autostart
app-accessibility/voxtype-bin vulkan autostart
```

Each final line contains all desired flags. For the CPU default state, remove every existing `app-accessibility/voxtype-bin` atom line instead of adding one.

```sh
grep -R -- 'app-accessibility/voxtype-bin' /etc/portage/package.use/
```

Directory layouts may have multiple `package.use` fragments. Search every relevant fragment with the command above, then use `sudoedit` on the relevant file or files. Remove or replace all existing `app-accessibility/voxtype-bin` occurrences so exactly one desired final atom line remains in the complete configuration. This preserves unrelated entries and comments and avoids duplicate, conflicting atoms.

For example, edit the package-specific fragment with:

```sh
sudoedit /etc/portage/package.use/voxtype
```

If `/etc/portage/package.use` is a regular file, use:

```sh
sudoedit /etc/portage/package.use
```

Locate every existing `app-accessibility/voxtype-bin` atom line and remove or replace it so exactly one desired final atom line remains; for the CPU default state, remove all such atom lines. This preserves unrelated entries and comments and avoids duplicate, conflicting atoms.

After either configuration path, apply the selected binary and autostart state:

```sh
sudo emerge --ask app-accessibility/voxtype-bin
```

## Model Setup

Initialize Voxtype and download a model:

```sh
voxtype setup
voxtype setup model
```

For Czech transcription, select a multilingual `base`, `small`, or `large-v3-turbo` model. Never select a model ending in `.en`, as those models are English-only. Configure the selected model and language in the user configuration:

```toml
[whisper]
model = "base"
language = "cs"
```

## KDE And OpenRC

There is no systemd unit. On KDE, an XDG Autostart entry runs `voxtype daemon`. The daemon requires PipeWire to be running in the logged-in desktop session. Enable that KDE-only entry with the `autostart` final line in the per-machine configuration.

Use a toggle-style hotkey configuration:

```toml
[hotkey]
enabled = false
mode = "toggle"
```

`[hotkey] enabled = false` disables Voxtype's evdev listener, while `mode = "toggle"` retains toggle mode for the KDE shortcut.

Create a KDE Custom Shortcut that runs `voxtype record toggle`, for example on `Meta+V`. KWin does not provide a key-release binding, so a KDE shortcut must trigger the toggle command rather than a press-and-release action.

## Clipboard And Typing Backends

Install `gui-apps/wl-clipboard` for Wayland clipboard integration. Use eitype or dotool as the KDE Wayland typing backend. `wtype` is unsupported on KWin. `x11-misc/ydotool` is a fallback, but the user must manually configure `ydotoold`, `/dev/uinput`, and its permissions; the overlay makes none of these changes.

Do not make a user, group, or system-level change for this setup. In particular, do not add the desktop user to the `input` group when using a KDE shortcut.

## Cloudflared OpenRC

`net-vpn/cloudflared-openrc` installs an OpenRC service for Gentoo's official
`net-vpn/cloudflared` package. It supports one remotely managed Cloudflare
Tunnel per host and does not contain a tunnel token or enable itself.

Accept the testing keyword for the host architecture:

```text
# amd64
net-vpn/cloudflared-openrc ~amd64
# arm64
net-vpn/cloudflared-openrc ~arm64
```

If `/etc/portage/package.accept_keywords/` is a directory, edit
`/etc/portage/package.accept_keywords/cloudflared-openrc`. If
`/etc/portage/package.accept_keywords` is a regular file, edit that file
instead. Add the appropriate architecture-specific line from above while
preserving unrelated entries and comments.

Install the package:

```sh
sudo emerge --ask net-vpn/cloudflared-openrc
```

Edit the root-only token file with `sudoedit /etc/cloudflared/token`. Paste only
the token, without a variable name, quotes, or other configuration, then save
the file. This avoids placing the token in shell history.

Enable and start the service explicitly:

```sh
sudo rc-update add cloudflared default
sudo rc-service cloudflared start
sudo rc-service cloudflared status
```

The command line includes `--token-file /etc/cloudflared/token`, so process argv
exposes only the token file path, not the token value. The token is not exported
to the daemon environment. Removing the package does not remove Cloudflare-side
tunnels or DNS records.

Service output is written to `/var/log/cloudflared.log`, and errors are written
to `/var/log/cloudflared.err`. Invalid or revoked token failures retry every
five seconds without a retry limit, and each failure repeats in the error log.
Before `cloudflared` launches, the service rejects a missing or non-regular
token file, ownership other than UID:GID `0:0`, mode other than `0600`, and
empty or whitespace-only content. It also rejects relative token paths, spaces,
and characters outside `[A-Za-z0-9_./-]` before constructing the daemon command.
Each clear file error includes only a validated token file path and appears in
`rc-service` output.

## Updating And Removal

Update the overlay and installed packages with:

```sh
sudo emaint sync -r overlay
sudo emerge --update --deep --newuse --ask app-accessibility/voxtype-bin
sudo emerge --update --deep --ask net-vpn/cloudflared-openrc
```

Using `--deep` includes the `net-vpn/cloudflared` dependency, whose self-update
is disabled by this service.

`/etc/cloudflared/token` is protected by Portage's `CONFIG_PROTECT`. Review
configuration updates with `dispatch-conf` or `etc-update`, and do not blindly
replace the configured tunnel token.

Revision `1-r1` detects an active legacy `TUNNEL_TOKEN=` or
`export TUNNEL_TOKEN=` assignment preserved in `/etc/conf.d/cloudflared` and
prints a migration warning. It never copies or prints the token automatically.
Manually move only the token value into `/etc/cloudflared/token`, set that file
to `root:root` mode `0600`, and remove the legacy assignment. The r1 service
also unsets an inherited legacy `TUNNEL_TOKEN` before launching `cloudflared`.

Remove unused dependencies or uninstall Voxtype with:

```sh
sudo emerge --ask --unmerge app-accessibility/voxtype-bin
sudo emerge --ask --depclean
```

Stop, disable, and uninstall the Cloudflared OpenRC service with:

```sh
sudo rc-service cloudflared stop
sudo rc-update del cloudflared default
sudo emerge --ask --unmerge net-vpn/cloudflared-openrc
```

Quietly check whether the preserved legacy configuration still contains a token
assignment, and remove it without displaying the token. Also remove the r1 token
file:

```sh
if sudo test -f /etc/conf.d/cloudflared && \
  sudo grep -qE '^[[:space:]]*(export[[:space:]]+)?TUNNEL_TOKEN[[:space:]]*=' /etc/conf.d/cloudflared; then
  sudo rm -f -- /etc/conf.d/cloudflared
fi
sudo rm -f -- /etc/cloudflared/token
```

Quiet matching and removal do not print either token. Filesystem deletion is
not guaranteed secure erasure, so rotate or revoke the tunnel token in
Cloudflare. Optionally remove `/var/log/cloudflared.log` and
`/var/log/cloudflared.err`. If the tunnel is no longer needed, delete it and
remove its obsolete public hostname or DNS CNAME to avoid stale DNS and
Cloudflare error 1016.

XDG model and configuration files are managed by the user and are not removed by Portage. Removing the personal XDG configuration and model data is optional: `~/.config/voxtype` and `~/.local/share/voxtype`.
