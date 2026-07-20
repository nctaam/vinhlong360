> STATUS: active

# Launch-Safety Closed Rollback

This runbook replaces the single-host release during a maintenance window. It
does not deploy anything by itself, does not authorize a live run, and never
changes the global noindex posture. H1, H2, owner authorization, Stage 3, and a
live SLA remain outside this workstream.

## Provenance prerequisite

The operator must obtain the known-good closed archive and adjacent `.sha256`
file from an independently approved release provenance process before using
this procedure. The SHA-256 sidecar is integrity evidence, not a signature. A
matching sidecar proves only that the archive bytes match the recorded digest;
it does not establish who produced or approved those bytes.

The archive must be the `vl360-launch-release` format produced by
`scripts/package_launch_release.py`. It must declare `launch_posture=closed`,
exclude all `agent/data/**`, `.env`, unlock values, developer overrides, and
contain canonical config, readiness, Nginx, Compose audit, and all five tracked
systemd unit files.

## Required external authorities

The archive deliberately excludes `.env`, virtual environments, dependency
caches, and persistent data. A host execution therefore requires explicit,
pre-provisioned authorities for the environment file, runtime dependencies,
persistent `agent/data`, and detach/remount operations. The command refuses a
live run when any authority is absent. Neither installer nor rehearsal performs
network access or package installation.

Persistent storage includes all of `agent/data`, especially
`agent/data/sitemap-bundles`. The installer hashes every regular file before
detach and after remount. The old open tree is never a recovery source.

## Exact phase order

1. `record-and-verify-evidence`
2. `suspend-watchdog`
3. `enable-maintenance`
4. `stop-vl-nuxt`
5. `purge-runtime-caches`
6. `install-known-good-closed`
7. `verify-dependencies-units-daemon-reload`
8. `verify-readiness-and-listeners`
9. `verify-nginx-closed-boundary`
10. `verify-browser-worker-cache`
11. `reopen-and-recover-watchdog`

Archive and sidecar verification completes before the watchdog, maintenance
selector, service state, cache trees, or release root can change. The recovery
trap is armed only after the maintenance selector, `nginx -t`, reload, and
drained state are established.

The cache purge authority contains exactly `web-nuxt/.output`,
`web-nuxt/.nuxt`, and `web-nuxt/.cache`. There is no dynamic readiness cache
path list, so no additional path is inferred. Absolute paths, parent segments,
symlinks, release-root deletion, `agent/data`, and protected descendants are
refused.

Closed admission is backend-independent: Nuxt on loopback port 3000 is
required. Port 8360 is validated as loopback-only when present, but a missing
agent listener does not invalidate a closed Nuxt release. Nginx remains the only
non-loopback owner of ports 80 and 443.

## Local rehearsal

Use disposable Git Bash paths, a synthetic Task 31 archive plus its sidecar,
an external fake environment file with no unlock names, an external runtime
authority directory, a release root, and a persistent data path. The local
command model can stand in only for unavailable privileged commands such as
`systemctl`, `nginx -t`, `findmnt`, and bind mount operations. Archive
verification, path/symlink checks, extraction, tree swap, phase recording, and
persistent byte hashing always execute for real.

```bash
KNOWN_GOOD_CLOSED=/tmp/vl360/known-good-closed.tar.gz \
LOCAL_RELEASE_ROOT=/tmp/vl360/release \
PERSISTENT_AGENT_DATA_ROOT=/tmp/vl360/persistent-agent-data \
ENVIRONMENT_AUTHORITY=/tmp/vl360/external.env \
RUNTIME_AUTHORITY=/tmp/vl360/runtime \
EVIDENCE_DIR=/tmp/vl360/evidence \
OPERATOR=local-reviewer \
OPERATOR_CIDR=127.0.0.1/32 \
CANDIDATE_RELEASE_ID=local-candidate \
ROLLBACK_RELEASE_ID=local-known-good \
bash scripts/ops/rehearse_launch_rollback.sh --local-rehearsal
```

The Task 43 browser script is always the browser authority. If no suitable
server or browser is available, it records `blocked`/`skipped`; no stub can
produce a browser pass. Docker/Nginx integration is likewise an explicit skip
when Docker is unavailable, never synthesized evidence. On a host with no
Nuxt listener on loopback port 3000, the rehearsal exits `2` after recording
`nuxt-3000-unavailable`; this is an expected blocked prerequisite, not a
successful closed-readiness claim. Recovery remains in maintenance and never
reopens traffic.

## Host execution gate

Do not run this command without a separate owner-approved operational task.
The exact acknowledgement is mandatory and is not approval by itself:

```bash
ACKNOWLEDGE_MAINTENANCE=launch-safety-rollback \
ENVIRONMENT_AUTHORITY=/approved/external/vl360.env \
RUNTIME_AUTHORITY=/approved/external/runtime \
MOUNT_AUTHORITY=/approved/bin/vl360-mount-authority \
bash scripts/ops/rehearse_launch_rollback.sh --execute-on-host
```

The watchdog timer's prior active state is recorded. It is restored only when
it was active before the operation; an intentionally inactive timer remains
inactive. The watchdog script independently checks the maintenance selector
before probes and again immediately before any restart.

## Failure and evidence semantics

An initial package verification failure leaves operational host state unchanged
and never arms recovery. A pre-reopen failure keeps traffic drained and repeats
the same verifier, installer, dependency/unit checks, readiness/listener proof,
Nginx proof, and real browser proof using a corrected closed package or the
known-good closed package. Recovery never disables maintenance or restores the
candidate/open tree.

After a reopen attempt, recovery first records maintenance enable, `nginx -t`,
reload, and maintenance probe as `passed`, `failed`, or `skipped`. Only all four
passing can establish `traffic_state=drained`; a recognized normal upstream is
`open`, and every inconclusive state is `unknown`. Package mutation is skipped
unless traffic is proven drained. The original failing exit status is preserved.

Listener evidence uses the `socket_boundary_probe.py` schema. Nginx proof uses
the Task 43 closed-boundary schema. Browser evidence uses the Task 43 controlled
worker/cache schema. Every phase and final summary hardcodes
`stage3_claim=false` and `live_sla_proven=false`, and records local elapsed time
only. Local evidence is not a live SLA, Stage 3, H1, H2, or launch approval.
