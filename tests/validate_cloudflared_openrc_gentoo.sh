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
