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

EXPECTED_EBUILD = """# Copyright 2026 Andrej Kouril
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

EXPECTED_INITD = """#!/sbin/openrc-run

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

EXPECTED_CONFD = """# Token for one remotely managed Cloudflare Tunnel.
# Keep this file root-readable only and do not pass the token on the command line.
TUNNEL_TOKEN=""
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
    Tunnel connector with a protected environment token and process
    supervision.
  </longdescription>
</pkgmetadata>
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

Service output is written to `/var/log/cloudflared.log`, and errors are written
to `/var/log/cloudflared.err`. Invalid or revoked token failures retry every
five seconds without a retry limit, and each failure repeats in the error log.
An empty token is rejected before `cloudflared` launches, and its message
appears in `rc-service` output.
"""

EXPECTED_README_UPDATE = """sudo emerge --update --deep --ask net-vpn/cloudflared-openrc
```

Using `--deep` includes the `net-vpn/cloudflared` dependency, whose self-update
is disabled by this service."""

EXPECTED_README_REMOVAL = """sudo rc-service cloudflared stop
sudo rc-update del cloudflared default
sudo emerge --ask --unmerge net-vpn/cloudflared-openrc
```

A modified `/etc/conf.d/cloudflared` may remain after unmerging the package. If
decommissioning the service, securely remove that token-bearing file and,
optionally, `/var/log/cloudflared.log` and `/var/log/cloudflared.err`. Then rotate
the tunnel token in Cloudflare. If the tunnel is no longer needed, delete it and
remove its obsolete public hostname or DNS CNAME to avoid stale DNS and
Cloudflare error 1016."""


def normalize_newlines(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text[:-1] if text.endswith("\n") else text


class CloudflaredOpenRCTest(unittest.TestCase):
    def test_package_files_exist(self):
        for path in (EBUILD, INITD, CONFD, LOGROTATE, METADATA):
            with self.subTest(path=path):
                self.assertTrue(path.is_file())

    def test_ebuild_matches_canonical_content(self):
        self.assertEqual(
            normalize_newlines(EBUILD.read_text()), normalize_newlines(EXPECTED_EBUILD)
        )

    def test_init_script_matches_canonical_content(self):
        self.assertEqual(
            normalize_newlines(INITD.read_text()), normalize_newlines(EXPECTED_INITD)
        )

    def test_config_matches_canonical_content(self):
        self.assertEqual(
            normalize_newlines(CONFD.read_text()), normalize_newlines(EXPECTED_CONFD)
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

    def test_config_contains_no_token_prefix(self):
        self.assertNotIn("eyJ", CONFD.read_text())

    def test_source_config_mode_and_installed_mode(self):
        mode = stat.S_IMODE(CONFD.stat().st_mode)
        self.assertIn(mode, (0o600, 0o644))
        self.assertIn("fperms 0600 /etc/conf.d/cloudflared", EBUILD.read_text())

    def test_init_script_source_mode(self):
        self.assertEqual(stat.S_IMODE(INITD.stat().st_mode), 0o644)

    def test_gentoo_validator_exists_and_is_executable(self):
        self.assertTrue(GENTOO_VALIDATOR.is_file())
        self.assertEqual(stat.S_IMODE(GENTOO_VALIDATOR.stat().st_mode), 0o755)

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
