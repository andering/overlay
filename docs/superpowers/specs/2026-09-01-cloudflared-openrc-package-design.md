# Cloudflared OpenRC Package Design

## Goal

Add a reusable Gentoo companion package that runs the official
`net-vpn/cloudflared` binary as a supervised OpenRC service for remotely
managed Cloudflare Tunnels.

The package is generic. It must not contain configuration specific to a
machine hostname or domain, a Cloudflare account, a tunnel UUID, or a tunnel
token.

## Package Boundary

Create `net-vpn/cloudflared-openrc` in the `andering/overlay` repository. The
package depends on Gentoo's existing `net-vpn/cloudflared`; it does not build,
bundle, revise, or override the upstream binary package.

Revision `1-r1` installs only:

- `/etc/init.d/cloudflared`, the OpenRC service definition.
- `/etc/conf.d/cloudflared`, the non-secret token-file path configuration.
- `/etc/cloudflared/token`, the empty administrator-owned token file.
- `/etc/logrotate.d/cloudflared`, bounded rotation for the service logs.
- Gentoo package metadata and user-facing overlay documentation.

The package supports one remotely managed tunnel connector per host. Multiple
service instances, locally managed tunnel credentials, automatic Cloudflare
provisioning, and systemd integration are outside this version's scope.
The original `cloudflared-openrc-1.ebuild` remains available unchanged; the
token-file hardening is shipped as `cloudflared-openrc-1-r1.ebuild`. Version
`1` continues to install `files/cloudflared.initd` and
`files/cloudflared.confd`, both preserved byte-for-byte from the original
package. Revision `1-r1` installs `files/cloudflared-r1.initd` and
`files/cloudflared-r1.confd` to the same destination names. The logrotate file
is unchanged and remains shared. This source split preserves the effective v1
payload rather than preserving only its ebuild text.

Repository-only Gentoo integration validation lives in
`tests/validate_cloudflared_openrc_gentoo.sh`. The executable script derives the
repository and package paths from its own location and uses `PORTAGE_TMPDIR`
when locating the staged Portage image, so it does not depend on one checkout
or build-host path. A separate
`tests/validate_cloudflared_openrc_upgrade_gentoo.sh` performs real v1-to-r1
Portage merges under a generated temporary `ROOT`. It accepts no caller-supplied
target, rejects `/`, verifies its canonical root is an empty child of its own
temporary parent, and never merges into the operator's live root. The main
Gentoo validator invokes this isolated upgrade validator after both staged
builds pass.

## OpenRC Service

The service runs:

```text
/usr/bin/cloudflared tunnel --no-autoupdate run --token-file /etc/cloudflared/token
```

It reads `TUNNEL_TOKEN_FILE` from `/etc/conf.d/cloudflared` and passes that path
to `cloudflared` with `--token-file`. Process command-line inspection exposes
only `/etc/cloudflared/token`; the token value is not exported to the daemon
environment or included in process arguments. The init script defaults an
unset `TUNNEL_TOKEN_FILE` to `/etc/cloudflared/token`, so a preserved legacy
configuration cannot leave the command path empty. Before daemon launch,
`start_pre` unsets any inherited or legacy exported `TUNNEL_TOKEN`, requires an
absolute token path containing only characters from `[A-Za-z0-9_./-]`, and
constructs `command_args` only after the path and token file pass every check.
This prevents OpenRC's command-argument evaluation from interpreting spaces or
shell metacharacters supplied through configuration.

The init script uses OpenRC's `supervise-daemon`, keeps `cloudflared` in the
foreground, writes standard output to `/var/log/cloudflared.log` and standard
error to `/var/log/cloudflared.err`, waits five seconds before respawning an
unexpectedly terminated process, sets `respawn_max=0` for unlimited supervised
recovery, and declares a dependency on networking. `start_pre` owns all token
file validation; `required_files` is not used because it would bypass the
custom diagnostics.

Logrotate rotates both service logs weekly, retains four rotations, compresses
old logs after one cycle, and uses `copytruncate` so `cloudflared` can continue
writing through the file descriptors held by `supervise-daemon`.

The package does not add the service to an OpenRC runlevel and does not start
or restart it during installation or upgrade. After configuring a token, the
administrator explicitly runs:

```sh
rc-update add cloudflared default
rc-service cloudflared start
```

## Secret Handling

The installed `/etc/conf.d/cloudflared` contains only the
`TUNNEL_TOKEN_FILE="/etc/cloudflared/token"` path setting and comments, never a
real token. It is installed with mode `0644`. The ebuild creates an empty
`/etc/cloudflared/token`, owned by root with mode `0600`; administrators place
only the token value in that file.

The file lives under `/etc`, so Portage configuration protection preserves
administrator changes across package upgrades. Package documentation warns
against supplying the token as a command-line option, storing it in source
control, or placing it in shell history.

The service runs with the privileges OpenRC uses by default. Creating a
dedicated system account is outside this initial package because Gentoo does
not currently provide an `acct-user/cloudflared` package and the companion
package should remain narrowly scoped.

## Ebuild And Metadata

The package uses EAPI 8, slot `0`, and architecture keywords compatible with
the official binary package (`~amd64` and `~arm64`). It has no source archive;
the ebuild installs overlay-owned files from `FILESDIR`.

The source init scripts `files/cloudflared.initd` and
`files/cloudflared-r1.initd` are stored with mode `0644`, avoiding the
unnecessary executable-bit finding from `pkgcheck`. Each ebuild's `newinitd`
helper installs its version-specific source as `/etc/init.d/cloudflared` with
mode `0755`.

The repository uses `thin-manifests = true`. Because this package has no
distfiles, `pkgdev manifest` is a verification step and does not create a
`Manifest` file.

Both versions depend on `app-admin/logrotate` and `sys-apps/openrc`. Version `1`
retains its original unversioned `net-vpn/cloudflared` dependency. Revision
`1-r1` requires `>=net-vpn/cloudflared-2025.4.0`, the minimum supported binary
for its `--token-file` invocation.

The version floor is part of migration safety. An upgrade from version `1` to
`1-r1` changes both credential storage and the `cloudflared` command-line
interface; the dependency ensures Portage installs a compatible binary before
the hardened service is started. Keeping version `1` unversioned preserves its
original dependency contract and reproducible payload.

`pkg_postinst` prints the required next actions: edit the root-only token file,
enable the service manually, and start it. On an upgrade from version `1`, it
also detects an active legacy `TUNNEL_TOKEN=` or `export TUNNEL_TOKEN=`
assignment in the preserved configuration and warns the administrator to move
only the value into the token file, set root ownership and mode `0600`, and
remove the assignment. It never copies or prints the token automatically. The
README documents installation, migration, status checks, and removal without
embedding machine-specific values. Removal instructions use a quiet match to
detect a legacy assignment without displaying it, remove both legacy and
token-file credential storage, and require token rotation or revocation because
filesystem deletion alone is not guaranteed secure erasure.

## Failure Behavior

- Missing or non-regular token file, ownership other than UID:GID `0:0`, mode
  other than `0600`, or empty/whitespace-only content: `start_pre` stops before
  launching `cloudflared` and reports only the configured token-file path.
- A relative token path, whitespace, or any character outside
  `[A-Za-z0-9_./-]`: `start_pre` stops before file access or command-argument
  construction and reports only that the configured path is unsafe.
- A legacy exported `TUNNEL_TOKEN`: `start_pre` removes it from the service
  environment before any successful daemon launch while `pkg_postinst` still
  detects the assignment for migration guidance.
- Invalid or revoked token: `cloudflared` exits and OpenRC supervises unlimited
  retries with a five-second delay; `/var/log/cloudflared.log` and
  `/var/log/cloudflared.err` preserve service output and errors while process
  arguments expose only the token-file path.
- Temporary network loss: `cloudflared` handles reconnection; if it exits,
  `supervise-daemon` restarts it.
- Package removal: Portage removes package-owned service files according to
  normal configuration-protection behavior and does not delete Cloudflare-side
  tunnels or DNS records.

## Validation

1. In a Gentoo environment with `pkgdev`, `pkgcheck`, and `ebuild`, run
   `tests/validate_cloudflared_openrc_gentoo.sh`. Confirm `pkgdev manifest`
   reports `manifest not needed, thin manifests and no distfiles`, no
   `Manifest` file is created, strict version-level
   `pkgcheck scan --exit=error,warning,style,info cloudflared-openrc-1-r1.ebuild`
   reports no findings, and both package versions build into their distinct
   Portage image roots. For version `1`, the validator compares the installed
   init, conf, and logrotate files to the legacy sources, checks modes `0755`,
   `0600`, and `0644`, confirms no token file exists, and exercises the original
   environment-token startup behavior. It then independently builds revision
   `1-r1` and runs all hardened staged-file, token-file, startup, and migration
   checks. The script prints
   `cloudflared-openrc Gentoo validation passed for 1 and 1-r1` only after both
   versions pass.
2. Run `python3 -m unittest -v tests/test_cloudflared_openrc.py`, then run
   `bash -n` for `files/cloudflared.initd`, `files/cloudflared-r1.initd`,
   `files/cloudflared-r1.confd`, and the Gentoo validation script. The contract
   tests compare both v1 auxiliaries to their original canonical bytes and both
   r1 auxiliaries to their hardened canonical bytes.
3. Confirm `start_pre` rejects, in order, a missing or non-regular token file,
   wrong numeric ownership, wrong mode, and empty or whitespace-only content,
   then accepts a root-owned mode-`0600` file containing a non-secret value.
4. Use a non-secret test token or controlled test tunnel to confirm argv
   includes `--token-file /etc/cloudflared/token`, not the token value, and the
   daemon environment does not contain `TUNNEL_TOKEN`.
5. Confirm `supervise-daemon` writes to `/var/log/cloudflared.log` and
   `/var/log/cloudflared.err`, and restarts the process without a retry limit
   through `respawn_max=0` after an unexpected exit.
6. Confirm `/etc/logrotate.d/cloudflared` rotates both logs weekly, retains four
   rotations, compresses old logs, and uses `copytruncate`.
7. Confirm the v1 and r1 Portage image roots are distinct so one version cannot
   satisfy checks with stale files from the other.
8. Confirm revision `1-r1` emits migration instructions for an active legacy
   assignment, including an exported assignment, without copying or printing
   its value, and version `1` remains available with its ebuild and effective
   auxiliary payload unchanged.
9. Run `tests/validate_cloudflared_openrc_upgrade_gentoo.sh` only in the Gentoo
   validation environment. Confirm it refuses arguments, generates and guards a
   non-live temporary `ROOT`, merges v1, writes only an exported non-secret
   placeholder, merges r1, and verifies CONFIG_PROTECT preserves the legacy
   configuration while staging the r1 conf update. Confirm the new token file
   is initially empty, root-owned, and mode `0600`; r1 safely defaults the token
   path, removes the exported legacy variable before a valid placeholder launch,
   and emits migration guidance without printing the placeholder.
10. Confirm installation leaves OpenRC runlevels unchanged.

## Deployment

On each target host, install `net-vpn/cloudflared-openrc`, place only that
host's tunnel token in `/etc/cloudflared/token`, then manually enable and start
the service. The package makes no Cloudflare-side changes.
