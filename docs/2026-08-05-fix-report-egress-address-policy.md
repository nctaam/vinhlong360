> STATUS: active — fix report for branch `fix/egress-address-policy`, based on `8c7c7337`.
> Commit: `fabb156b` — `security: deny site-local, IPv4-translated and 6to4-relay egress targets`
> (both files in one commit, R20.7). Left untracked deliberately: only the two
> source files are committed.

**Process note (disclosed):** the first commit attempt used PowerShell
here-string syntax (`@'…'@`) inside the Bash tool, which does not understand
it, so a stray `@` line landed at the top and bottom of the message and the
subject became `@` instead of the required `security:` prefix. I amended
**my own commit from this session** (`b54fb588` → `fabb156b`) via
`git commit --amend -F <msgfile>` to fix only the message. No pre-existing
commit was amended, reset, rebased or reverted — the parent is still
`8c7c7337`, verified with `git log -1 --format=%P`. The tracked content is
byte-identical to the commit that passed the full pre-commit gate
(`run_hard: sạch (hard=0, ratchet không tăng)`); the amend restaged nothing,
so the hook reported no staged files on the second pass.

# Egress address-policy fixes — `agent/pinned_http.py`

Three confirmed defects in the shared DNS-pinned outbound HTTP client.
Environment: **Python 3.14.5**, Windows. Files touched: `agent/pinned_http.py`,
`tests/test_pinned_http.py` (nothing else).

Method: TDD. Every defect below has a demonstrated RED before the fix. For
Defects 2 and 3 the production behaviour was already correct, so RED was
produced by temporarily mutating production code (reverted immediately via
`git checkout --`) — the point of those defects is that the *tests* had no
teeth, and a test with teeth must be shown to go red against the regression it
claims to guard.

---

## Defect 1 (CRITICAL) — address policy accepted internal-ish IPv6 and IPv4 ranges

### Root cause

`_require_allowed_ip` delegated the non-transition case entirely to
`ipaddress.is_global`. Three independent gaps:

1. **`fec0::/10` (RFC 3879 site-local).** CPython 3.14 dropped this from
   `ipaddress._private_networks`, so `is_global` returns `True` for the whole
   /10 — including `fec0:0:0:ffff::/64`, the historical Windows default
   site-local resolver addresses. Nothing else in the module covered it.
2. **`::ffff:0:0:0/96` (RFC 2765 IPv4-translated).** A *different* network from
   the IPv4-**mapped** `::ffff:0:0/96`. `IPv6Address.ipv4_mapped` is `None`
   throughout the translated prefix, so the existing mapped check never fired,
   yet the address still embeds an IPv4 destination (`::ffff:0:7f00:1` embeds
   `127.0.0.1`).
3. **`192.88.99.0/24` (RFC 7526 6to4 relay anycast).** `IPv6Address.sixtofour`
   only ever sees the IPv6 side (`2002::/16`), which the module already denied.
   The IPv4 peer of the same mechanism was left open — the policy was
   half-applied to a single transition mechanism.

### RED evidence

New/extended test data added to `_BLOCKED_IPS` first, before any production
change:

```
$ python -m pytest tests/test_pinned_http.py -q
...
FAILED tests/test_pinned_http.py::test_resolver_rejects_blocked_and_transition_answers[192.88.99.1]
FAILED tests/test_pinned_http.py::test_resolver_rejects_blocked_and_transition_answers[192.88.99.255]
FAILED tests/test_pinned_http.py::test_resolver_rejects_blocked_and_transition_answers[::ffff:0:7f00:1]
FAILED tests/test_pinned_http.py::test_resolver_rejects_blocked_and_transition_answers[::ffff:0:a00:1]
FAILED tests/test_pinned_http.py::test_resolver_rejects_blocked_and_transition_answers[fec0::1]
FAILED tests/test_pinned_http.py::test_resolver_rejects_blocked_and_transition_answers[fec0:0:0:ffff::1]
FAILED tests/test_pinned_http.py::test_resolver_rejects_blocked_and_transition_answers[feff:ffff:ffff:ffff:ffff:ffff:ffff:ffff]
FAILED tests/test_pinned_http.py::test_blocked_literal_ip_never_calls_dns[192.88.99.1]
  ... (same 7 addresses)
FAILED tests/test_pinned_http.py::test_redirect_to_blocked_literal_is_rejected[192.88.99.1]
  ... (same 7 addresses)
21 failed, 134 passed in 4.48s
```

Failing for the right reason — the policy simply did not reject:

```
$ python -m pytest "...[fec0::1]" "...[::ffff:0:7f00:1]" "...[192.88.99.1]"
E       Failed: DID NOT RAISE <class 'pinned_http.BlockedAddressError'>
E       Failed: DID NOT RAISE <class 'pinned_http.BlockedAddressError'>
E       Failed: DID NOT RAISE <class 'pinned_http.BlockedAddressError'>
3 failed in 1.19s
```

(`test_redirect_to_blocked_literal_is_rejected` failed with
`RedirectPolicyError: redirect loop detected` — the client *accepted* the
address and followed the redirect into it, which is the same defect seen from
the redirect path.)

### Fix

Placed each denial where it reads honestly rather than lumping all three
together:

- **IPv4-translated → the IPv6 transition helper.** It is a transition form,
  the exact sibling of the mapped prefix already handled there.
  New module constant `_IPV4_TRANSLATED_NETWORK`, added as an `or` term in
  `_is_transition_address`.
- **Site-local and 6to4 relay anycast → a new broader denied-networks check.**
  `fec0::/10` is not a transition form at all (it is a deprecated internal
  scope), and `192.88.99.0/24` is IPv4 so it cannot live in an IPv6-only
  helper. Both are "reserved/deprecated ranges that `is_global` reports as
  global", which is a distinct, nameable category:

```python
_DENIED_NETWORKS = (
    ipaddress.ip_network("fec0::/10"),
    ipaddress.ip_network("192.88.99.0/24"),
)

def _is_denied_network(address) -> bool:
    return any(address in network for network in _DENIED_NETWORKS)
```

`_require_allowed_ip` gained one `if _is_denied_network(address): raise
BlockedAddressError(...)`. Mixing address families in one tuple is safe:
`ip_network.__contains__` returns `False` for an address of the other version
rather than raising (verified by execution: `IPv6Address('fec0::1') in
IPv4Network('192.88.99.0/24')` → `False`, and the reverse → `False`).

### Test-data gap closed

`_BLOCKED_IPS` had **no IPv6 private/ULA/link-local/site-local entry at all**.
Added `fc00::1`, `fd12:3456:789a::1`, `fe80::1` (already correctly denied by
`is_global`, now regression-locked in that direction too) alongside the newly
denied `fec0::1`, `fec0:0:0:ffff::1`, `feff:ffff:...:ffff` (top of the /10),
`::ffff:0:7f00:1`, `::ffff:0:a00:1`, `192.88.99.1`, `192.88.99.255`.

Also added `_ALLOWED_IPS` and `test_public_addresses_stay_allowed` as a
standing additive-denial guard, and repointed the existing
`test_public_literal_ip_never_calls_dns` at the same tuple.

### Other gaps found — reported, deliberately NOT fixed

Probing the wider IANA special-purpose space by execution turned up further
ranges that `is_global` still allows. I did **not** add them: the task scope is
the four confirmed addresses plus the same family, and none of these is the
same family. The principled boundary I applied is *"the module already denies
one side of this exact mechanism"* — true for 6to4 (`2002::/16` denied, IPv4
peer missed) and for the mapped/translated pair, false for everything below.
NAT64, Teredo and ISATAP have no reserved IPv4-side prefix, so 6to4 was the
only such inconsistency. Recorded here so the decision is visible, not lost:

| Still ALLOWED after this fix | Note |
| --- | --- |
| `192.31.196.0/24`, `192.175.48.0/24`, `2001:4:112::/48`, `2620:4f:8000::/48` | AS112 DNS sink (globally routed anycast) |
| `192.52.193.0/24`, `2001:3::/32` | AMT — a tunnelling mechanism neither side of which is currently denied |
| `2001:1::1`, `2001:1::2` | PCP / TURN anycast |
| `2001:20::/28`, `2001:30::/28` | ORCHIDv2, Drone Remote ID (non-routable identifiers) |
| `5f00::/16` | SRv6 SIDs — intended for use inside an SR domain, the closest of these to "internal-ish" |
| `fe00::/10` | unallocated reserved remainder of `fe00::/9`; unlike `fec0::/10` it was never a deployed scope |

Corroboration for the `fec0::/10` decision: `agent/tests/test_source_policy.py`
already asserts `http://[fec0::1]/source` and `http://[feff::1]/source` are
rejected by the *separate* source-URL policy. `pinned_http` was the outlier.

---

## Defect 2 (IMPORTANT) — nothing verified the pinned backend was installed

`network_backend=_PinnedNetworkBackend(hop)` is the single line that makes any
of the pinning real, and it appeared exactly once in the repo with no test
asserting it. httpcore's `ConnectionPool.__init__` does `SyncBackend() if
network_backend is None else network_backend`, and `SyncBackend` dials via
`socket.create_connection((host, port))` — its own unpoliced DNS resolution at
connect time.

### RED evidence

Temporarily deleted the kwarg from `agent/pinned_http.py`:

```
MUTATION APPLIED: dropped network_backend kwarg

$ python -m pytest ...::test_transport_wires_the_pinned_network_backend \
                   ...::test_transport_builds_verified_non_proxy_http1_pool -q
>       assert isinstance(backend, ph._PinnedNetworkBackend)
E       AssertionError: assert False
E        +  where False = isinstance(None, <class 'pinned_http._PinnedNetworkBackend'>)
1 failed, 1 passed in 2.40s
```

The pre-existing pool test passed against the mutant — it only ever asserted
`ssl_context`, `http1`, `http2`, `retries`, `max_connections`,
`max_keepalive_connections`, `proxy`.

And the decisive check — the whole file against the mutant with **only the new
test deselected**:

```
$ python -m pytest tests/test_pinned_http.py -q \
    --deselect "tests/test_pinned_http.py::test_transport_wires_the_pinned_network_backend"
21 failed, 133 passed, 1 deselected in 3.47s
```

21 failures — byte-for-byte the same 21 Defect-1 address failures present
*without* the mutation. Removing the pinning produced **zero** additional
failures. Production file restored with `git checkout -- agent/pinned_http.py`
(verified clean before the Defect-1 fix was written).

### Fix

`test_transport_wires_the_pinned_network_backend` asserts the pool receives a
`_PinnedNetworkBackend`, then proves it carries *this* hop behaviourally: it
dials the exact pre-approved sockaddr `("93.184.216.34", 443)` rather than by
name, and rejects `other.example` with `PeerMismatchError`.

---

## Defect 3 (MINOR) — the shared-connect-budget test had no teeth

`test_backend_fallback_uses_one_connect_budget` asserted only that fallback
reached the second address. `FakeSocket.timeouts` records every `settimeout`
value and the test never looked at it, so a per-address timeout **reset** —
which would let N addresses stretch a caller's 5s budget to N×5s — passed
unnoticed. Production behaviour is correct and was not changed.

### RED evidence

Throwaway probe simulating the regression (`_remaining_timeout` monkeypatched
to always return the full 5.0s), running the OLD assertion set and the NEW one
side by side:

```
test_OLD_assertions_against_regression PASSED   <- shipped test: no teeth
test_NEW_assertions_against_regression FAILED   <- strengthened test: teeth

>       assert first.timeouts == [4.0]
E       AssertionError: assert [5.0] == [4.0]
1 failed, 1 passed in 1.52s
```

Probe file deleted after capture.

### Fix

Named both sockets and asserted the exact shared monotonic budget:
deadline `10.0 + 5.0 = 15.0`; attempt 1 at `t=11.0` gets `4.0`, the fallback at
`t=12.0` gets only the remaining `3.0`.

```python
assert first.timeouts == [4.0]
assert second.timeouts == [3.0]
assert second.timeouts[0] < first.timeouts[0] < 5.0
```

---

## GREEN

```
$ python -m pytest tests/test_pinned_http.py -q
155 passed in 3.50s

$ python -m ruff check agent/pinned_http.py tests/test_pinned_http.py
All checks passed!
```

Complexity (repo limit R20.8 = 12), measured with the repo's own
`scripts/checks/check_complexity.py`:

| function | complexity |
| --- | --- |
| `_is_transition_address` | 8 |
| `_require_allowed_ip` | 7 |
| `_is_denied_network` | 2 |
| `_is_isatap` | 1 |

`ComplexityCheck().run(['agent/pinned_http.py'])` → **0 violations**.

---

## Before / after address verdicts

Produced by loading the pre-fix module from `git show 8c7c7337:agent/pinned_http.py`
side by side with the fixed one and calling `_require_allowed_ip` on each.

### The four confirmed-bad addresses

| address | before | after | |
| --- | --- | --- | --- |
| `fec0::1` | ALLOW | **BLOCK** | fixed |
| `fec0:0:0:ffff::1` | ALLOW | **BLOCK** | fixed |
| `::ffff:0:7f00:1` | ALLOW | **BLOCK** | fixed |
| `192.88.99.1` | ALLOW | **BLOCK** | fixed |

### Same-range siblings (also newly denied)

| address | before | after |
| --- | --- | --- |
| `fec0::` | ALLOW | **BLOCK** |
| `feff:ffff:ffff:ffff:ffff:ffff:ffff:ffff` | ALLOW | **BLOCK** |
| `::ffff:0:0:0` | ALLOW | **BLOCK** |
| `::ffff:0:a00:1` | ALLOW | **BLOCK** |
| `::ffff:0:ffff:ffff` | ALLOW | **BLOCK** |
| `192.88.99.0` | ALLOW | **BLOCK** |
| `192.88.99.255` | ALLOW | **BLOCK** |

11 addresses newly blocked.

### Already blocked — unchanged (no double-denial regressions)

`fc00::1`, `fd12:3456:789a::1`, `fe80::1`, `::1`, `127.0.0.1`, `::`,
`0.0.0.0`, `10.0.0.1`, `169.254.169.254`, `100.64.0.1`, `192.0.2.1`,
`224.0.0.1`, `240.0.0.1`, `::127.0.0.1`, `::ffff:127.0.0.1`,
`64:ff9b::7f00:1`, `64:ff9b:1::7f00:1`, `2002:7f00:1::`,
`2001:0000:4136:e378:8000:63bf:3fff:fdd2`, `2001:db8:1:2:0:5efe:7f00:1`
— all BLOCK before, BLOCK after.

### Legitimate public — must stay reachable (additive-denial contract)

| address | before | after |
| --- | --- | --- |
| `93.184.216.34` | ALLOW | ALLOW |
| `1.1.1.1` | ALLOW | ALLOW |
| `8.8.8.8` | ALLOW | ALLOW |
| `142.250.185.78` | ALLOW | ALLOW |
| `192.88.98.255` (just below the denied /24) | ALLOW | ALLOW |
| `192.88.100.0` (just above the denied /24) | ALLOW | ALLOW |
| `2606:2800:220:1:248:1893:25c8:1946` | ALLOW | ALLOW |
| `2001:4860:4860::8888` | ALLOW | ALLOW |
| `2a00:1450:4001:800::200e` | ALLOW | ALLOW |

**Regressions: NONE.** No address moved BLOCK → ALLOW, and no legitimate public
address moved ALLOW → BLOCK. The change is purely additive denial.

---

## Scope discipline

Not touched, as instructed: streaming body caps, global deadlines,
content-type enforcement, bounded decompression. No live DNS, no real sockets,
no data mutation, no secrets, no deploy, no push. Repo-wide suite, `--cov`,
`run_hard.py` and `run_backend_regression.py` were **not** run — only
`tests/test_pinned_http.py` and Ruff on the two touched files.

## Concerns

- **CPython-version-coupled policy.** The `fec0::/10` hole appeared because a
  stdlib classification changed under the module. `is_global` is a moving
  dependency; the denied-networks tuple now pins the ranges this module cares
  about explicitly, but the same class of drift can recur for any range still
  delegated to `is_global`. The residual-gap table above is the current
  exposure surface.
- **`::ffff:0:0:0/96` reachability is theoretical on most stacks**, but it was
  accepted by policy, which is the property under test.
