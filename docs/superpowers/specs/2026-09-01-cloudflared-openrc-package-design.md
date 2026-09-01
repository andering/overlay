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

Version `1` installs only:

- `/etc/init.d/cloudflared`, the OpenRC service definition.
- `/etc/conf.d/cloudflared`, the administrator-owned secret configuration.
- `/etc/logrotate.d/cloudflared`, bounded rotation for the service logs.
- Gentoo package metadata and user-facing overlay documentation.

The package supports one remotely managed tunnel connector per host. Multiple
service instances, locally managed tunnel credentials, automatic Cloudflare
provisioning, and systemd integration are outside this version's scope.

Repository-only Gentoo integration validation lives in
`tests/validate_cloudflared_openrc_gentoo.sh`. The executable script derives the
repository and package paths from its own location and uses `PORTAGE_TMPDIR`
when locating the staged Portage image, so it does not depend on one checkout
or build-host path.

## OpenRC Service

The service runs:

```text
/usr/bin/cloudflared tunnel --no-autoupdate run
```

It reads `TUNNEL_TOKEN` from `/etc/conf.d/cloudflared` and exports it to the
daemon environment. The token must not be included in `command_args`, which
would expose it through process command-line inspection.

The init script uses OpenRC's `supervise-daemon`, keeps `cloudflared` in the
foreground, writes standard output to `/var/log/cloudflared.log` and standard
error to `/var/log/cloudflared.err`, waits five seconds before respawning an
unexpectedly terminated process, sets `respawn_max=0` for unlimited supervised
recovery, and declares a dependency on networking. Service startup fails with
a clear message when `TUNNEL_TOKEN` is empty.

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

The installed `/etc/conf.d/cloudflared` contains an empty token assignment and
instructions, never a real token. It is owned by root and installed with mode
`0600`.

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

The source `files/cloudflared.initd` is stored with mode `0644`, avoiding the
unnecessary executable-bit finding from `pkgcheck`. The ebuild's `newinitd`
helper installs `/etc/init.d/cloudflared` with mode `0755`.

The repository uses `thin-manifests = true`. Because this package has no
distfiles, `pkgdev manifest` is a verification step and does not create a
`Manifest` file.

Runtime dependencies are:

- `app-admin/logrotate`
- `net-vpn/cloudflared`
- `sys-apps/openrc`

`pkg_postinst` prints only the required next actions: edit the root-only config,
enable the service manually, and start it. The README documents installation,
configuration, status checks, and removal without embedding machine-specific
values.

## Failure Behavior

- Empty token: startup stops before launching `cloudflared` and identifies
  `/etc/conf.d/cloudflared` as the file to edit.
- Invalid or revoked token: `cloudflared` exits and OpenRC supervises unlimited
  retries with a five-second delay; `/var/log/cloudflared.log` and
  `/var/log/cloudflared.err` preserve service output and errors without exposing
  the token in the process command line.
- Temporary network loss: `cloudflared` handles reconnection; if it exits,
  `supervise-daemon` restarts it.
- Package removal: Portage removes package-owned service files according to
  normal configuration-protection behavior and does not delete Cloudflare-side
  tunnels or DNS records.

## Validation

1. In a Gentoo environment with `pkgdev`, `pkgcheck`, and `ebuild`, run
   `tests/validate_cloudflared_openrc_gentoo.sh`. Confirm `pkgdev manifest`
   reports `manifest not needed, thin manifests and no distfiles`, no
   `Manifest` file is created, `pkgcheck scan --exit=error,warning,style,info`
   reports no findings, the temporary image builds, and the script prints
   `cloudflared-openrc Gentoo validation passed`.
2. Run `python3 -m unittest -v tests/test_cloudflared_openrc.py`, then run
   `bash -n` for both `files/cloudflared.initd` and the Gentoo validation script.
3. Confirm service startup fails before process launch when the token is empty.
4. Use a non-secret test token or controlled test tunnel to confirm the token
   is consumed from the environment and absent from the process command line.
5. Confirm `supervise-daemon` writes to `/var/log/cloudflared.log` and
   `/var/log/cloudflared.err`, and restarts the process without a retry limit
   through `respawn_max=0` after an unexpected exit.
6. Confirm `/etc/logrotate.d/cloudflared` rotates both logs weekly, retains four
   rotations, compresses old logs, and uses `copytruncate`.
7. Confirm installation leaves OpenRC runlevels unchanged.

## Deployment

On each target host, install `net-vpn/cloudflared-openrc`, set that host's
tunnel token in `/etc/conf.d/cloudflared`, then manually enable and start the
service. The package makes no Cloudflare-side changes.
