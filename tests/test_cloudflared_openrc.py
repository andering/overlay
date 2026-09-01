import os
import stat
import subprocess
import tempfile
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
UPGRADE_VALIDATOR = ROOT / "tests" / "validate_cloudflared_openrc_upgrade_gentoo.sh"

EXPECTED_EBUILD_V1 = """# Copyright 2026 Andrej Kouril
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
"""

EXPECTED_EBUILD_R1 = """# Copyright 2026 Andrej Kouril
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
"""

EXPECTED_INITD_V1 = """#!/sbin/openrc-run

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
"""

EXPECTED_INITD_R1 = """#!/sbin/openrc-run

# Copyright 2026 Andrej Kouril
# Distributed under the terms of the GNU General Public License v2

description="Cloudflare Tunnel connector"
supervisor="supervise-daemon"
: "${TUNNEL_TOKEN_FILE:=/etc/cloudflared/token}"
command="/usr/bin/cloudflared"
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
	unset TUNNEL_TOKEN

	case "${TUNNEL_TOKEN_FILE}" in
		/*) ;;
		*)
			eerror "Cloudflare Tunnel token file path must be absolute"
			return 1
			;;
	esac

	case "${TUNNEL_TOKEN_FILE}" in
		*[!A-Za-z0-9_./-]*)
			eerror "Cloudflare Tunnel token file path contains unsafe characters"
			return 1
			;;
	esac

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

	command_args="tunnel --no-autoupdate run --token-file ${TUNNEL_TOKEN_FILE}"
}
"""

EXPECTED_CONFD_V1 = """# Token for one remotely managed Cloudflare Tunnel.
# Keep this file root-readable only and do not pass the token on the command line.
TUNNEL_TOKEN=""
"""

EXPECTED_CONFD_R1 = """# Path to the token for one remotely managed Cloudflare Tunnel.
# The token file must contain only the token and remain root-owned with mode 0600.
TUNNEL_TOKEN_FILE="/etc/cloudflared/token"
"""

EXPECTED_LOGROTATE = """/var/log/cloudflared.log /var/log/cloudflared.err {
	weekly
	rotate 4
	compress
	delaycompress
	missingok
	notifempty
	copytruncate
}
"""

EXPECTED_METADATA = """<?xml version="1.0" encoding="UTF-8"?>
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
"""

EXPECTED_GENTOO_VALIDATOR = """#!/usr/bin/env bash

set -euo pipefail

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "${script_dir}/.." && pwd)
package_dir="${repo_root}/net-vpn/cloudflared-openrc"
upgrade_validator="${script_dir}/validate_cloudflared_openrc_upgrade_gentoo.sh"
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

restore_token_file() {
	install -o 0 -g 0 -m 600 /dev/null "${r1_token_file}"
}

migration_root=$(mktemp -d "${PORTAGE_TMPDIR:-/var/tmp}/cloudflared-openrc-migration.XXXXXX")
cleanup() {
	restore_token_file
	rm -rf "${migration_root}"
}
trap cleanup EXIT

mkdir -p "${migration_root}/etc/conf.d"
printf '%s\\n' 'export TUNNEL_TOKEN="migration-placeholder"' >"${migration_root}/etc/conf.d/cloudflared"

unset TUNNEL_TOKEN TUNNEL_TOKEN_FILE command_args
. "${migration_root}/etc/conf.d/cloudflared"
. "${r1_initd}"
test "${TUNNEL_TOKEN_FILE}" = /etc/cloudflared/token
test -z "${command_args+x}"
TUNNEL_TOKEN_FILE="${r1_token_file}"
restore_token_file
printf '%s\\n' 'validator-placeholder' >"${r1_token_file}"
start_pre
test -z "${TUNNEL_TOKEN+x}"
test "${command_args}" = "tunnel --no-autoupdate run --token-file ${r1_token_file}"
unset TUNNEL_TOKEN TUNNEL_TOKEN_FILE command_args

. "${r1_confd}"
. "${r1_initd}"

test -z "${command_args+x}"
! grep -Fq 'required_files=' "${r1_initd}"
! grep -Eq '(^|[[:space:]])export[[:space:]]+TUNNEL_TOKEN([[:space:]]|$)' "${r1_initd}"
grep -Fq 'output_log="/var/log/cloudflared.log"' "${r1_initd}"
grep -Fq 'error_log="/var/log/cloudflared.err"' "${r1_initd}"
grep -Fq 'respawn_max="0"' "${r1_initd}"

expect_start_pre_failure() {
	local expected_error=$1
	validation_error=
	unset command_args
	! start_pre
	test "${validation_error}" = "${expected_error}"
	test -z "${command_args+x}"
}

TUNNEL_TOKEN_FILE=relative/token
expect_start_pre_failure "Cloudflare Tunnel token file path must be absolute"

TUNNEL_TOKEN_FILE="/tmp/cloudflared token"
expect_start_pre_failure "Cloudflare Tunnel token file path contains unsafe characters"

TUNNEL_TOKEN_FILE='/tmp/cloudflared;token'
expect_start_pre_failure "Cloudflare Tunnel token file path contains unsafe characters"

TUNNEL_TOKEN_FILE="${r1_token_file}"

rm "${r1_token_file}"
expect_start_pre_failure "Cloudflare Tunnel token file is missing or not a regular file: ${TUNNEL_TOKEN_FILE}"

restore_token_file
chown 1:0 "${r1_token_file}"
expect_start_pre_failure "Cloudflare Tunnel token file must be owned by UID:GID 0:0: ${TUNNEL_TOKEN_FILE}"

restore_token_file
chmod 640 "${r1_token_file}"
expect_start_pre_failure "Cloudflare Tunnel token file mode must be 600: ${TUNNEL_TOKEN_FILE}"

restore_token_file
printf ' \\t\\n' >"${r1_token_file}"
expect_start_pre_failure "Cloudflare Tunnel token file is empty or whitespace-only: ${TUNNEL_TOKEN_FILE}"

restore_token_file
printf '%s\\n' 'validator-placeholder' >"${r1_token_file}"
start_pre
test "${command_args}" = "tunnel --no-autoupdate run --token-file ${r1_token_file}"

migration_output=$(
	EROOT="${migration_root}" WORKDIR="${migration_root}/work" bash -c '
		ewarn() { printf "warning:%s\\n" "$*"; }
		elog() { :; }
		source "$1"
		pkg_postinst
	' bash "${package_dir}/cloudflared-openrc-1-r1.ebuild"
)
grep -Fq "Legacy TUNNEL_TOKEN assignment detected in ${migration_root}/etc/conf.d/cloudflared." <<<"${migration_output}"
grep -Fq "Manually move only its token value into ${migration_root}/etc/cloudflared/token." <<<"${migration_output}"
grep -Fq "Set ${migration_root}/etc/cloudflared/token ownership to root:root and mode to 0600." <<<"${migration_output}"
grep -Fq "Remove the legacy TUNNEL_TOKEN assignment from ${migration_root}/etc/conf.d/cloudflared." <<<"${migration_output}"
grep -Fq 'The token was not copied or printed automatically.' <<<"${migration_output}"
! grep -Fq 'migration-placeholder' <<<"${migration_output}"

restore_token_file
trap - EXIT
rm -rf "${migration_root}"

"${upgrade_validator}"

printf '%s\\n' "cloudflared-openrc Gentoo validation passed for 1 and 1-r1"
"""

EXPECTED_README_INTRO = """# andering/overlay

Gentoo overlay containing:

- `app-accessibility/voxtype-bin`
- `net-vpn/cloudflared-openrc`
- `x11-misc/eitype`
"""

EXPECTED_README_SECTION = """## Cloudflared OpenRC

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
"""

EXPECTED_README_UPDATE = """sudo emerge --update --deep --ask net-vpn/cloudflared-openrc
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
also unsets an inherited legacy `TUNNEL_TOKEN` before launching `cloudflared`."""

EXPECTED_README_REMOVAL = """sudo rc-service cloudflared stop
sudo rc-update del cloudflared default
sudo emerge --ask --unmerge net-vpn/cloudflared-openrc
```

Quietly check whether the preserved legacy configuration still contains a token
assignment, and remove it without displaying the token. Also remove the r1 token
file:

```sh
if sudo test -f /etc/conf.d/cloudflared && \\
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
Cloudflare error 1016."""


def normalize_newlines(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text[:-1] if text.endswith("\n") else text


class CloudflaredOpenRCTest(unittest.TestCase):
    def test_package_files_exist(self):
        for path in (
            EBUILD_V1,
            EBUILD_R1,
            INITD_V1,
            CONFD_V1,
            INITD_R1,
            CONFD_R1,
            LOGROTATE,
            METADATA,
        ):
            with self.subTest(path=path):
                self.assertTrue(path.is_file())

    def test_v1_ebuild_matches_committed_content(self):
        self.assertEqual(
            normalize_newlines(EBUILD_V1.read_text()),
            normalize_newlines(EXPECTED_EBUILD_V1),
        )

    def test_r1_ebuild_matches_canonical_content(self):
        self.assertTrue(EBUILD_R1.is_file())
        if EBUILD_R1.is_file():
            self.assertEqual(
                normalize_newlines(EBUILD_R1.read_text()),
                normalize_newlines(EXPECTED_EBUILD_R1),
            )

    def test_v1_auxiliaries_match_committed_content(self):
        self.assertEqual(
            normalize_newlines(INITD_V1.read_text()),
            normalize_newlines(EXPECTED_INITD_V1),
        )
        self.assertEqual(
            normalize_newlines(CONFD_V1.read_text()),
            normalize_newlines(EXPECTED_CONFD_V1),
        )

    def test_r1_auxiliaries_match_canonical_content(self):
        self.assertTrue(INITD_R1.is_file())
        self.assertTrue(CONFD_R1.is_file())
        if not INITD_R1.is_file() or not CONFD_R1.is_file():
            return
        self.assertEqual(
            normalize_newlines(INITD_R1.read_text()),
            normalize_newlines(EXPECTED_INITD_R1),
        )
        self.assertEqual(
            normalize_newlines(CONFD_R1.read_text()),
            normalize_newlines(EXPECTED_CONFD_R1),
        )

    def test_logrotate_matches_canonical_content(self):
        self.assertEqual(
            normalize_newlines(LOGROTATE.read_text()),
            normalize_newlines(EXPECTED_LOGROTATE),
        )

    def test_metadata_matches_canonical_content(self):
        self.assertEqual(
            normalize_newlines(METADATA.read_text()),
            normalize_newlines(EXPECTED_METADATA),
        )

    def test_config_contains_only_the_token_file_path(self):
        text = CONFD_R1.read_text()
        self.assertNotIn('TUNNEL_TOKEN="', text)
        self.assertNotIn("eyJ", text)

    def test_source_config_mode_and_installed_mode(self):
        self.assertEqual(stat.S_IMODE(CONFD_V1.stat().st_mode), 0o644)
        self.assertEqual(stat.S_IMODE(CONFD_R1.stat().st_mode), 0o644)
        self.assertTrue(EBUILD_R1.is_file())
        if not EBUILD_R1.is_file():
            return
        ebuild = EBUILD_R1.read_text()
        self.assertIn("fperms 0644 /etc/conf.d/cloudflared", ebuild)
        self.assertIn("fowners root:root /etc/cloudflared/token", ebuild)
        self.assertIn("fperms 0600 /etc/cloudflared/token", ebuild)

    def test_init_uses_safe_default_without_required_files(self):
        text = INITD_R1.read_text()
        self.assertIn(': "${TUNNEL_TOKEN_FILE:=/etc/cloudflared/token}"', text)
        self.assertNotIn("required_files=", text)

    def test_start_pre_checks_token_file_in_security_order(self):
        text = INITD_R1.read_text()
        checks = (
            "unset TUNNEL_TOKEN",
            'case "${TUNNEL_TOKEN_FILE}" in',
            "*[!A-Za-z0-9_./-]*)",
            'if [ ! -f "${TUNNEL_TOKEN_FILE}" ]; then',
            "token_owner=$(stat -c '%u:%g' -- \"${TUNNEL_TOKEN_FILE}\")",
            'if [ "${token_owner}" != "0:0" ]; then',
            "token_mode=$(stat -c '%a' -- \"${TUNNEL_TOKEN_FILE}\")",
            'if [ "${token_mode}" != "600" ]; then',
            "if ! grep -q '[^[:space:]]' -- \"${TUNNEL_TOKEN_FILE}\"; then",
            'command_args="tunnel --no-autoupdate run --token-file ${TUNNEL_TOKEN_FILE}"',
        )
        for check in checks:
            self.assertIn(check, text)
        positions = [text.index(check) for check in checks]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn('cat "${TUNNEL_TOKEN_FILE}"', text)

    def test_r1_unsets_exported_legacy_token(self):
        with tempfile.TemporaryDirectory(prefix="cloudflared-openrc-") as root:
            token_file = Path(root) / "custom-token"
            token_file.write_text("validator-placeholder\n")
            token_file.chmod(0o600)
            result = subprocess.run(
                [
                    "bash",
                    "-c",
                    """
set -e
eerror() { printf '%s\n' "$*" >&2; }
stat() {
  if [ "$1" = -c ] && [ "$2" = %u:%g ]; then
    printf '0:0\n'
  else
    command stat "$@"
  fi
}
export TUNNEL_TOKEN=legacy-placeholder
TUNNEL_TOKEN_FILE=$2
source "$1"
start_pre
test -z "${TUNNEL_TOKEN+x}"
test "${command_args}" = "tunnel --no-autoupdate run --token-file ${TUNNEL_TOKEN_FILE}"
""",
                    "bash",
                    str(INITD_R1),
                    str(token_file),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("legacy-placeholder", result.stdout + result.stderr)

    def test_r1_rejects_unsafe_token_paths(self):
        unsafe_paths = (
            "relative/token",
            "/tmp/cloudflared token",
            "/tmp/cloudflared;touch-token",
        )
        for token_path in unsafe_paths:
            with self.subTest(token_path=token_path):
                result = subprocess.run(
                    [
                        "bash",
                        "-c",
                        """
set -e
eerror() { printf '%s\n' "$*" >&2; }
TUNNEL_TOKEN_FILE=$2
source "$1"
if start_pre; then
  exit 10
fi
test -z "${command_args+x}"
""",
                        "bash",
                        str(INITD_R1),
                        token_path,
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertRegex(
                    result.stderr,
                    r"path (must be absolute|contains unsafe characters)",
                )
                self.assertNotIn(token_path, result.stderr)

    def test_r1_accepts_safe_custom_absolute_token_path(self):
        with tempfile.TemporaryDirectory(prefix="cloudflared-openrc-") as root:
            token_file = Path(root) / "custom_token-1.token"
            token_file.write_text("validator-placeholder\n")
            token_file.chmod(0o600)
            result = subprocess.run(
                [
                    "bash",
                    "-c",
                    """
set -e
eerror() { printf '%s\n' "$*" >&2; }
stat() {
  if [ "$1" = -c ] && [ "$2" = %u:%g ]; then
    printf '0:0\n'
  else
    command stat "$@"
  fi
}
TUNNEL_TOKEN_FILE=$2
source "$1"
test -z "${command_args+x}"
start_pre
test "${command_args}" = "tunnel --no-autoupdate run --token-file ${TUNNEL_TOKEN_FILE}"
""",
                    "bash",
                    str(INITD_R1),
                    str(token_file),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_r1_postinst_warns_without_printing_legacy_token(self):
        self.assertTrue(EBUILD_R1.is_file())
        if not EBUILD_R1.is_file():
            return

        with tempfile.TemporaryDirectory() as root:
            confd = Path(root) / "etc" / "conf.d"
            confd.mkdir(parents=True)
            (confd / "cloudflared").write_text(
                'export TUNNEL_TOKEN="migration-placeholder"\n'
            )
            result = subprocess.run(
                [
                    "bash",
                    "-c",
                    """
ewarn() { printf 'warning:%s\\n' "$*"; }
elog() { :; }
source "$1"
pkg_postinst
""",
                    "bash",
                    str(EBUILD_R1),
                ],
                env={
                    **os.environ,
                    "EROOT": root,
                    "WORKDIR": f"{root}/work",
                },
                check=True,
                capture_output=True,
                text=True,
            )

        self.assertIn("Legacy TUNNEL_TOKEN assignment detected", result.stdout)
        self.assertIn("root:root and mode to 0600", result.stdout)
        self.assertIn("Remove the legacy TUNNEL_TOKEN assignment", result.stdout)
        self.assertIn("not copied or printed automatically", result.stdout)
        self.assertNotIn("migration-placeholder", result.stdout)

    def test_versions_use_separate_auxiliaries(self):
        v1_ebuild = EBUILD_V1.read_text()
        r1_ebuild = EBUILD_R1.read_text()
        self.assertIn('newinitd "${FILESDIR}/cloudflared.initd" cloudflared', v1_ebuild)
        self.assertIn('newconfd "${FILESDIR}/cloudflared.confd" cloudflared', v1_ebuild)
        self.assertNotIn("token-file", INITD_V1.read_text())
        self.assertNotIn("TUNNEL_TOKEN_FILE", CONFD_V1.read_text())
        self.assertIn(
            'newinitd "${FILESDIR}/cloudflared-r1.initd" cloudflared', r1_ebuild
        )
        self.assertIn(
            'newconfd "${FILESDIR}/cloudflared-r1.confd" cloudflared', r1_ebuild
        )
        self.assertIn("--token-file", INITD_R1.read_text())
        self.assertIn("TUNNEL_TOKEN_FILE", CONFD_R1.read_text())

    def test_init_script_source_modes(self):
        self.assertEqual(stat.S_IMODE(INITD_V1.stat().st_mode), 0o644)
        self.assertEqual(stat.S_IMODE(INITD_R1.stat().st_mode), 0o644)

    def test_gentoo_validator_exists_and_is_executable(self):
        self.assertTrue(GENTOO_VALIDATOR.is_file())
        self.assertEqual(stat.S_IMODE(GENTOO_VALIDATOR.stat().st_mode), 0o755)

    def test_upgrade_validator_exists_and_is_executable(self):
        self.assertTrue(UPGRADE_VALIDATOR.is_file())
        if not UPGRADE_VALIDATOR.is_file():
            return

        self.assertEqual(stat.S_IMODE(UPGRADE_VALIDATOR.stat().st_mode), 0o755)
        text = UPGRADE_VALIDATOR.read_text()
        self.assertIn('test "$#" -eq 0', text)
        self.assertIn('test "${upgrade_root}" != /', text)
        self.assertIn('realpath -e -- "${upgrade_root}"', text)
        self.assertIn('case "${upgrade_root}" in', text)
        self.assertIn('ROOT="${upgrade_root}" ebuild', text)
        self.assertIn("! grep -Fq 'upgrade-placeholder' <<<", text)

    def test_readme_documents_secure_legacy_credential_removal(self):
        text = (ROOT / "README.md").read_text()
        self.assertIn("sudo grep -qE", text)
        self.assertIn("(export[[:space:]]+)?TUNNEL_TOKEN", text)
        self.assertIn("sudo rm -f -- /etc/conf.d/cloudflared", text)
        self.assertIn("sudo rm -f -- /etc/cloudflared/token", text)
        self.assertIn("do not print either token", text)
        self.assertIn("rotate or revoke", text)
        self.assertNotIn("cat /etc/conf.d/cloudflared", text)

    def test_gentoo_validator_matches_canonical_content(self):
        self.assertEqual(
            normalize_newlines(GENTOO_VALIDATOR.read_text()),
            normalize_newlines(EXPECTED_GENTOO_VALIDATOR),
        )

    def test_readme_documents_cloudflared_openrc(self):
        text = normalize_newlines((ROOT / "README.md").read_text())
        for expected in (
            EXPECTED_README_INTRO,
            EXPECTED_README_SECTION,
            EXPECTED_README_UPDATE,
            EXPECTED_README_REMOVAL,
        ):
            with self.subTest(expected=expected):
                self.assertIn(normalize_newlines(expected), text)


if __name__ == "__main__":
    unittest.main()
