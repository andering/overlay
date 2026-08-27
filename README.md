# andering/overlay

Gentoo overlay for `app-accessibility/voxtype-bin`.

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

## Updating And Removal

Update the overlay and installed packages with:

```sh
sudo emaint sync -r overlay
sudo emerge --update --deep --newuse --ask app-accessibility/voxtype-bin
```

Remove unused dependencies or uninstall Voxtype with:

```sh
sudo emerge --ask --unmerge app-accessibility/voxtype-bin
sudo emerge --ask --depclean
```

XDG model and configuration files are managed by the user and are not removed by Portage. Removing the personal XDG configuration and model data is optional: `~/.config/voxtype` and `~/.local/share/voxtype`.
