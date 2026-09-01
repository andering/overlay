#!/usr/bin/env bash

set -euo pipefail

test "$#" -eq 0 || {
	printf '%s\n' 'usage: validate_cloudflared_openrc_upgrade_gentoo.sh' >&2
	exit 2
}

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo_root=$(cd -- "${script_dir}/.." && pwd)
package_dir="${repo_root}/net-vpn/cloudflared-openrc"
r1_initd_source="${package_dir}/files/cloudflared-r1.initd"
r1_confd_source="${package_dir}/files/cloudflared-r1.confd"

upgrade_parent=$(mktemp -d "${PORTAGE_TMPDIR:-/var/tmp}/cloudflared-openrc-upgrade.XXXXXX")
cleanup() {
	rm -rf -- "${upgrade_parent}"
}
trap cleanup EXIT

upgrade_parent=$(realpath -e -- "${upgrade_parent}")
test "${upgrade_parent}" != /
upgrade_root="${upgrade_parent}/root"
mkdir -m 700 -- "${upgrade_root}"
upgrade_root=$(realpath -e -- "${upgrade_root}")
test "${upgrade_root}" != /
test "$(dirname -- "${upgrade_root}")" = "${upgrade_parent}"
case "${upgrade_root}" in
	"${upgrade_parent}"/*) ;;
	*)
		printf '%s\n' 'upgrade root escaped its generated parent' >&2
		exit 1
		;;
esac
test -z "$(ls -A -- "${upgrade_root}")"

cd "${package_dir}"

ROOT="${upgrade_root}" ebuild cloudflared-openrc-1.ebuild clean merge

legacy_confd="${upgrade_root}/etc/conf.d/cloudflared"
legacy_expected="${upgrade_parent}/legacy.confd"
test -f "${legacy_confd}"
printf '%s\n' 'export TUNNEL_TOKEN="upgrade-placeholder"' >"${legacy_expected}"
install -o 0 -g 0 -m 600 "${legacy_expected}" "${legacy_confd}"

if ! r1_output=$(ROOT="${upgrade_root}" ebuild cloudflared-openrc-1-r1.ebuild clean merge 2>&1); then
	printf '%s\n' "${r1_output}" >&2
	exit 1
fi

cmp -s "${legacy_expected}" "${legacy_confd}"
test "$(stat -c '%a' "${legacy_confd}")" = 600

shopt -s nullglob
protected_confd=("${upgrade_root}/etc/conf.d/._cfg"[0-9][0-9][0-9][0-9]_cloudflared)
test "${#protected_confd[@]}" = 1
cmp -s "${r1_confd_source}" "${protected_confd[0]}"

installed_initd="${upgrade_root}/etc/init.d/cloudflared"
token_file="${upgrade_root}/etc/cloudflared/token"
cmp -s "${r1_initd_source}" "${installed_initd}"
test -f "${token_file}"
test "$(stat -c '%u:%g' "${token_file}")" = 0:0
test "$(stat -c '%a' "${token_file}")" = 600
test ! -s "${token_file}"

unset TUNNEL_TOKEN TUNNEL_TOKEN_FILE command_args
. "${legacy_confd}"
. "${installed_initd}"
test "${TUNNEL_TOKEN_FILE}" = /etc/cloudflared/token
test -z "${command_args+x}"

TUNNEL_TOKEN_FILE="${token_file}"
printf '%s\n' 'validator-placeholder' >"${token_file}"
eerror() {
	validation_error=$*
}
validation_error=
start_pre
test -z "${validation_error}"
test -z "${TUNNEL_TOKEN+x}"
test "${command_args}" = "tunnel --no-autoupdate run --token-file ${token_file}"

grep -Fq "Legacy TUNNEL_TOKEN assignment detected in ${legacy_confd}." <<<"${r1_output}"
grep -Fq "Manually move only its token value into ${token_file}." <<<"${r1_output}"
grep -Fq 'The token was not copied or printed automatically.' <<<"${r1_output}"
! grep -Fq 'upgrade-placeholder' <<<"${r1_output}"

printf '%s\n' 'cloudflared-openrc isolated CONFIG_PROTECT upgrade validation passed'
