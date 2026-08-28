# Copyright 2026 Andrej Kouril
# Distributed under the terms of the GNU General Public License v2

EAPI=8

CRATES="
	aho-corasick@1.1.4
	anstream@0.6.21
	anstyle@1.0.13
	anstyle-parse@0.2.7
	anstyle-query@1.1.5
	anstyle-wincon@3.0.11
	anyhow@1.0.100
	ashpd@0.12.1
	async-broadcast@0.7.2
	async-recursion@1.1.1
	async-trait@0.1.89
	autocfg@1.5.0
	bitflags@2.10.0
	bumpalo@3.19.1
	bytes@1.11.0
	calloop@0.14.3
	cfg-if@1.0.4
	clap@4.5.54
	clap_builder@4.5.54
	clap_derive@4.5.49
	clap_lex@0.7.6
	colorchoice@1.0.4
	concurrent-queue@2.5.0
	crossbeam-utils@0.8.21
	displaydoc@0.2.5
	endi@1.1.1
	enumflags2@0.7.12
	enumflags2_derive@0.7.12
	env_filter@0.1.4
	env_logger@0.11.8
	equivalent@1.0.2
	errno@0.3.14
	event-listener@5.4.1
	event-listener-strategy@0.5.4
	fastrand@2.3.0
	form_urlencoded@1.2.2
	futures-channel@0.3.31
	futures-core@0.3.31
	futures-io@0.3.31
	futures-lite@2.6.1
	futures-macro@0.3.31
	futures-task@0.3.31
	futures-util@0.3.31
	getrandom@0.3.4
	hashbrown@0.16.1
	heck@0.5.0
	hermit-abi@0.5.2
	hex@0.4.3
	icu_collections@2.1.1
	icu_locale_core@2.1.1
	icu_normalizer@2.1.1
	icu_normalizer_data@2.1.1
	icu_properties@2.1.2
	icu_properties_data@2.1.2
	icu_provider@2.1.1
	idna@1.1.0
	idna_adapter@1.2.1
	indexmap@2.13.0
	indoc@2.0.7
	is_terminal_polyfill@1.70.2
	jiff@0.2.18
	jiff-static@0.2.18
	js-sys@0.3.83
	libc@0.2.180
	linux-raw-sys@0.4.15
	linux-raw-sys@0.11.0
	litemap@0.8.1
	log@0.4.29
	memchr@2.7.6
	memmap2@0.9.9
	memoffset@0.9.1
	mio@1.1.1
	once_cell@1.21.3
	once_cell_polyfill@1.70.2
	ordered-stream@0.2.0
	parking@2.2.1
	percent-encoding@2.3.2
	pin-project-lite@0.2.16
	pin-utils@0.1.0
	pkg-config@0.3.32
	polling@3.11.0
	portable-atomic@1.13.0
	portable-atomic-util@0.2.4
	potential_utf@0.1.4
	ppv-lite86@0.2.21
	proc-macro-crate@3.4.0
	proc-macro2@1.0.105
	pyo3@0.27.2
	pyo3-build-config@0.27.2
	pyo3-ffi@0.27.2
	pyo3-macros@0.27.2
	pyo3-macros-backend@0.27.2
	quote@1.0.43
	r-efi@5.3.0
	rand@0.9.2
	rand_chacha@0.9.0
	rand_core@0.9.3
	regex@1.12.2
	regex-automata@0.4.13
	regex-syntax@0.8.8
	reis@0.5.0
	rustix@0.38.44
	rustix@1.1.3
	rustversion@1.0.22
	serde@1.0.228
	serde_core@1.0.228
	serde_derive@1.0.228
	serde_repr@0.1.20
	signal-hook-registry@1.4.8
	slab@0.4.11
	smallvec@1.15.1
	socket2@0.6.1
	stable_deref_trait@1.2.1
	strsim@0.11.1
	syn@2.0.114
	synstructure@0.13.2
	target-lexicon@0.13.4
	tempfile@3.24.0
	thiserror@2.0.17
	thiserror-impl@2.0.17
	tinystr@0.8.2
	tokio@1.49.0
	toml_datetime@0.7.5+spec-1.1.0
	toml_edit@0.23.10+spec-1.0.0
	toml_parser@1.0.6+spec-1.1.0
	tracing@0.1.44
	tracing-attributes@0.1.31
	tracing-core@0.1.36
	uds_windows@1.1.0
	unicode-ident@1.0.22
	unindent@0.2.4
	url@2.5.8
	utf8_iter@1.0.4
	utf8parse@0.2.2
	uuid@1.19.0
	wasi@0.11.1+wasi-snapshot-preview1
	wasip2@1.0.1+wasi-0.2.4
	wasm-bindgen@0.2.106
	wasm-bindgen-macro@0.2.106
	wasm-bindgen-macro-support@0.2.106
	wasm-bindgen-shared@0.2.106
	winapi@0.3.9
	winapi-i686-pc-windows-gnu@0.4.0
	winapi-x86_64-pc-windows-gnu@0.4.0
	windows-link@0.2.1
	windows-sys@0.59.0
	windows-sys@0.60.2
	windows-sys@0.61.2
	windows-targets@0.52.6
	windows-targets@0.53.5
	windows_aarch64_gnullvm@0.52.6
	windows_aarch64_gnullvm@0.53.1
	windows_aarch64_msvc@0.52.6
	windows_aarch64_msvc@0.53.1
	windows_i686_gnu@0.52.6
	windows_i686_gnu@0.53.1
	windows_i686_gnullvm@0.52.6
	windows_i686_gnullvm@0.53.1
	windows_i686_msvc@0.52.6
	windows_i686_msvc@0.53.1
	windows_x86_64_gnu@0.52.6
	windows_x86_64_gnu@0.53.1
	windows_x86_64_gnullvm@0.52.6
	windows_x86_64_gnullvm@0.53.1
	windows_x86_64_msvc@0.52.6
	windows_x86_64_msvc@0.53.1
	winnow@0.7.14
	wit-bindgen@0.46.0
	writeable@0.6.2
	xkbcommon@0.9.0
	xkeysym@0.2.1
	yoke@0.8.1
	yoke-derive@0.8.1
	zbus@5.13.1
	zbus_macros@5.13.1
	zbus_names@4.3.1
	zerocopy@0.8.33
	zerocopy-derive@0.8.33
	zerofrom@0.1.6
	zerofrom-derive@0.1.6
	zerotrie@0.2.3
	zerovec@0.11.5
	zerovec-derive@0.11.2
	zvariant@5.9.1
	zvariant_derive@5.9.1
	zvariant_utils@3.3.0
"

inherit cargo

DESCRIPTION="CLI tool for typing text with Wayland Emulated Input"
HOMEPAGE="https://github.com/Adam-D-Lewis/eitype"
SRC_URI="
	https://github.com/Adam-D-Lewis/eitype/archive/refs/tags/${PV}.tar.gz -> ${P}.tar.gz
	${CARGO_CRATE_URIS}
"

LICENSE="
	Apache-2.0
	MIT
	Unicode-3.0
	Apache-2.0-with-LLVM-exceptions
	|| ( MIT Unlicense )
	|| ( MIT Apache-2.0 )
	|| ( MIT Apache-2.0 LGPL-2.1+ )
	|| ( MIT Apache-2.0 ZLIB )
	|| ( BSD-2 MIT Apache-2.0 )
	|| ( Apache-2.0-with-LLVM-exceptions Apache-2.0 MIT )
"
SLOT="0"
KEYWORDS="~amd64"

BDEPEND="virtual/pkgconfig"
DEPEND="x11-libs/libxkbcommon"
RDEPEND="${DEPEND}"

src_configure() {
	cargo_src_configure --bin eitype
}

src_install() {
	cargo_src_install
	dodoc README.md LICENSE
}
