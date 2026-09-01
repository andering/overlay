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
