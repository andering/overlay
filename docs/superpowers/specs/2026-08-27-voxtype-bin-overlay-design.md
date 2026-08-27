# Voxtype Binary Gentoo Overlay Design

## Purpose

Create a reusable, Git-backed personal Gentoo overlay at `/app/overlay` for
installing Voxtype through Portage. The GitHub repository, if created later,
will be `andering/overlay`. The overlay must work on Gentoo systems using
OpenRC, KDE Plasma on Wayland, and PipeWire without installing or enabling
services, changing groups, or altering user configuration during merge.

## Discovery Summary

The initial target host is an amd64 Gentoo system with OpenRC 0.63.3, KDE
Plasma on Wayland, PipeWire 1.6.7 with WirePlumber, and a working PipeWire
PulseAudio microphone source. Its AMD Ryzen 9 9900X supports AVX2 and
AVX-512. Portage enables the `vulkan`, `amdgpu`, and `radeonsi` USE flags.

Python 3.14.6, Rust 1.96.1, Git 2.54.0, and `gui-apps/wl-clipboard` are
available. `vulkaninfo`, `ydotool`, `dev-util/pkgdev`, and
`dev-util/pkgcheck` are not installed.

A scan of the Gentoo repository, GURU, and every enabled third-party overlay
found no Voxtype ebuild. Web searches likewise found no maintained Gentoo
ebuild suitable for reuse.

## Upstream Package

The pinned upstream release is `v0.7.5`, published on 2026-05-28 by
`peteonrails/voxtype`. Its source is MIT licensed.

Current stable release assets are raw Linux binaries, not AppImages. Earlier
upstream documentation mentioning AppImages is stale. The package will use
the official raw release assets and the accompanying source archive:

| Selection   | Asset                               | SHA-256                                                            |
| ----------- | ----------------------------------- | ------------------------------------------------------------------ |
| Default CPU | `voxtype-0.7.5-linux-x86_64-avx2`   | `18ae0510d0c964689f8c9b7119c0b9a45569985e82977dc4f1ef4d76fddd887c` |
| Vulkan      | `voxtype-0.7.5-linux-x86_64-vulkan` | `64626d07f3aae2825ddb82ea66878f708c8a820a3fd3ece76d99ff98477f132d` |

Upstream provides `SHA256SUMS.txt` and a detached PGP signature. Portage's
generated Manifest will verify the exact source archive and selected binary
at fetch time. The release binaries require at least the x86-64-v3/AVX2
baseline, so this initial package targets `~amd64`; it intentionally does
not claim support for older x86_64 CPUs or experimental arm64 binaries.

## Repository Layout

The Portage repository name is `overlay`. It will contain:

```text
metadata/layout.conf
profiles/repo_name
profiles/use.local.desc
app-accessibility/voxtype-bin/
  Manifest
  metadata.xml
  voxtype-bin-0.7.5.ebuild
  files/
README.md
.gitignore
```

`metadata/layout.conf` will declare the Gentoo master repository, EAPI 8,
and thin Manifests. `profiles/use.local.desc` will describe the overlay-local
`autostart` USE flag.

## Ebuild Design

`app-accessibility/voxtype-bin` will be an EAPI 8 binary package with:

- `LICENSE="MIT"`, `KEYWORDS="~amd64"`, and `RESTRICT="mirror"`.
- `IUSE="autostart vulkan"`; CPU is the default and `vulkan` selects the
  official Vulkan Whisper binary independently on each PC.
- The release source archive downloaded alongside the selected binary to
  install upstream documentation, the MIT license, the upstream SVG icon,
  and desktop metadata using normal ebuild helpers.
- `/usr/bin/voxtype` installed from the selected upstream binary. The ebuild
  will not run upstream GPU setup, create mutable alternative symlinks, or
  auto-detect hardware.
- A visible local desktop entry with `Exec=voxtype configure` and
  `Terminal=true`, using the upstream SVG icon. A hidden daemon desktop entry
  is also installed from upstream metadata. This avoids the upstream
  `voxtype-configure-launcher` helper, which is not distributed with the raw
  binary asset.
- `autostart` disabled by default. When enabled, it installs an XDG autostart
  entry restricted to KDE that runs `voxtype daemon` only after the user logs
  into a graphical session. It does not install a systemd unit.

Hard runtime dependencies will be verified against the fetched release binary
with `lddtree` before the ebuild is finalized. The expected audio stack is
`media-libs/alsa-lib` and `media-video/pipewire[pipewire-alsa]`; the Vulkan
variant additionally requires the Gentoo Vulkan loader. Optional integrations
are deliberately not forced as dependencies because Voxtype can be configured
without them:

- `gui-apps/wl-clipboard` enables clipboard output/fallback.
- A KDE-compatible typing backend such as eitype or dotool enables direct
  Wayland typing. `wtype` does not work on KDE Wayland.
- `x11-misc/ydotool` is a fallback only. Its daemon, `/dev/uinput` access,
  permissions, and any group membership remain an explicit administrator
  decision and are never changed by the ebuild.
- The `input` group is not required when KDE uses a compositor shortcut. The
  ebuild never adds users to it.

The package will not depend on `dev-python/whisper`, which is unrelated to
OpenAI Whisper.

## KDE and OpenRC Operation

The README will prescribe a user-session configuration, not a system service:

1. Run `voxtype setup` and select a multilingual Whisper model for Czech,
   such as `base`, `small`, or `large-v3-turbo`; do not select an `.en` model.
2. Configure `[whisper] language = "cs"` or a constrained multilingual set
   including `"cs"` in the user configuration.
3. Start `voxtype daemon` from KDE Autostart manually, or enable the
   per-machine `autostart` USE flag.
4. Disable Voxtype's evdev hotkey in the user configuration and create a KDE
   Custom Shortcut bound to `voxtype record toggle` (for example, Meta+V).
   KWin has no key-release binding, so toggle mode is the correct Plasma
   workflow.

This preserves the session's PipeWire, Wayland, and D-Bus context and avoids
kernel-level hotkey access. The README will explain `ydotoold` and `/dev/uinput`
only as opt-in fallback requirements.

## README Scope

The top-level README will document:

- adding the Git remote with `eselect repository` and a manual
  `/etc/portage/repos.conf/overlay.conf` alternative;
- synchronizing with `emaint sync -r overlay`;
- installing, updating, and removing `app-accessibility/voxtype-bin`;
- CPU default versus per-machine `vulkan` and `autostart` USE settings;
- initial setup, Czech/multilingual models, and model storage expectations;
- KDE Autostart and KDE Custom Shortcut configuration on OpenRC;
- conditional typing, clipboard, evdev, ydotoold, `/dev/uinput`, and
  permission requirements; and
- cleanup boundaries: Portage removes only files it owns, while user model
  and configuration data under XDG directories remain a user-managed choice.

## Validation

Before installing any development tools, ask for explicit permission to run
the required `sudo emerge` command. Once authorized, install
`dev-util/pkgdev` and `dev-util/pkgcheck`, then:

1. Fetch through Portage and generate `Manifest` with `pkgdev manifest`.
2. Run `pkgcheck scan` and resolve meaningful diagnostics.
3. Run `ebuild ... clean unpack prepare compile install` for the default CPU
   build and the `vulkan` USE variant.
4. Inspect the staged install trees and run `lddtree` on each installed
   binary to verify runtime dependency declarations.
5. After separate confirmation, run `emerge --ask
app-accessibility/voxtype-bin`, inspect installed files, then unmerge and
   confirm Portage leaves no untracked package-owned files.

## Git and Publishing

Create clean, logical local commits: first repository metadata and
documentation, then the Voxtype package and Manifest after validation. Do not
create the GitHub repository, add an origin, or push until the user explicitly
selects GitHub visibility and authorizes that external action.
