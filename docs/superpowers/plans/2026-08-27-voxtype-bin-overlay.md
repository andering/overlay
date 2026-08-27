# Voxtype Binary Overlay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a Git-backed EAPI 8 Gentoo overlay that installs the pinned Voxtype 0.7.5 CPU or Vulkan binary safely through Portage on KDE Plasma Wayland and OpenRC.

**Architecture:** The overlay packages one upstream raw binary selected at build time with the `vulkan` USE flag. An accompanying signed-release source archive supplies documentation and desktop assets; the ebuild installs only Portage-owned files and has no service or privilege-changing phases. Optional XDG KDE autostart is isolated behind the local `autostart` USE flag.

**Tech Stack:** Gentoo Portage, EAPI 8, Bash ebuild helpers, pkgdev, pkgcheck, Git.

---

## File Structure

| Path                                                            | Responsibility                                                            |
| --------------------------------------------------------------- | ------------------------------------------------------------------------- |
| `metadata/layout.conf`                                          | Declares the Gentoo master and thin Manifests for this repository.        |
| `profiles/repo_name`                                            | Defines the Portage repository identifier as `overlay`.                   |
| `profiles/use.local.desc`                                       | Documents the local `autostart` USE flag.                                 |
| `app-accessibility/voxtype-bin/voxtype-bin-0.7.5.ebuild`        | Fetches, verifies, and installs the selected upstream binary plus assets. |
| `app-accessibility/voxtype-bin/metadata.xml`                    | Package maintainer and upstream metadata.                                 |
| `app-accessibility/voxtype-bin/files/voxtype-configure.desktop` | Visible desktop launcher for the configuration TUI.                       |
| `app-accessibility/voxtype-bin/files/voxtype-daemon.desktop`    | Optional KDE-only XDG autostart entry.                                    |
| `README.md`                                                     | Multi-machine installation and KDE/OpenRC operating guide.                |
| `.gitignore`                                                    | Excludes local Portage and editor artifacts only.                         |
| `app-accessibility/voxtype-bin/Manifest`                        | Portage-generated checksums for every fetched distfile.                   |

### Task 1: Author Repository Metadata and Usage Documentation

**Files:**

- Create: `metadata/layout.conf`
- Create: `profiles/repo_name`
- Create: `profiles/use.local.desc`
- Create: `.gitignore`
- Create: `README.md`

- [ ] **Step 1: Write the repository structure check before adding package files**

Run:

```bash
test ! -e metadata/layout.conf
test ! -e profiles/repo_name
test ! -e app-accessibility/voxtype-bin
```

Expected: all commands exit successfully because the empty repository has no
Portage metadata yet.

- [ ] **Step 2: Create the repository metadata**

Create `metadata/layout.conf`:

```ini
masters = gentoo
thin-manifests = true
```

Create `profiles/repo_name`:

```text
overlay
```

Create `profiles/use.local.desc`:

```text
autostart - Install a KDE-only XDG autostart entry for the Voxtype daemon
```

Create `.gitignore`:

```gitignore
# Local Portage and QA artifacts
distfiles/
packages/
.pkgcheck/

# Editor and operating-system metadata
.DS_Store
*~
```

- [ ] **Step 3: Write the top-level README**

Create `README.md` with these exact operational sections and commands:

````markdown
# andering/overlay

Personal Gentoo overlay containing `app-accessibility/voxtype-bin`.

## Add The Overlay

After the repository is available at `https://github.com/andering/overlay.git`:

```bash
sudo eselect repository add overlay git https://github.com/andering/overlay.git
sudo emaint sync -r overlay
```

Manual alternative, create `/etc/portage/repos.conf/overlay.conf`:

```ini
[overlay]
location = /var/db/repos/overlay
sync-type = git
sync-uri = https://github.com/andering/overlay.git
masters = gentoo
auto-sync = yes
```

Then clone and synchronize it:

```bash
sudo git clone https://github.com/andering/overlay.git /var/db/repos/overlay
sudo emaint sync -r overlay
```

## Install Voxtype

```bash
sudo emerge --ask app-accessibility/voxtype-bin
```

The default installs Voxtype's official x86-64-v3 AVX2 CPU binary. Enable
Vulkan independently on machines with a working Vulkan stack:

```bash
echo 'app-accessibility/voxtype-bin vulkan' | sudo tee /etc/portage/package.use/voxtype
sudo emerge --ask app-accessibility/voxtype-bin
```

Use CPU on a different machine with:

```bash
echo 'app-accessibility/voxtype-bin -vulkan' | sudo tee /etc/portage/package.use/voxtype
sudo emerge --ask app-accessibility/voxtype-bin
```

Both upstream binaries require AVX2. This package is keyworded `~amd64`.

## First Run And Czech Dictation

Run the setup wizard in the logged-in graphical session:

```bash
voxtype setup
voxtype setup model
```

For Czech, select a multilingual Whisper model such as `base`, `small`, or
`large-v3-turbo`; do not select a `.en` model. In
`~/.config/voxtype/config.toml`, use:

```toml
[whisper]
model = "base"
language = "cs"
```

Models and per-user configuration are stored below XDG user directories and
are intentionally not installed or removed by Portage.

## KDE Plasma Wayland On OpenRC

Voxtype must run in the logged-in KDE/PipeWire session. Do not create a
systemd unit. Add `voxtype daemon` in System Settings > Autostart, or opt in
to the packaged KDE-only autostart entry:

```bash
echo 'app-accessibility/voxtype-bin autostart' | sudo tee /etc/portage/package.use/voxtype
sudo emerge --ask app-accessibility/voxtype-bin
```

Use a KDE global shortcut instead of the evdev listener. In
`~/.config/voxtype/config.toml` set:

```toml
[hotkey]
enabled = false
mode = "toggle"
```

Then open System Settings > Shortcuts > Custom Shortcuts, create a Command or
URL action, assign a shortcut such as Meta+V, and set its command to:

```text
voxtype record toggle
```

KWin does not provide a key-release binding, so toggle mode is preferred over
push-to-talk for a KDE shortcut.

`gui-apps/wl-clipboard` provides clipboard output/fallback. KDE Wayland needs
a compatible text-injection backend such as eitype or dotool for direct typing;
`wtype` does not work with KWin's Wayland protocol support. `x11-misc/ydotool`
is only a fallback. If it is chosen, configure `ydotoold`, `/dev/uinput`, and
any permissions yourself; this overlay never starts the daemon or changes
users or groups. The `input` group is unnecessary when using the KDE shortcut.

## Update And Remove

```bash
sudo emaint sync -r overlay
sudo emerge --ask --update --deep --newuse app-accessibility/voxtype-bin
sudo emerge --ask --depclean
sudo emerge --ask --unmerge app-accessibility/voxtype-bin
```

Unmerge removes only Portage-owned files. To remove optional personal data,
review and then delete `~/.config/voxtype` and `~/.local/share/voxtype`.
````

- [ ] **Step 4: Verify the metadata and README before package implementation**

Run:

```bash
test "$(tr -d '\n' < profiles/repo_name)" = overlay
grep -Fx 'masters = gentoo' metadata/layout.conf
grep -Fx 'thin-manifests = true' metadata/layout.conf
grep -F 'voxtype record toggle' README.md
grep -F 'language = "cs"' README.md
```

Expected: every command succeeds, proving the repository name, master,
Manifest policy, KDE shortcut, and Czech configuration are documented.

- [ ] **Step 5: Commit the repository foundation**

```bash
git add metadata/layout.conf profiles/repo_name profiles/use.local.desc .gitignore README.md
git commit -m "chore: add Gentoo overlay metadata"
```

### Task 2: Add the Pinned EAPI 8 Binary Package

**Files:**

- Create: `app-accessibility/voxtype-bin/voxtype-bin-0.7.5.ebuild`
- Create: `app-accessibility/voxtype-bin/metadata.xml`
- Create: `app-accessibility/voxtype-bin/files/voxtype-configure.desktop`
- Create: `app-accessibility/voxtype-bin/files/voxtype-daemon.desktop`

- [ ] **Step 1: Create the desktop entries before the ebuild consumes them**

Create `app-accessibility/voxtype-bin/files/voxtype-configure.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=Voxtype Configuration
GenericName=Voice-to-Text Settings
Comment=Configure Voxtype dictation settings
Exec=voxtype configure
Icon=voxtype
Categories=Settings;Accessibility;
Keywords=voxtype;voice;dictation;transcription;whisper;
Terminal=true
StartupWMClass=voxtype
```

Create `app-accessibility/voxtype-bin/files/voxtype-daemon.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=Voxtype Daemon
Comment=Start the Voxtype dictation daemon in KDE Plasma
Exec=voxtype daemon
Icon=voxtype
Terminal=false
OnlyShowIn=KDE;
X-KDE-autostart-after=panel
```

- [ ] **Step 2: Write the failing package-content checks**

Run:

```bash
test -f app-accessibility/voxtype-bin/voxtype-bin-0.7.5.ebuild
```

Expected: failure because the EAPI 8 ebuild does not exist yet.

- [ ] **Step 3: Create the complete EAPI 8 ebuild**

Create `app-accessibility/voxtype-bin/voxtype-bin-0.7.5.ebuild`:

```bash
# Copyright 2026 Andrej Kouril
# Distributed under the terms of the GNU General Public License v2

EAPI=8

inherit desktop

DESCRIPTION="Push-to-talk voice-to-text for Wayland Linux systems"
HOMEPAGE="https://voxtype.io https://github.com/peteonrails/voxtype"
SRC_URI="
    https://github.com/peteonrails/voxtype/archive/refs/tags/v${PV}.tar.gz -> ${P}.tar.gz
    !vulkan? ( https://github.com/peteonrails/voxtype/releases/download/v${PV}/voxtype-${PV}-linux-x86_64-avx2 -> ${PN}-${PV}-linux-x86_64-avx2 )
    vulkan? ( https://github.com/peteonrails/voxtype/releases/download/v${PV}/voxtype-${PV}-linux-x86_64-vulkan -> ${PN}-${PV}-linux-x86_64-vulkan )
"

S="${WORKDIR}/voxtype-${PV}"

LICENSE="MIT"
SLOT="0"
KEYWORDS="~amd64"
IUSE="autostart vulkan"
RESTRICT="mirror"

RDEPEND="
    media-libs/alsa-lib
    media-video/pipewire[pipewire-alsa]
    vulkan? ( media-libs/vulkan-loader )
"

src_unpack() {
    unpack "${P}.tar.gz"
}

src_install() {
    local binary

    if use vulkan; then
        binary="${DISTDIR}/${PN}-${PV}-linux-x86_64-vulkan"
    else
        binary="${DISTDIR}/${PN}-${PV}-linux-x86_64-avx2"
    fi

    newbin "${binary}" voxtype
    doicon packaging/appimage/voxtype.svg
    domenu "${FILESDIR}/voxtype-configure.desktop"
    domenu packaging/appimage/voxtype.desktop

    if use autostart; then
        insinto /etc/xdg/autostart
        newins "${FILESDIR}/voxtype-daemon.desktop" voxtype-daemon.desktop
    fi

    dodoc README.md docs/INSTALL.md docs/USER_MANUAL.md docs/CONFIGURATION.md LICENSE
}
```

- [ ] **Step 4: Add package metadata**

Create `app-accessibility/voxtype-bin/metadata.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE pkgmetadata SYSTEM "http://www.gentoo.org/dtd/metadata.dtd">
<pkgmetadata>
  <maintainer type="person">
    <email>andering@gmail.com</email>
    <name>Andrej Kouril</name>
  </maintainer>
  <upstream>
    <remote-id type="github">peteonrails/voxtype</remote-id>
  </upstream>
  <longdescription lang="en">
    Prebuilt Voxtype push-to-talk voice-to-text binary for Linux Wayland
    sessions. The package provides CPU and Vulkan Whisper variants.
  </longdescription>
</pkgmetadata>
```

- [ ] **Step 5: Validate EAPI, metadata, and desktop semantics**

Run:

```bash
grep -Fx 'EAPI=8' app-accessibility/voxtype-bin/voxtype-bin-0.7.5.ebuild
grep -F 'voxtype-0.7.5-linux-x86_64-avx2' app-accessibility/voxtype-bin/voxtype-bin-0.7.5.ebuild
grep -F 'voxtype-0.7.5-linux-x86_64-vulkan' app-accessibility/voxtype-bin/voxtype-bin-0.7.5.ebuild
grep -F 'OnlyShowIn=KDE;' app-accessibility/voxtype-bin/files/voxtype-daemon.desktop
grep -F 'Exec=voxtype configure' app-accessibility/voxtype-bin/files/voxtype-configure.desktop
grep -F 'peteonrails/voxtype' app-accessibility/voxtype-bin/metadata.xml
```

Expected: every command succeeds. The package has exact asset names, does not
ship a systemd unit, and exposes the correct upstream identifier.

- [ ] **Step 6: Commit the initial package definition**

```bash
git add app-accessibility/voxtype-bin/voxtype-bin-0.7.5.ebuild app-accessibility/voxtype-bin/metadata.xml app-accessibility/voxtype-bin/files
git commit -m "feat: add Voxtype binary ebuild"
```

### Task 3: Obtain QA Tools and Verify Release Artifacts

**Files:**

- Modify: `app-accessibility/voxtype-bin/voxtype-bin-0.7.5.ebuild` only if `lddtree` identifies a non-system linked-library provider not already declared in `RDEPEND`.
- Create: `app-accessibility/voxtype-bin/Manifest`

- [ ] **Step 1: Request explicit authorization before the first sudo/emerge operation**

Ask exactly: "May I run `sudo emerge --ask dev-util/pkgdev dev-util/pkgcheck`
to install the Gentoo QA tools required for Manifest generation and package
validation?"

Do not run an emerge command until the user confirms.

- [ ] **Step 2: Install the requested QA tools after approval**

Run:

```bash
sudo emerge --ask dev-util/pkgdev dev-util/pkgcheck
```

Expected: Portage presents the dependency plan and waits for confirmation;
after confirmation, both commands become available on `PATH`.

- [ ] **Step 3: Generate the Manifest through Portage tooling**

Run from `/app/overlay`:

```bash
pkgdev manifest
```

Expected: `app-accessibility/voxtype-bin/Manifest` contains SHA-256 entries
for the v0.7.5 source archive, AVX2 binary, and Vulkan binary. Verify the
upstream binary digests match:

```bash
grep -F '18ae0510d0c964689f8c9b7119c0b9a45569985e82977dc4f1ef4d76fddd887c' app-accessibility/voxtype-bin/Manifest
grep -F '64626d07f3aae2825ddb82ea66878f708c8a820a3fd3ece76d99ff98477f132d' app-accessibility/voxtype-bin/Manifest
```

- [ ] **Step 4: Exercise both ebuild variants without merging**

Run:

```bash
ebuild app-accessibility/voxtype-bin/voxtype-bin-0.7.5.ebuild clean unpack prepare compile install
USE="vulkan" ebuild app-accessibility/voxtype-bin/voxtype-bin-0.7.5.ebuild clean unpack prepare compile install
USE="vulkan autostart" ebuild app-accessibility/voxtype-bin/voxtype-bin-0.7.5.ebuild clean unpack prepare compile install
```

Expected: all three invocations exit successfully. `compile` is a no-op because
the package installs a verified upstream binary.

- [ ] **Step 5: Inspect staged trees and linked libraries**

For each completed ebuild invocation, identify the `image` directory reported
by Portage and run:

```bash
find "${IMAGE_DIR}" -type f -o -type l
lddtree "${IMAGE_DIR}/usr/bin/voxtype"
```

Expected CPU tree: `/usr/bin/voxtype`, one SVG icon, the visible configuration
desktop entry, the hidden daemon desktop entry, and documentation under
`/usr/share/doc/voxtype-bin-0.7.5`.

Expected Vulkan tree: the same files plus
`/etc/xdg/autostart/voxtype-daemon.desktop` only when tested with
`USE="vulkan autostart"`.

Confirm `libasound.so.2` resolves through `media-libs/alsa-lib` and the Vulkan
binary resolves `libvulkan.so.1` through `media-libs/vulkan-loader`. Add an
explicit RDEPEND atom only for a non-system provider shown by `lddtree` that
is not already listed, then rerun both ebuild commands.

- [ ] **Step 6: Run package QA and fix meaningful findings**

Run from `/app/overlay`:

```bash
pkgcheck scan
```

Expected: no errors. Correct all actionable errors and warnings in the ebuild,
metadata, desktop files, or Manifest, then rerun `pkgdev manifest` and
`pkgcheck scan` until clean.

- [ ] **Step 7: Commit the validated Manifest and any dependency correction**

```bash
git add app-accessibility/voxtype-bin/voxtype-bin-0.7.5.ebuild app-accessibility/voxtype-bin/Manifest
git commit -m "chore: verify Voxtype release artifacts"
```

### Task 4: Perform an Authorized Merge/Unmerge Lifecycle Test

**Files:**

- No source files changed unless validation exposes a package defect.

- [ ] **Step 1: Request separate permission for a system package lifecycle test**

Ask exactly: "May I run `sudo emerge --ask
app-accessibility/voxtype-bin`, inspect its installed files, and unmerge it to
verify that the package leaves no Portage-untracked files?"

Do not merge or unmerge the package without confirmation.

- [ ] **Step 2: Merge the CPU default after approval**

Run:

```bash
sudo emerge --ask app-accessibility/voxtype-bin
qlist -I app-accessibility/voxtype-bin
```

Expected: Portage owns the binary, desktop entries, icon, and documentation.
No systemd unit, OpenRC service, users, groups, or ydotool daemon are added.

- [ ] **Step 3: Validate the installed executable in the graphical session**

Run:

```bash
voxtype --version
voxtype setup
```

Expected: the version reports 0.7.5 and the setup command reports the current
audio, model, and optional output integration state without changing groups or
starting services.

- [ ] **Step 4: Unmerge and check Portage ownership boundaries**

Run:

```bash
sudo emerge --ask --unmerge app-accessibility/voxtype-bin
qlist -I app-accessibility/voxtype-bin
```

Expected: the final `qlist` has no output. Verify that no package-owned files
remain in `/usr/bin/voxtype`, `/usr/share/applications`,
`/usr/share/icons`, `/usr/share/doc`, or `/etc/xdg/autostart`; retain user
model/configuration directories unless the user chooses to remove them.

### Task 5: Final Git Verification and Publishing Boundary

**Files:**

- Modify: `README.md` only if commands or observed behavior changed during validation.

- [ ] **Step 1: Verify the final repository state**

Run:

```bash
git status --short
git log --oneline --decorate -10
git diff main~3..main --check
```

Expected: no uncommitted files, logical documentation/package/validation
commits, and no whitespace errors.

- [ ] **Step 2: Confirm the required overlay inventory**

Run:

```bash
test -f metadata/layout.conf
test -f profiles/repo_name
test -f app-accessibility/voxtype-bin/voxtype-bin-0.7.5.ebuild
test -f app-accessibility/voxtype-bin/metadata.xml
test -f app-accessibility/voxtype-bin/Manifest
test -f README.md
```

Expected: every command succeeds.

- [ ] **Step 3: Preserve the external publishing gate**

Do not create `andering/overlay`, configure an `origin`, change GitHub
visibility, or push. Ask the user for explicit authorization and whether the
repository should be public or private before any GitHub operation.
