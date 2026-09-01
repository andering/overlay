#!/usr/bin/env bash

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
printf '%s\n' 'export TUNNEL_TOKEN="migration-placeholder"' >"${migration_root}/etc/conf.d/cloudflared"

unset TUNNEL_TOKEN TUNNEL_TOKEN_FILE command_args
. "${migration_root}/etc/conf.d/cloudflared"
. "${r1_initd}"
test "${TUNNEL_TOKEN_FILE}" = /etc/cloudflared/token
test -z "${command_args+x}"
TUNNEL_TOKEN_FILE="${r1_token_file}"
restore_token_file
printf '%s\n' 'validator-placeholder' >"${r1_token_file}"
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
printf ' \t\n' >"${r1_token_file}"
expect_start_pre_failure "Cloudflare Tunnel token file is empty or whitespace-only: ${TUNNEL_TOKEN_FILE}"

restore_token_file
printf '%s\n' 'validator-placeholder' >"${r1_token_file}"
start_pre
test "${command_args}" = "tunnel --no-autoupdate run --token-file ${r1_token_file}"

migration_output=$(
	EROOT="${migration_root}" WORKDIR="${migration_root}/work" bash -c '
		ewarn() { printf "warning:%s\n" "$*"; }
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

printf '%s\n' "cloudflared-openrc Gentoo validation passed for 1 and 1-r1"
