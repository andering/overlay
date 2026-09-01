# Cloudflared OpenRC Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a generic `net-vpn/cloudflared-openrc` companion package that securely runs Gentoo's official `cloudflared` binary as a manually enabled, supervised OpenRC service.

**Architecture:** Keep the original version `1` ebuild and its `cloudflared.initd` and `cloudflared.confd` auxiliaries unchanged, then ship token-file hardening in revision `1-r1` with separate `cloudflared-r1.initd` and `cloudflared-r1.confd` sources. Both versions install their own sources to the standard `/etc/init.d/cloudflared` and `/etc/conf.d/cloudflared` destinations; only the unchanged logrotate source is shared. This preserves the effective v1 payload, not merely its ebuild text. Revision `1-r1` also installs an empty protected token file and requires `>=net-vpn/cloudflared-2025.4.0`, ensuring its `--token-file` interface is available during migration; version `1` retains its original unversioned dependency. `TUNNEL_TOKEN_FILE` defaults to `/etc/cloudflared/token`. `start_pre` unsets an inherited legacy `TUNNEL_TOKEN`, rejects non-absolute or unsafe token paths before file access, validates the token file, and only then interpolates the safe path into `command_args`. A separate upgrade validator uses real Portage merges under a generated, canonical, empty temporary `ROOT` that cannot be `/`; the normal Gentoo validator invokes it after both staged builds. Supervision logs to `/var/log/cloudflared.log` and `/var/log/cloudflared.err` and uses `respawn_max=0` for unlimited recovery. Logrotate bounds both files with weekly rotation and `copytruncate`.

The distributable package files must contain no host, domain, Cloudflare account, or tunnel-specific values.

**Tech Stack:** Gentoo EAPI 8, OpenRC, `supervise-daemon`, logrotate, Cloudflare Tunnel, Python `unittest`, pkgdev, pkgcheck.

---

## File Structure

- Create: `tests/test_cloudflared_openrc.py` - repository-level assertions for package contents, security constraints, and documentation.
- Create: `tests/validate_cloudflared_openrc_gentoo.sh` - executable, self-locating Gentoo package QA, build, and staged-image validation.
- Create: `tests/validate_cloudflared_openrc_upgrade_gentoo.sh` - executable real-merge CONFIG_PROTECT upgrade validation under a generated non-live Portage `ROOT`.
- Preserve: `net-vpn/cloudflared-openrc/cloudflared-openrc-1.ebuild` - committed version `1` package.
- Create: `net-vpn/cloudflared-openrc/cloudflared-openrc-1-r1.ebuild` - token-file hardening and migration guidance.
- Preserve: `net-vpn/cloudflared-openrc/files/cloudflared.initd` - original version `1` environment-token OpenRC service.
- Preserve: `net-vpn/cloudflared-openrc/files/cloudflared.confd` - original version `1` blank environment-token configuration.
- Create: `net-vpn/cloudflared-openrc/files/cloudflared-r1.initd` - hardened revision `1-r1` token-file OpenRC service stored with source mode `0644` and installed by `newinitd` with mode `0755`.
- Create: `net-vpn/cloudflared-openrc/files/cloudflared-r1.confd` - revision `1-r1` non-secret token-file path configuration.
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
EBUILD_V1 = PACKAGE / "cloudflared-openrc-1.ebuild"
EBUILD_R1 = PACKAGE / "cloudflared-openrc-1-r1.ebuild"
INITD_V1 = PACKAGE / "files" / "cloudflared.initd"
CONFD_V1 = PACKAGE / "files" / "cloudflared.confd"
INITD_R1 = PACKAGE / "files" / "cloudflared-r1.initd"
CONFD_R1 = PACKAGE / "files" / "cloudflared-r1.confd"
LOGROTATE = PACKAGE / "files" / "cloudflared.logrotated"
METADATA = PACKAGE / "metadata.xml"
GENTOO_VALIDATOR = ROOT / "tests" / "validate_cloudflared_openrc_gentoo.sh"


class CloudflaredOpenRCTest(unittest.TestCase):
    def test_package_files_exist(self):
        for path in (EBUILD_V1, EBUILD_R1, INITD_V1, CONFD_V1, INITD_R1, CONFD_R1, LOGROTATE, METADATA):
            with self.subTest(path=path):
                self.assertTrue(path.is_file())

    def test_ebuild_is_a_companion_package(self):
        text = EBUILD_R1.read_text()
        self.assertIn('EAPI=8', text)
        self.assertIn('S="${WORKDIR}"', text)
        self.assertIn('SLOT="0"', text)
        self.assertIn('KEYWORDS="~amd64 ~arm64"', text)
        self.assertIn('app-admin/logrotate', text)
        self.assertIn('>=net-vpn/cloudflared-2025.4.0', text)
        self.assertIn('sys-apps/openrc', text)
        self.assertIn('newinitd "${FILESDIR}/cloudflared-r1.initd" cloudflared', text)
        self.assertIn('newconfd "${FILESDIR}/cloudflared-r1.confd" cloudflared', text)
        self.assertIn('fperms 0644 /etc/conf.d/cloudflared', text)
        self.assertIn('touch "${ED}/etc/cloudflared/token" || die', text)
        self.assertIn('fowners root:root /etc/cloudflared/token', text)
        self.assertIn('fperms 0600 /etc/cloudflared/token', text)
        self.assertIn('newins "${FILESDIR}/cloudflared.logrotated" cloudflared', text)

    def test_service_uses_supervision_and_token_file(self):
        text = INITD_R1.read_text()
        self.assertTrue(text.startswith("#!/sbin/openrc-run\n"))
        self.assertIn('supervisor="supervise-daemon"', text)
        self.assertIn(': "${TUNNEL_TOKEN_FILE:=/etc/cloudflared/token}"', text)
        self.assertIn('command="/usr/bin/cloudflared"', text)
        self.assertIn('command_args="tunnel --no-autoupdate run --token-file ${TUNNEL_TOKEN_FILE}"', text)
        self.assertIn('output_log="/var/log/cloudflared.log"', text)
        self.assertIn('error_log="/var/log/cloudflared.err"', text)
        self.assertIn('respawn_delay="5"', text)
        self.assertIn('respawn_max="0"', text)
        self.assertIn('need net', text)
        self.assertNotIn('required_files=', text)
        self.assertNotIn('export TUNNEL_TOKEN', text)

    def test_service_rejects_insecure_token_files(self):
        text = INITD_R1.read_text()
        self.assertIn('if [ ! -f "${TUNNEL_TOKEN_FILE}" ]; then', text)
        self.assertIn("stat -c '%u:%g'", text)
        self.assertIn("stat -c '%a'", text)
        self.assertIn("grep -q '[^[:space:]]'", text)
        self.assertIn('return 1', text)

    def test_config_contains_only_the_token_file_path(self):
        text = CONFD_R1.read_text()
        self.assertIn('TUNNEL_TOKEN_FILE="/etc/cloudflared/token"', text)
        self.assertNotIn('TUNNEL_TOKEN="', text)
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
        mode = stat.S_IMODE(CONFD_R1.stat().st_mode)
        self.assertIn(mode, (0o600, 0o644))
        self.assertIn('fperms 0644 /etc/conf.d/cloudflared', EBUILD_R1.read_text())
        self.assertIn('fperms 0600 /etc/cloudflared/token', EBUILD_R1.read_text())

    def test_init_script_source_mode(self):
        self.assertEqual(stat.S_IMODE(INITD_V1.stat().st_mode), 0o644)
        self.assertEqual(stat.S_IMODE(INITD_R1.stat().st_mode), 0o644)

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

- Restore: `net-vpn/cloudflared-openrc/cloudflared-openrc-1.ebuild`
- Create: `net-vpn/cloudflared-openrc/cloudflared-openrc-1-r1.ebuild`
- Restore: `net-vpn/cloudflared-openrc/files/cloudflared.initd`
- Restore: `net-vpn/cloudflared-openrc/files/cloudflared.confd`
- Create: `net-vpn/cloudflared-openrc/files/cloudflared-r1.initd`
- Create: `net-vpn/cloudflared-openrc/files/cloudflared-r1.confd`
- Create: `net-vpn/cloudflared-openrc/files/cloudflared.logrotated`
- Create: `net-vpn/cloudflared-openrc/metadata.xml`

- [ ] **Step 1: Preserve version 1 and create the revision ebuild**

Restore `cloudflared-openrc-1.ebuild` to its committed content and create
`net-vpn/cloudflared-openrc/cloudflared-openrc-1-r1.ebuild`:

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
	>=net-vpn/cloudflared-2025.4.0
	sys-apps/openrc
"

src_install() {
	newinitd "${FILESDIR}/cloudflared-r1.initd" cloudflared
	newconfd "${FILESDIR}/cloudflared-r1.confd" cloudflared
	fperms 0644 /etc/conf.d/cloudflared
	dodir /etc/cloudflared
	touch "${ED}/etc/cloudflared/token" || die "failed to create token file"
	fowners root:root /etc/cloudflared/token
	fperms 0600 /etc/cloudflared/token
	insinto /etc/logrotate.d
	newins "${FILESDIR}/cloudflared.logrotated" cloudflared
}

pkg_postinst() {
	local legacy_confd="${EROOT}/etc/conf.d/cloudflared"
	local token_file="${EROOT}/etc/cloudflared/token"
	local legacy_assignment='^[[:space:]]*(export[[:space:]]+)?TUNNEL_TOKEN[[:space:]]*='

	if [[ -f ${legacy_confd} ]] && grep -Eq "${legacy_assignment}" "${legacy_confd}"; then
		ewarn "Legacy TUNNEL_TOKEN assignment detected in ${legacy_confd}."
		ewarn "Manually move only its token value into ${token_file}."
		ewarn "Set ${token_file} ownership to root:root and mode to 0600."
		ewarn "Remove the legacy TUNNEL_TOKEN assignment from ${legacy_confd}."
		ewarn "The token was not copied or printed automatically."
	fi

	elog "Store only the tunnel token in /etc/cloudflared/token."
	elog "Then enable and start the service manually:"
	elog "  rc-update add cloudflared default"
	elog "  rc-service cloudflared start"
}
```

Keep version `1` byte-for-byte unchanged with its unversioned
`net-vpn/cloudflared` dependency. The r1 floor guarantees that an upgrade pulls
in a binary supporting `--token-file` before the service migrates away from the
legacy environment-token invocation.

- [ ] **Step 2: Create the non-secret token-file path configuration**

Preserve the original version `1` `files/cloudflared.confd` byte-for-byte and
create `net-vpn/cloudflared-openrc/files/cloudflared-r1.confd`:

```sh
# Path to the token for one remotely managed Cloudflare Tunnel.
# The token file must contain only the token and remain root-owned with mode 0600.
TUNNEL_TOKEN_FILE="/etc/cloudflared/token"
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

Preserve the original version `1` `files/cloudflared.initd` byte-for-byte and
create `net-vpn/cloudflared-openrc/files/cloudflared-r1.initd`:

```sh
#!/sbin/openrc-run

# Copyright 2026 Andrej Kouril
# Distributed under the terms of the GNU General Public License v2

description="Cloudflare Tunnel connector"
supervisor="supervise-daemon"
: "${TUNNEL_TOKEN_FILE:=/etc/cloudflared/token}"
command="/usr/bin/cloudflared"
command_args="tunnel --no-autoupdate run --token-file ${TUNNEL_TOKEN_FILE}"
pidfile="/run/cloudflared.pid"
output_log="/var/log/cloudflared.log"
error_log="/var/log/cloudflared.err"
respawn_delay="5"
respawn_max="0"
retry="TERM/30/KILL/5"

depend() {
	need net
}

start_pre() {
	if [ ! -f "${TUNNEL_TOKEN_FILE}" ]; then
		eerror "Cloudflare Tunnel token file is missing or not a regular file: ${TUNNEL_TOKEN_FILE}"
		return 1
	fi

	local token_owner token_mode
	token_owner=$(stat -c '%u:%g' -- "${TUNNEL_TOKEN_FILE}") || return 1
	if [ "${token_owner}" != "0:0" ]; then
		eerror "Cloudflare Tunnel token file must be owned by UID:GID 0:0: ${TUNNEL_TOKEN_FILE}"
		return 1
	fi

	token_mode=$(stat -c '%a' -- "${TUNNEL_TOKEN_FILE}") || return 1
	if [ "${token_mode}" != "600" ]; then
		eerror "Cloudflare Tunnel token file mode must be 600: ${TUNNEL_TOKEN_FILE}"
		return 1
	fi

	if ! grep -q '[^[:space:]]' -- "${TUNNEL_TOKEN_FILE}"; then
		eerror "Cloudflare Tunnel token file is empty or whitespace-only: ${TUNNEL_TOKEN_FILE}"
		return 1
	fi
}
```

Keep the source init script non-executable so `pkgcheck` does not report an
unnecessary executable bit. The `newinitd` helper installs it with mode `0755`:

```sh
chmod 644 net-vpn/cloudflared-openrc/files/cloudflared.initd
chmod 644 net-vpn/cloudflared-openrc/files/cloudflared-r1.initd
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
    Tunnel connector with a protected token file and process
    supervision.
  </longdescription>
</pkgmetadata>
```

- [ ] **Step 6: Run focused tests and syntax checks**

Run from `/app/overlay`:

```sh
python3 -m unittest -v tests/test_cloudflared_openrc.py
bash -n net-vpn/cloudflared-openrc/files/cloudflared.initd
bash -n net-vpn/cloudflared-openrc/files/cloudflared-r1.initd
bash -n net-vpn/cloudflared-openrc/files/cloudflared-r1.confd
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
bash -n net-vpn/cloudflared-openrc/files/cloudflared-r1.initd
bash -n net-vpn/cloudflared-openrc/files/cloudflared-r1.confd
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
v1_initd_source="${package_dir}/files/cloudflared.initd"
v1_confd_source="${package_dir}/files/cloudflared.confd"
r1_initd_source="${package_dir}/files/cloudflared-r1.initd"
r1_confd_source="${package_dir}/files/cloudflared-r1.confd"
logrotate_source="${package_dir}/files/cloudflared.logrotated"

cd "${package_dir}"

bash -n "${v1_initd_source}" "${v1_confd_source}" "${r1_initd_source}" "${r1_confd_source}"
pkgdev manifest --force --verbose
test ! -e Manifest
pkgcheck scan --exit=error,warning,style,info cloudflared-openrc-1-r1.ebuild
ebuild cloudflared-openrc-1.ebuild clean install

v1_image_root="${PORTAGE_TMPDIR:-/var/tmp}/portage/net-vpn/cloudflared-openrc-1/image"
v1_initd="${v1_image_root}/etc/init.d/cloudflared"
v1_confd="${v1_image_root}/etc/conf.d/cloudflared"
v1_token_file="${v1_image_root}/etc/cloudflared/token"
v1_logrotate="${v1_image_root}/etc/logrotate.d/cloudflared"

cmp -s "${v1_initd_source}" "${v1_initd}"
cmp -s "${v1_confd_source}" "${v1_confd}"
cmp -s "${logrotate_source}" "${v1_logrotate}"
test -x "${v1_initd}"
test "$(stat -c '%a' "${v1_initd}")" = 755
test -f "${v1_confd}"
test "$(stat -c '%a' "${v1_confd}")" = 600
test -f "${v1_logrotate}"
test "$(stat -c '%a' "${v1_logrotate}")" = 644
test ! -e "${v1_token_file}"
! grep -Fq -- '--token-file' "${v1_initd}"
! grep -Fq 'TUNNEL_TOKEN_FILE' "${v1_confd}"
grep -Fq 'export TUNNEL_TOKEN' "${v1_initd}"

unset TUNNEL_TOKEN TUNNEL_TOKEN_FILE
. "${v1_confd}"
. "${v1_initd}"
test -z "${TUNNEL_TOKEN}"
test "${command_args}" = 'tunnel --no-autoupdate run'
test "${required_files}" = /etc/conf.d/cloudflared

eerror() {
	validation_error=$*
}

validation_error=
! start_pre
test "${validation_error}" = 'TUNNEL_TOKEN is empty in /etc/conf.d/cloudflared'
TUNNEL_TOKEN=validator-placeholder
start_pre
test "$(printenv TUNNEL_TOKEN)" = validator-placeholder
unset TUNNEL_TOKEN TUNNEL_TOKEN_FILE required_files

ebuild cloudflared-openrc-1-r1.ebuild clean install

r1_image_root="${PORTAGE_TMPDIR:-/var/tmp}/portage/net-vpn/cloudflared-openrc-1-r1/image"
r1_initd="${r1_image_root}/etc/init.d/cloudflared"
r1_confd="${r1_image_root}/etc/conf.d/cloudflared"
r1_token_file="${r1_image_root}/etc/cloudflared/token"
r1_logrotate="${r1_image_root}/etc/logrotate.d/cloudflared"

test "${v1_image_root}" != "${r1_image_root}"
test ! -e "${v1_token_file}"
cmp -s "${r1_initd_source}" "${r1_initd}"
cmp -s "${r1_confd_source}" "${r1_confd}"
cmp -s "${logrotate_source}" "${r1_logrotate}"
test -x "${r1_initd}"
test "$(stat -c '%a' "${r1_initd}")" = 755
test -f "${r1_confd}"
test "$(stat -c '%a' "${r1_confd}")" = 644
test "$(grep -Evc '^(#|$)' "${r1_confd}")" = 1
grep -Fxq 'TUNNEL_TOKEN_FILE="/etc/cloudflared/token"' "${r1_confd}"
! grep -Fq 'TUNNEL_TOKEN="' "${r1_confd}"
test -f "${r1_token_file}"
test "$(stat -c '%u:%g' "${r1_token_file}")" = 0:0
test "$(stat -c '%a' "${r1_token_file}")" = 600
test ! -s "${r1_token_file}"
test -f "${r1_logrotate}"
test "$(stat -c '%a' "${r1_logrotate}")" = 644
grep -Fq copytruncate "${r1_logrotate}"

unset TUNNEL_TOKEN_FILE
TUNNEL_TOKEN="migration-placeholder"
. "${r1_initd}"
test "${TUNNEL_TOKEN_FILE}" = /etc/cloudflared/token
unset TUNNEL_TOKEN TUNNEL_TOKEN_FILE

. "${r1_confd}"
. "${r1_initd}"
test "${command_args}" = 'tunnel --no-autoupdate run --token-file /etc/cloudflared/token'
! grep -Fq 'required_files=' "${r1_initd}"
! grep -Eq '(^|[[:space:]])export[[:space:]]+TUNNEL_TOKEN([[:space:]]|$)' "${r1_initd}"
grep -Fq 'output_log="/var/log/cloudflared.log"' "${r1_initd}"
grep -Fq 'error_log="/var/log/cloudflared.err"' "${r1_initd}"
grep -Fq 'respawn_max="0"' "${r1_initd}"

expect_start_pre_failure() {
	local expected_error=$1
	validation_error=
	! start_pre
	test "${validation_error}" = "${expected_error}"
}

TUNNEL_TOKEN_FILE="${r1_token_file}"

restore_token_file() {
	install -o 0 -g 0 -m 600 /dev/null "${r1_token_file}"
}

rm "${r1_token_file}"
expect_start_pre_failure "Cloudflare Tunnel token file is missing or not a regular file: ${TUNNEL_TOKEN_FILE}"

restore_token_file
chown 1:0 "${r1_token_file}"
expect_start_pre_failure "Cloudflare Tunnel token file must be owned by UID:GID 0:0: ${TUNNEL_TOKEN_FILE}"

restore_token_file
chmod 640 "${r1_token_file}"
expect_start_pre_failure "Cloudflare Tunnel token file mode must be 600: ${TUNNEL_TOKEN_FILE}"

restore_token_file
printf ' \t\n' > "${r1_token_file}"
expect_start_pre_failure "Cloudflare Tunnel token file is empty or whitespace-only: ${TUNNEL_TOKEN_FILE}"

restore_token_file
printf '%s\n' 'validator-placeholder' > "${r1_token_file}"
start_pre

# Run pkg_postinst against a temporary root with an active legacy assignment.
# Assert every migration instruction appears and the placeholder value does not.
restore_token_file

printf '%s\n' "cloudflared-openrc Gentoo validation passed for 1 and 1-r1"
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
bash -n net-vpn/cloudflared-openrc/files/cloudflared-r1.initd
bash -n net-vpn/cloudflared-openrc/files/cloudflared-r1.confd
bash -n tests/validate_cloudflared_openrc_gentoo.sh
bash -n tests/validate_cloudflared_openrc_upgrade_gentoo.sh
tests/validate_cloudflared_openrc_gentoo.sh
tests/validate_cloudflared_openrc_upgrade_gentoo.sh
git diff --check
git status --short
```

Expected: tests and syntax checks pass. The canonical tests prove the version `1` ebuild and both legacy auxiliaries remain unchanged while revision `1-r1` references only its hardened auxiliaries. The Gentoo validator syntax-checks both versions' source files, reports `manifest not needed, thin manifests and no distfiles: net-vpn/cloudflared-openrc::overlay`, leaves no `Manifest`, and runs strict version-level `pkgcheck scan --exit=error,warning,style,info cloudflared-openrc-1-r1.ebuild` without findings. It builds version `1` into its own Portage image root, compares installed init, conf, and logrotate files to the legacy sources, verifies modes, confirms no token file exists, and exercises the environment-token startup behavior. It then builds revision `1-r1` into a distinct image root and runs all hardened staged-file, safe-path, exported-token cleanup, token-file, startup-failure, valid-placeholder, and migration checks. The main validator invokes the isolated upgrade validator, which uses a generated guarded alternate Portage `ROOT` to perform real v1 and r1 merges and prove CONFIG_PROTECT behavior. The isolated validator prints `cloudflared-openrc isolated CONFIG_PROTECT upgrade validation passed`; only then does the main validator print `cloudflared-openrc Gentoo validation passed for 1 and 1-r1`. The version-level pkgcheck restriction keeps all strict r1 checks while avoiding the expected package-level redundancy report caused by retaining version `1`. `git diff --check` emits no output, and status lists only the intended package, tests, documentation, spec, and plan changes. Do not commit unless the user explicitly requests it.

### Task 5: Address Final Security And Upgrade Review

**Files:**

- Modify: `tests/test_cloudflared_openrc.py`
- Modify: `tests/validate_cloudflared_openrc_gentoo.sh`
- Create: `tests/validate_cloudflared_openrc_upgrade_gentoo.sh`
- Modify: `net-vpn/cloudflared-openrc/files/cloudflared-r1.initd`
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-09-01-cloudflared-openrc-package-design.md`
- Modify: `docs/superpowers/plans/2026-09-01-cloudflared-openrc-package.md`

- [ ] **Step 1: Add failing runtime and documentation contracts**

Extend the canonical r1 init expectation and focused tests so `start_pre` must
unset `TUNNEL_TOKEN`, reject relative paths and characters outside
`[A-Za-z0-9_./-]`, and assign `command_args` only after every validation check.
Exercise real sourced init behavior with paths containing a space and shell
metacharacters, plus a valid custom absolute path. Require removal documentation
to use quiet legacy-assignment detection and remove both credential files
without printing token content. Require an executable isolated upgrade
validator whose canonical script includes generated-root containment, non-`/`,
and empty-root guards.

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v \
  tests.test_cloudflared_openrc.CloudflaredOpenRCTest.test_r1_unsets_exported_legacy_token \
  tests.test_cloudflared_openrc.CloudflaredOpenRCTest.test_r1_rejects_unsafe_token_paths \
  tests.test_cloudflared_openrc.CloudflaredOpenRCTest.test_r1_accepts_safe_custom_absolute_token_path \
  tests.test_cloudflared_openrc.CloudflaredOpenRCTest.test_readme_documents_secure_legacy_credential_removal \
  tests.test_cloudflared_openrc.CloudflaredOpenRCTest.test_upgrade_validator_exists_and_is_executable
```

Expected: failures because r1 retains the exported variable, interpolates the
path before validation, the README omits legacy credential removal, and the
upgrade validator does not exist.

- [ ] **Step 3: Harden r1 startup minimally**

At the beginning of `start_pre`, run `unset TUNNEL_TOKEN`. Validate the path with
shell `case` patterns: one requiring a leading `/`, followed by one rejecting
`*[!A-Za-z0-9_./-]*`. Keep the existing regular-file, numeric-owner, mode, and
non-whitespace checks in order. Move:

```sh
command_args="tunnel --no-autoupdate run --token-file ${TUNNEL_TOKEN_FILE}"
```

to the end of `start_pre`, after all checks pass.

- [ ] **Step 4: Add the isolated real-merge upgrade validator**

Create `tests/validate_cloudflared_openrc_upgrade_gentoo.sh` with no positional
arguments. Generate a parent with `mktemp -d`, create its `root` child, resolve
both with `realpath -e`, and fail unless the root is non-`/`, is exactly a child
of the generated parent, and is empty. Set an EXIT trap before the first merge.
Merge v1 with `ROOT="${upgrade_root}" ebuild ... clean merge`, replace only the
isolated legacy conf with `export TUNNEL_TOKEN="upgrade-placeholder"`, then
merge r1 into the same root while capturing output. Verify quietly that:

- the legacy conf remains unchanged and mode `0600`;
- exactly one protected `._cfg????_cloudflared` r1 conf exists;
- the installed init is r1;
- `/etc/cloudflared/token` is initially empty, UID:GID `0:0`, mode `0600`;
- sourcing legacy conf and r1 init gives the safe default path;
- a valid placeholder token lets `start_pre` complete, removes
  `TUNNEL_TOKEN`, and creates safe path-only `command_args`;
- migration warnings are present and `upgrade-placeholder` is absent from
  captured output.

The main Gentoo validator invokes this script only after both staged versions
pass.

- [ ] **Step 5: Document safe removal and migration boundaries**

Update the README to quietly test legacy `/etc/conf.d/cloudflared` for either
`TUNNEL_TOKEN=` or `export TUNNEL_TOKEN=`, remove that file only when matched,
remove `/etc/cloudflared/token`, and rotate or revoke the Cloudflare token. State
that quiet matching and deletion never print the token and that rotation is
required because filesystem deletion is not guaranteed secure erasure.

- [ ] **Step 6: Run focused GREEN and complete verification**

Run the focused tests from Step 2, then the complete Python suite, `bash -n` for
both ebuilds, all legacy/r1 init/config sources, and both validators. In the
Gentoo container, run strict r1 pkgcheck, the dual-version validator, and the
isolated upgrade validator. Finally run `git diff --check`, confirm no Manifest
exists, and prove the v1 ebuild and both legacy auxiliaries have zero diff from
HEAD. Do not commit or push.

## Plan Review

- Spec coverage: Tasks 2, 4, and 5 preserve the version `1` ebuild, unversioned dependency, and legacy auxiliaries; add separate hardened revision `1-r1` auxiliaries and the `>=net-vpn/cloudflared-2025.4.0` migration floor; remove inherited legacy tokens; validate token paths before command construction; provide the safe default token path and ordered ownership/mode/content checks; emit non-disclosing legacy migration warnings; exercise a real CONFIG_PROTECT upgrade only below a generated non-live Portage root; retain path-only process arguments, OpenRC supervision with separate output and error logs and `respawn_max=0`, bounded weekly `copytruncate` log rotation, architecture keywords, dependencies, and manual enablement. Task 3 and Task 5 document installation, migration, operation, and removal. No package action provisions Cloudflare or changes runlevels.
- Placeholder scan: all package paths, file contents, test commands, and expected outcomes are explicit. The README instructs administrators to paste only the token and contains no example token value.
- Consistency: package atom, revision, v1 unversioned dependency, r1 minimum cloudflared version, version-specific source auxiliaries, distinct Portage image roots, shared logrotate path, installed service/config names, v1 environment-token behavior, r1 token-file behavior, exported-token cleanup, safe path grammar, post-validation command construction, migration and removal guidance, alternate-root CONFIG_PROTECT validation, architecture keywords, manifestless thin-manifest behavior, source-`0644`/installed-`0755` init-script modes, and both self-locating Gentoo validation entry points match across tests, implementation, and documentation.
