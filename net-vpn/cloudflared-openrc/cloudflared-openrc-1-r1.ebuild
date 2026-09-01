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
