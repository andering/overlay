# Cloudflared OpenRC Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a generic `net-vpn/cloudflared-openrc` companion package that securely runs Gentoo's official `cloudflared` binary as a manually enabled, supervised OpenRC service.

**Architecture:** The package owns only an OpenRC init script, a protected blank configuration file, a logrotate policy, metadata, and documentation. `TUNNEL_TOKEN` is loaded from `/etc/conf.d/cloudflared` and exported to the daemon environment, while `supervise-daemon` logs to `/var/log/cloudflared.log` and `/var/log/cloudflared.err` and uses `respawn_max=0` for unlimited recovery without exposing the token in process arguments. Logrotate bounds both files with weekly rotation and `copytruncate`.

The distributable package files must contain no host, domain, Cloudflare account, or tunnel-specific values.

**Tech Stack:** Gentoo EAPI 8, OpenRC, `supervise-daemon`, logrotate, Cloudflare Tunnel, Python `unittest`, pkgdev, pkgcheck.

---

## File Structure

- Create: `tests/test_cloudflared_openrc.py` - repository-level assertions for package contents, security constraints, and documentation.
- Create: `tests/validate_cloudflared_openrc_gentoo.sh` - executable, self-locating Gentoo package QA, build, and staged-image validation.
- Create: `net-vpn/cloudflared-openrc/cloudflared-openrc-1.ebuild` - companion package definition and administrator guidance.
- Create: `net-vpn/cloudflared-openrc/files/cloudflared.initd` - supervised OpenRC service stored with source mode `0644` and installed by `newinitd` with mode `0755`.
- Create: `net-vpn/cloudflared-openrc/files/cloudflared.confd` - blank root-only token configuration template.
- Create: `net-vpn/cloudflared-openrc/files/cloudflared.logrotated` - bounded rotation policy for service logs.
- Create: `net-vpn/cloudflared-openrc/metadata.xml` - package maintainer and purpose metadata.
- Modify: `README.md` - overlay package list and cloudflared installation/operation instructions.

### Task 1: Add Failing Package Contract Tests

**Files:**

- Create: `tests/test_cloudflared_openrc.py`

- [ ] **Step 1: Write the package contract tests**

Create `tests/test_cloudflared_openrc.py`:

```python
import stat
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "net-vpn" / "cloudflared-openrc"
EBUILD = PACKAGE / "cloudflared-openrc-1.ebuild"
INITD = PACKAGE / "files" / "cloudflared.initd"
CONFD = PACKAGE / "files" / "cloudflared.confd"
LOGROTATE = PACKAGE / "files" / "cloudflared.logrotated"
METADATA = PACKAGE / "metadata.xml"
GENTOO_VALIDATOR = ROOT / "tests" / "validate_cloudflared_openrc_gentoo.sh"


class CloudflaredOpenRCTest(unittest.TestCase):
    def test_package_files_exist(self):
        for path in (EBUILD, INITD, CONFD, LOGROTATE, METADATA):
            with self.subTest(path=path):
                self.assertTrue(path.is_file())

    def test_ebuild_is_a_companion_package(self):
        text = EBUILD.read_text()
        self.assertIn('EAPI=8', text)
        self.assertIn('S="${WORKDIR}"', text)
        self.assertIn('SLOT="0"', text)
        self.assertIn('KEYWORDS="~amd64 ~arm64"', text)
        self.assertIn('app-admin/logrotate', text)
        self.assertIn('net-vpn/cloudflared', text)
        self.assertIn('sys-apps/openrc', text)
        self.assertIn('newinitd "${FILESDIR}/cloudflared.initd" cloudflared', text)
        self.assertIn('newconfd "${FILESDIR}/cloudflared.confd" cloudflared', text)
        self.assertIn('fperms 0600 /etc/conf.d/cloudflared', text)
        self.assertIn('newins "${FILESDIR}/cloudflared.logrotated" cloudflared', text)

    def test_service_uses_supervision_and_environment_token(self):
        text = INITD.read_text()
        self.assertTrue(text.startswith("#!/sbin/openrc-run\n"))
        self.assertIn('supervisor="supervise-daemon"', text)
        self.assertIn('command="/usr/bin/cloudflared"', text)
        self.assertIn('command_args="tunnel --no-autoupdate run"', text)
        self.assertIn('output_log="/var/log/cloudflared.log"', text)
        self.assertIn('error_log="/var/log/cloudflared.err"', text)
        self.assertIn('respawn_delay="5"', text)
        self.assertIn('respawn_max="0"', text)
        self.assertIn('need net', text)
        self.assertIn('export TUNNEL_TOKEN', text)
        self.assertNotIn('--token', text)

    def test_service_rejects_an_empty_token(self):
        text = INITD.read_text()
        self.assertIn('if [ -z "${TUNNEL_TOKEN}" ]; then', text)
        self.assertIn('/etc/conf.d/cloudflared', text)
        self.assertIn('return 1', text)

    def test_config_starts_blank(self):
        text = CONFD.read_text()
        self.assertIn('TUNNEL_TOKEN=""', text)
        self.assertNotIn('eyJ', text)

    def test_service_logs_are_rotated(self):
        self.assertEqual(LOGROTATE.read_text(), """/var/log/cloudflared.log /var/log/cloudflared.err {
\tweekly
\trotate 4
\tcompress
\tdelaycompress
\tmissingok
\tnotifempty
\tcopytruncate
}
""")

    def test_repository_does_not_store_a_secret_config(self):
        mode = stat.S_IMODE(CONFD.stat().st_mode)
        self.assertIn(mode, (0o600, 0o644))
        self.assertIn('fperms 0600 /etc/conf.d/cloudflared', EBUILD.read_text())

    def test_init_script_source_mode(self):
        self.assertEqual(stat.S_IMODE(INITD.stat().st_mode), 0o644)

    def test_gentoo_validator_exists_and_is_executable(self):
        self.assertTrue(GENTOO_VALIDATOR.is_file())
        self.assertEqual(stat.S_IMODE(GENTOO_VALIDATOR.stat().st_mode), 0o755)

    def test_readme_documents_manual_enablement(self):
        text = (ROOT / "README.md").read_text()
        self.assertIn("net-vpn/cloudflared-openrc", text)
        self.assertIn("rc-update add cloudflared default", text)
        self.assertIn("rc-service cloudflared start", text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and verify the package contract fails**

Run from `/app/overlay`:

```sh
python3 -m unittest -v tests/test_cloudflared_openrc.py
```

Expected: failures or errors because `net-vpn/cloudflared-openrc` and its README documentation do not exist yet.

### Task 2: Implement the Companion Package

**Files:**

- Create: `net-vpn/cloudflared-openrc/cloudflared-openrc-1.ebuild`
- Create: `net-vpn/cloudflared-openrc/files/cloudflared.initd`
- Create: `net-vpn/cloudflared-openrc/files/cloudflared.confd`
- Create: `net-vpn/cloudflared-openrc/files/cloudflared.logrotated`
- Create: `net-vpn/cloudflared-openrc/metadata.xml`

- [ ] **Step 1: Create the ebuild**

Create `net-vpn/cloudflared-openrc/cloudflared-openrc-1.ebuild`:

```bash
# Copyright 2026 Andrej Kouril
# Distributed under the terms of the GNU General Public License v2

EAPI=8

DESCRIPTION="OpenRC service integration for Cloudflare Tunnel"
HOMEPAGE="https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/"

S="${WORKDIR}"

LICENSE="GPL-2"
SLOT="0"
KEYWORDS="~amd64 ~arm64"

RDEPEND="
	app-admin/logrotate
	net-vpn/cloudflared
	sys-apps/openrc
"

src_install() {
	newinitd "${FILESDIR}/cloudflared.initd" cloudflared
	newconfd "${FILESDIR}/cloudflared.confd" cloudflared
	fperms 0600 /etc/conf.d/cloudflared
	insinto /etc/logrotate.d
	newins "${FILESDIR}/cloudflared.logrotated" cloudflared
}

pkg_postinst() {
	elog "Set TUNNEL_TOKEN in /etc/conf.d/cloudflared."
	elog "Then enable and start the service manually:"
	elog "  rc-update add cloudflared default"
	elog "  rc-service cloudflared start"
}
```

- [ ] **Step 2: Create the blank protected configuration**

Create `net-vpn/cloudflared-openrc/files/cloudflared.confd`:

```sh
# Token for one remotely managed Cloudflare Tunnel.
# Keep this file root-readable only and do not pass the token on the command line.
TUNNEL_TOKEN=""
```

- [ ] **Step 3: Create the log rotation policy**

Create `net-vpn/cloudflared-openrc/files/cloudflared.logrotated`:

```text
/var/log/cloudflared.log /var/log/cloudflared.err {
	weekly
	rotate 4
	compress
	delaycompress
	missingok
	notifempty
	copytruncate
}
```

- [ ] **Step 4: Create the supervised OpenRC service**

Create `net-vpn/cloudflared-openrc/files/cloudflared.initd`:

```sh
#!/sbin/openrc-run

# Copyright 2026 Andrej Kouril
# Distributed under the terms of the GNU General Public License v2

description="Cloudflare Tunnel connector"
supervisor="supervise-daemon"
command="/usr/bin/cloudflared"
command_args="tunnel --no-autoupdate run"
pidfile="/run/cloudflared.pid"
output_log="/var/log/cloudflared.log"
error_log="/var/log/cloudflared.err"
respawn_delay="5"
respawn_max="0"
retry="TERM/30/KILL/5"
required_files="/etc/conf.d/cloudflared"

depend() {
	need net
}

start_pre() {
	if [ -z "${TUNNEL_TOKEN}" ]; then
		eerror "TUNNEL_TOKEN is empty in /etc/conf.d/cloudflared"
		return 1
	fi

	export TUNNEL_TOKEN
}
```

Keep the source init script non-executable so `pkgcheck` does not report an
unnecessary executable bit. The `newinitd` helper installs it with mode `0755`:

```sh
chmod 644 net-vpn/cloudflared-openrc/files/cloudflared.initd
```

- [ ] **Step 5: Create package metadata**

Create `net-vpn/cloudflared-openrc/metadata.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE pkgmetadata SYSTEM "http://www.gentoo.org/dtd/metadata.dtd">
<pkgmetadata>
  <maintainer type="person">
    <email>andering@gmail.com</email>
    <name>Andrej Kouril</name>
  </maintainer>
  <longdescription lang="en">
    OpenRC service integration for running one remotely managed Cloudflare
    Tunnel connector with a protected environment token and process
    supervision.
  </longdescription>
</pkgmetadata>
```

- [ ] **Step 6: Run focused tests and syntax checks**

Run from `/app/overlay`:

```sh
python3 -m unittest -v tests/test_cloudflared_openrc.py
bash -n net-vpn/cloudflared-openrc/files/cloudflared.initd
```

Expected: package-content tests pass except the README test, which still fails; shell syntax check exits successfully.

### Task 3: Document Installation And Operation

**Files:**

- Modify: `README.md`

- [ ] **Step 1: Update the overlay introduction and package list**

Replace the opening description with:

```markdown
# andering/overlay

Gentoo overlay containing:

- `app-accessibility/voxtype-bin`
- `net-vpn/cloudflared-openrc`
- `x11-misc/eitype`
```

Leave the existing Voxtype instructions intact after this package list.

- [ ] **Step 2: Add the Cloudflared OpenRC section**

Insert this section before `## Updating And Removal`:

````markdown
## Cloudflared OpenRC

`net-vpn/cloudflared-openrc` installs an OpenRC service for Gentoo's official
`net-vpn/cloudflared` package. It supports one remotely managed Cloudflare
Tunnel per host and does not contain a tunnel token or enable itself.

Accept the testing keyword:

```text
net-vpn/cloudflared-openrc ~amd64
```

Install the package:

```sh
sudo emerge --ask net-vpn/cloudflared-openrc
```

Edit the root-only configuration with `sudoedit /etc/conf.d/cloudflared` and
set the token without placing it in shell history:

```sh
TUNNEL_TOKEN="your-remotely-managed-tunnel-token"
```

Enable and start the service explicitly:

```sh
sudo rc-update add cloudflared default
sudo rc-service cloudflared start
sudo rc-service cloudflared status
```

The token is passed through the daemon environment and does not appear in the
`cloudflared` command line. Removing the package does not remove Cloudflare-side
tunnels or DNS records.
````

- [ ] **Step 3: Extend removal instructions**

Add this command beside the existing package removal commands:

```sh
sudo rc-service cloudflared stop
sudo rc-update del cloudflared default
sudo emerge --ask --unmerge net-vpn/cloudflared-openrc
```

- [ ] **Step 4: Run the complete contract suite**

Run from `/app/overlay`:

```sh
python3 -m unittest -v tests/test_cloudflared_openrc.py
bash -n net-vpn/cloudflared-openrc/files/cloudflared.initd
```

Expected: all tests pass and shell syntax validation succeeds.

### Task 4: Add Reproducible Gentoo Validation

**Files:**

- Create: `tests/validate_cloudflared_openrc_gentoo.sh`
- Modify: `tests/test_cloudflared_openrc.py`

- [ ] **Step 1: Ensure Gentoo package development tools are available**

On a Gentoo environment with `/app/overlay` mounted, run:

```sh
emerge --ask --oneshot dev-util/pkgdev dev-util/pkgcheck
```

Expected: `pkgdev` and `pkgcheck` are available. If already installed, Portage makes no package changes.

- [ ] **Step 2: Add the Gentoo validation script contract**

Add `GENTOO_VALIDATOR` and `test_gentoo_validator_exists_and_is_executable`
to `tests/test_cloudflared_openrc.py` as shown in Task 1, then run from
`/app/overlay`:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v \
  tests.test_cloudflared_openrc.CloudflaredOpenRCTest.test_gentoo_validator_exists_and_is_executable
```

Expected: FAIL because `tests/validate_cloudflared_openrc_gentoo.sh` does not exist yet.

- [ ] **Step 3: Create the Gentoo validation script**

Create `tests/validate_cloudflared_openrc_gentoo.sh`:

```bash
#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "${script_dir}/.." && pwd)
package_dir="${repo_root}/net-vpn/cloudflared-openrc"

cd "${package_dir}"

pkgdev manifest --force --verbose
test ! -e Manifest
pkgcheck scan --exit=error,warning,style,info
ebuild cloudflared-openrc-1.ebuild clean install

image_root="${PORTAGE_TMPDIR:-/var/tmp}/portage/net-vpn/cloudflared-openrc-1/image"
initd="${image_root}/etc/init.d/cloudflared"
confd="${image_root}/etc/conf.d/cloudflared"
logrotate="${image_root}/etc/logrotate.d/cloudflared"

test -x "${initd}"
test "$(stat -c '%a' "${initd}")" = 755
test "$(stat -c '%a' "${confd}")" = 600
grep -Fxq 'TUNNEL_TOKEN=""' "${confd}"
test -f "${logrotate}"
test "$(stat -c '%a' "${logrotate}")" = 644
grep -Fq copytruncate "${logrotate}"
grep -Fq -- '--no-autoupdate run' "${initd}"
! grep -Fq -- '--token' "${initd}"
grep -Fq 'output_log="/var/log/cloudflared.log"' "${initd}"
grep -Fq 'error_log="/var/log/cloudflared.err"' "${initd}"
grep -Fq 'respawn_max="0"' "${initd}"

printf '%s\n' "cloudflared-openrc Gentoo validation passed"
```

Make the script executable:

```sh
chmod 755 tests/validate_cloudflared_openrc_gentoo.sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v \
  tests.test_cloudflared_openrc.CloudflaredOpenRCTest.test_gentoo_validator_exists_and_is_executable
bash -n tests/validate_cloudflared_openrc_gentoo.sh
```

Expected: the Python validator contract passes and `bash -n` accepts the script.

- [ ] **Step 4: Run final repository and Gentoo verification**

Run from the repository root in the Gentoo environment:

```sh
python3 -m unittest -v tests/test_cloudflared_openrc.py
bash -n net-vpn/cloudflared-openrc/files/cloudflared.initd
bash -n tests/validate_cloudflared_openrc_gentoo.sh
tests/validate_cloudflared_openrc_gentoo.sh
git diff --check
git status --short
```

Expected: tests and syntax checks pass. The Gentoo validator reports `manifest not needed, thin manifests and no distfiles: net-vpn/cloudflared-openrc::overlay`, leaves no `Manifest`, runs `pkgcheck scan --exit=error,warning,style,info` without findings, builds the temporary image, verifies all staged modes and content, and prints `cloudflared-openrc Gentoo validation passed`. `git diff --check` emits no output, and status lists only the intended package, tests, documentation, spec, and plan changes. Do not commit unless the user explicitly requests it.

## Plan Review

- Spec coverage: Tasks 2 and 4 implement the generic companion package, secure environment token, OpenRC supervision with separate output and error logs and `respawn_max=0`, bounded weekly `copytruncate` log rotation, empty-token failure, protected config mode, architecture keywords, dependencies, and manual enablement. Task 3 documents installation, operation, and removal. No package action provisions Cloudflare or changes runlevels.
- Placeholder scan: all package paths, file contents, test commands, and expected outcomes are explicit. The README's example token is documentation only and cannot run.
- Consistency: package atom, service name, config path, logrotate path, environment variable, runtime command, architecture keywords, manifestless thin-manifest behavior, source-`0644`/installed-`0755` init-script modes, and the self-locating Gentoo validation entry point match across tests, implementation, and documentation.
