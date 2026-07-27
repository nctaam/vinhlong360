# Pinned Egress Security Observability

> STATUS: active - approved design; implementation has not started.

## Decision

Add one centralized, sanitized warning event at the public
`PinnedHTTPClient.get()` boundary for the three security-denial classes that are
currently operationally silent:

- `BlockedAddressError`;
- `PeerMismatchError`;
- `RedirectPolicyError`.

The three mapped consumers keep their existing return values, HTTP status
mapping, and failure behavior. The only product change is that a blocked egress
attempt becomes distinguishable from an ordinary slow or unavailable site in
local/server logs.

## Why The Log Belongs At The Client Boundary

Logging independently in admin, auto-learn, and quality-burst would duplicate
policy knowledge, produce inconsistent fields, and risk continuing the existing
raw-URL logging pattern. Logging in `_require_allowed_ip()` or
`_check_peer_matches_approved()` would know the low-level address but not the
consumer, redirect hop, or request lifecycle and could emit multiple records for
one request.

`PinnedHTTPClient.get()` is the smallest boundary that has all required context
and can guarantee exactly one event before re-raising the original typed error.

## Public Contract

`PinnedHTTPClient.get()` gains one required keyword-only argument:

```python
audit_context: str
```

The mapped production callers use stable literals:

| Consumer | `audit_context` |
| --- | --- |
| Admin image review | `admin_image_review` |
| Auto-learn source ingestion | `auto_learn` |
| GPT-5.5 quality-burst source verification | `quality_burst` |

The argument is required so future consumers cannot silently enter the shared
egress boundary without an operational identity. A small sanitizer lowercases
ASCII text, replaces each maximal run outside `[a-z0-9._-]` with `_`, strips
leading/trailing separators, truncates to 64 characters, and uses `unknown` if
no safe characters remain. Sanitization never changes fetch success or failure.

## Event Contract

The module uses a dedicated logger named `security.egress`. Every matching
failure produces one `WARNING` record with fixed-format fields:

```text
Pinned egress denied consumer=<context> reason=<reason> target=<origin> hop=<n>
```

Reason codes are stable and derived from exception type, never from exception
text:

| Exception | Reason |
| --- | --- |
| `BlockedAddressError` | `blocked_address` |
| `PeerMismatchError` | `peer_mismatch` |
| `RedirectPolicyError` | `redirect_policy` |

`hop` is zero for the initial request and increments for each accepted redirect.
The original exception is re-raised unchanged after logging.

The client does not emit this security event for ordinary resolution failure,
transport failure, deadline exhaustion, resolver saturation, body limits, or
content-encoding rejection. Existing consumer behavior for those failures stays
unchanged.

## Target Sanitization

The `target` field contains only a normalized origin:

```text
<scheme>://<ascii-host>:<effective-port>
```

Rules:

- include only `http` or `https`, ASCII host, and effective port;
- bracket IPv6 hosts;
- never include username, password, path, query, fragment, redirect `Location`,
  headers, response body, or raw exception text;
- return `<invalid>` when a safe origin cannot be derived;
- use logger argument substitution rather than interpolating untrusted input into
  the format string.

The normalized host or literal IP is intentionally retained because operators
must be able to distinguish which destination triggered the denial. Path/query
data is unnecessary for this goal and is the most likely place for tokens or
personal information to appear.

## Consumer Behavior

### Admin image review

Policy and redirect denials still map to the existing localized HTTP 400
responses. Transport/status failures still map to HTTP 502. The central security
event is the only new side effect.

### Auto-learn

Security denials return `None` as before. Auto-learn must not emit its existing
raw-URL warning for those three typed errors, otherwise the request would be
logged twice and could leak path/query data. Its existing warning behavior for
non-security exceptions remains outside this change.

### Quality-burst

Security denials still return an empty string and `verify_source_url()` still
returns `(False, "URL could not be fetched")`. The consumer remains silent; the
central `security.egress` warning is the sole observability event. Bounded body,
encoding, deadline, and resolver-saturation failures remain completely silent to
preserve the existing noise contract.

## Test Strategy

Implementation follows RED-GREEN TDD.

1. Add failing client tests proving each security exception maps to the correct
   reason and produces exactly one record.
2. Prove the record contains the audit context, sanitized origin, and redirect
   hop but not path, query, fragment, userinfo, redirect location, or raw
   exception text.
3. Prove body/decode/deadline/resolver/ordinary transport failures do not emit
   the security event.
4. Update the three consumer contract tests to require their exact
   `audit_context` literals.
5. Add real, no-network blocked-literal tests for admin, auto-learn, and
   quality-burst to prove their return/status behavior is unchanged and only one
   central record is emitted.
6. Run the focused pinned/consumer suite, Ruff, hard checks, and repository diff
   hygiene. The broader backend baseline remains required before completion.

## Documentation Truth-Sync

After all gates pass:

- mark this spec `done` and append measured results;
- close the operationally-silent egress residual in `docs/ROADMAP.md` and
  `docs/HANDOFF.md`;
- retain the cookie-gate incompatibility, unmigrated outbound callers, and
  unobserved production behavior as genuine residuals;
- record that no push, deployment, database rewrite, secret change, or indexing
  change occurred.

## Non-Goals

- No external logging service, SIEM, metrics backend, alerting integration, or
  paid dependency.
- No persistence of security events in the application database.
- No migration of the currently excluded outbound callers.
- No cookie jar or consent-redirect support.
- No change to destination policy, DNS pinning, body limits, decompression, or
  deadline semantics.
- No production deployment or production log inspection.

## Risks And Controls

- **Log leakage:** controlled by origin-only formatting, fixed reason codes, and
  exclusion of raw exception text.
- **Duplicate records:** controlled by logging once at `PinnedHTTPClient.get()`
  and suppressing auto-learn's consumer warning only for the three security
  errors.
- **Noise increase:** controlled by excluding ordinary network and bounded-body
  failures.
- **Future silent consumers:** controlled by the required `audit_context`
  argument and consumer-registry tests.
- **False completion claim:** local verification proves only code behavior; prod
  observability remains unproven until a separately authorized deployment.
