# andering/overlay

Gentoo overlay for `app-accessibility/voxtype-bin`.

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

The default installation is the CPU binary. It targets x86-64-v3 CPUs with AVX2 support and is keyworded `~amd64`.

## USE Flags

Choose Vulkan support per machine. To enable it:

```sh
echo 'app-accessibility/voxtype-bin vulkan' | sudo tee /etc/portage/package.use/voxtype
sudo emerge --ask app-accessibility/voxtype-bin
```

To disable it:

```sh
echo 'app-accessibility/voxtype-bin -vulkan' | sudo tee /etc/portage/package.use/voxtype
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

There is no systemd unit. On KDE, an XDG Autostart entry runs `voxtype daemon`. The daemon requires PipeWire to be running in the logged-in desktop session. Install that KDE-only entry with the optional `autostart` USE flag:

```sh
echo 'app-accessibility/voxtype-bin autostart' | sudo tee /etc/portage/package.use/voxtype
sudo emerge --ask app-accessibility/voxtype-bin
```

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
sudo emerge --depclean
sudo emerge --unmerge app-accessibility/voxtype-bin
```

XDG model and configuration files are managed by the user and are not removed by Portage. Removing the personal XDG configuration and model data is optional: `~/.config/voxtype` and `~/.local/share/voxtype`.
