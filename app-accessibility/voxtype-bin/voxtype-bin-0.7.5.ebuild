# Copyright 2026 Andrej Kouril
# Distributed under the terms of the GNU General Public License v2

EAPI=8

inherit desktop

DESCRIPTION="Push-to-talk voice-to-text for Wayland Linux systems"
HOMEPAGE="https://voxtype.io https://github.com/peteonrails/voxtype"
SRC_URI="
	https://github.com/peteonrails/voxtype/archive/refs/tags/v${PV}.tar.gz -> ${P}.tar.gz
	!vulkan? (
		https://github.com/peteonrails/voxtype/releases/download/v${PV}/voxtype-${PV}-linux-x86_64-avx2
		-> ${PN}-${PV}-linux-x86_64-avx2
	)
	vulkan? (
		https://github.com/peteonrails/voxtype/releases/download/v${PV}/voxtype-${PV}-linux-x86_64-vulkan
		-> ${PN}-${PV}-linux-x86_64-vulkan
	)
"

S="${WORKDIR}/voxtype-${PV}"

LICENSE="MIT"
SLOT="0"
KEYWORDS="~amd64"
IUSE="autostart vulkan"
RESTRICT="mirror"
QA_PRESTRIPPED="usr/bin/voxtype"

RDEPEND="
	media-libs/alsa-lib
	media-video/pipewire[pipewire-alsa]
	net-misc/curl
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
