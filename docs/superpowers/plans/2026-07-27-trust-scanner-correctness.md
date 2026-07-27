# Trust and Scanner Correctness Implementation Plan

> STATUS: done - approved umbrella design is `docs/superpowers/specs/2026-07-27-hardening-closure-design.md`; Plan A implementation and verification are complete.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make field-verification claims attribute-authoritative and make repository/package artifact checks inspect only inputs they own.

**Architecture:** `agent/database.py` owns one canonical `attributes.verifiedAt` accessor and removes every legacy top-level mirror; the API, export path, TypeScript contract, and entity byline consume that single meaning. `scripts/package_launch_release.py` separates a pure candidate validator from Git-index and immutable-snapshot providers, so repository hygiene ignores ambient files while package validation remains fail-closed over the exact bytes being archived.

**Tech Stack:** Python 3.10+, FastAPI data projection, pytest, Nuxt 4/Vue 3, TypeScript, Vitest, Git index plumbing, deterministic tar/gzip packaging, Ruff, repository hard checks.

## Global Constraints

- Execute only after re-reading `CLAUDE.md` and the approved umbrella spec at commit `9f078774` or its reviewed descendant.
- `attributes.verifiedAt` is the only field-verification authority. Never fall back to top-level `verifiedAt`, `updatedAt`, `createdAt`, `verified`, source presence, publish status, or freshness metadata.
- Remove top-level `verifiedAt` from normalized and public output even when a genuine `attributes.verifiedAt` exists; do not create a compatibility mirror.
- Do not rewrite the local knowledge DB, PostgreSQL, or `web/data.json`; no backup is required because this plan changes code, tests, and plan-status documentation only.
- Repository hygiene must use null-delimited `git ls-files`; do not add `.claude`, worktree, cache, or runtime-path ignore rules.
- Package integrity must inspect the exact immutable `_LaunchReleaseSnapshot.members` used by the archive writer, after snapshot capture and before output replacement.
- Preserve symlink, regular-file, lexical-location, exact-byte, atomic replacement, deterministic ordering, and destination-safety guarantees.
- Use uncommitted RED tests, make them GREEN, then commit. Never commit a known failing test because `CLAUDE.md` B5 requires every task commit to leave the repository working.
- Do not push, deploy, rotate secrets, enable indexing, mutate production data, or touch the untracked `agent/knowledge.db-shm` and `agent/knowledge.db-wal` files.

---

## File Structure

- Modify `agent/database.py`: add `canonical_verified_at()` and remove top-level verification mirroring from `_normalize_entity_timestamps()`.
- Modify `agent/public_api.py`: derive source freshness through the canonical accessor and strip legacy `verifiedAt` in the owned public projection.
- Modify `scripts/export_data.py`: remove legacy top-level `verifiedAt` defensively from future DB exports.
- Modify `agent/tests/test_database.py`: lock accessor normalization, adversarial inputs, and no-mirror timestamp behavior.
- Modify `agent/tests/test_public_api.py`: lock attribute-only freshness and conflicting legacy-field behavior.
- Modify `agent/tests/test_upgrade_phase1.py`: migrate freshness fixtures to `attributes.verifiedAt` and keep the historical contract suite truthful.
- Modify `tests/test_export_data.py`: prove exports retain only `attributes.verifiedAt` without writing `web/data.json`.
- Modify `web-nuxt/pages/dia-diem/[id].vue`: drive the byline only from `source_freshness.verified_at`.
- Modify `web-nuxt/types/index.ts`: remove top-level `Entity.verifiedAt` from the public type.
- Modify `web-nuxt/tests/smoke.test.ts`: lock truthful byline and absence of the legacy frontend access path.
- Modify `scripts/package_launch_release.py`: add the pure scanner, Git provider, snapshot provider, and immutable backend-package validation.
- Modify `tests/launch_safety/test_artifact_packaging.py`: lock Git-index ownership, lexical validation, and backend archive behavior.
- Modify `tests/launch_safety/test_release_package.py`: lock snapshot-member validation, ambient-noise immunity, exact bytes, and failure-before-publication.
- Modify this plan only after all Plan A gates pass: set `STATUS: done` and append exact results without checking historical execution boxes retroactively.

---

### Task 1: Make Field Verification Attribute-Authoritative

**Files:**
- Modify: `agent/database.py:1777-1841`
- Modify: `agent/public_api.py:207-250,977-984`
- Modify: `scripts/export_data.py:43-51`
- Modify: `agent/tests/test_database.py:660-686`
- Modify: `agent/tests/test_public_api.py:1-34`
- Modify: `agent/tests/test_upgrade_phase1.py:8-69`
- Modify: `tests/test_export_data.py:110-153`
- Modify: `web-nuxt/pages/dia-diem/[id].vue:932-964`
- Modify: `web-nuxt/types/index.ts:87-117`
- Modify: `web-nuxt/tests/smoke.test.ts:342-350`

**Interfaces:**
- Consumes: `Mapping[str, object]`, `datetime.fromisoformat`, existing `_days_since()`, `EntitySourceFreshness.verified_at`, and the owned `_project_public_entity_media()` projection.
- Produces: `canonical_verified_at(entity: Mapping[str, object]) -> str | None`; normalized entities with no top-level `verifiedAt`; public entities with no top-level `verifiedAt`; frontend byline authority at `source_freshness.verified_at` only.

- [ ] **Step 1: Write the failing canonical timestamp and normalization tests**

Update the import block in `agent/tests/test_database.py` to import `canonical_verified_at`, then replace the legacy mirror expectation and add the adversarial cases:

```python
def test_canonical_verified_at_reads_only_attribute() -> None:
    entity = {
        "verifiedAt": "2026-07-27T00:00:00Z",
        "attributes": {"verifiedAt": "2026-06-08T07:00:00+07:00"},
    }

    assert canonical_verified_at(entity) == "2026-06-08T00:00:00Z"


@pytest.mark.parametrize(
    "entity",
    [
        {"verifiedAt": "2026-07-27T00:00:00Z"},
        {"updatedAt": "2026-07-27T00:00:00Z"},
        {"verified": True},
        {"attributes": {"verifiedAt": ""}},
        {"attributes": {"verifiedAt": "not-a-date"}},
        {"attributes": {"verifiedAt": 123}},
        {"attributes": "not-an-object"},
    ],
)
def test_canonical_verified_at_rejects_legacy_or_invalid_values(entity: dict) -> None:
    assert canonical_verified_at(entity) is None


def test_normalization_removes_legacy_top_level_without_mirroring_attribute() -> None:
    entity = {
        "verifiedAt": "2026-07-27T00:00:00Z",
        "attributes": {"verifiedAt": "2026-06-08T00:00:00Z"},
    }

    result = _normalize_entity_timestamps(entity)

    assert "verifiedAt" not in result
    assert result["attributes"]["verifiedAt"] == "2026-06-08T00:00:00Z"
```

Keep the existing `updatedAt` and `createdAt` tests. Change `test_explicit_verified_at_in_attributes` so it asserts the attribute is retained and the top-level key is absent.

- [ ] **Step 2: Write the failing API, export, and frontend contract tests**

Replace top-level fixtures in `agent/tests/test_public_api.py` and `agent/tests/test_upgrade_phase1.py` with `{"attributes": {"verifiedAt": ...}}`. Add these API cases:

```python
def test_top_level_verified_at_is_never_verification_authority() -> None:
    result = _build_source_freshness(
        {"verifiedAt": _days_ago(1), "updatedAt": _days_ago(1)}
    )
    assert result["verified_at"] is None
    assert result["days_since_verified"] is None
    assert result["freshness_status"] == "unknown"


def test_attribute_wins_when_top_level_value_conflicts() -> None:
    result = _build_source_freshness(
        {
            "verifiedAt": _days_ago(1),
            "updatedAt": _days_ago(1),
            "attributes": {"verifiedAt": _days_ago(400)},
        }
    )
    assert result["freshness_status"] == "stale"


def test_public_projection_removes_legacy_verified_at() -> None:
    from public_api import _project_public_entity_media

    projected = _project_public_entity_media(
        {"id": "entity-1", "verifiedAt": "2026-07-27T00:00:00Z"}
    )
    assert "verifiedAt" not in projected
```

Add an export regression in `tests/test_export_data.py`:

```python
def test_export_keeps_only_attribute_verified_at(tmp_db, tmp_path, monkeypatch) -> None:
    from export_data import export

    entities = tmp_db.all_entities()
    entities[0]["verifiedAt"] = "2026-07-27T00:00:00Z"
    entities[0]["attributes"] = {"verifiedAt": "2026-06-08T00:00:00Z"}
    monkeypatch.setattr(tmp_db, "all_entities", lambda: entities)
    output = tmp_path / "out.json"

    export(tmp_db, str(output), dry_run=False)

    exported = json.loads(output.read_text(encoding="utf-8"))["entities"][0]
    assert "verifiedAt" not in exported
    assert exported["attributes"]["verifiedAt"] == "2026-06-08T00:00:00Z"
```

Extend the existing Vitest source contract in `web-nuxt/tests/smoke.test.ts`:

```typescript
expect(types).not.toContain('verifiedAt?: string')
expect(detail).toContain('sourceFreshness.value?.verified_at')
expect(detail).not.toContain('entity.value?.verifiedAt')
expect(detail).toContain('chưa kiểm chứng thực địa')
```

- [ ] **Step 3: Run the focused tests and confirm RED**

```powershell
python -m pytest agent/tests/test_database.py agent/tests/test_public_api.py agent/tests/test_upgrade_phase1.py tests/test_export_data.py -q
Set-Location web-nuxt
npm test -- --run tests/smoke.test.ts
Set-Location ..
```

Expected: backend failures show the missing `canonical_verified_at`, the retained/mirrored top-level field, and freshness still reading the legacy field; Vitest fails because the type and byline still expose `verifiedAt`.

- [ ] **Step 4: Implement the canonical accessor and no-mirror normalization**

Add `Mapping` to the `collections.abc` import in `agent/database.py`. Place this accessor immediately after `_coerce_iso_date()`:

```python
def canonical_verified_at(entity: Mapping[str, object]) -> str | None:
    """Return normalized field-verification time from attributes only."""
    attributes = entity.get("attributes")
    if not isinstance(attributes, Mapping):
        return None
    raw = attributes.get("verifiedAt")
    if not isinstance(raw, str) or not raw.strip():
        return None
    candidate = raw.strip()
    try:
        parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    else:
        parsed = parsed.astimezone(timezone.utc)
    return parsed.isoformat(timespec="seconds").replace("+00:00", "Z")
```

Update `_normalize_entity_timestamps()` so its docstring names only `updatedAt` and `createdAt`, then remove the legacy key unconditionally:

```python
    d.pop("verifiedAt", None)
    return d
```

Do not rewrite or normalize `attributes.verifiedAt` inside this serializer. The accessor normalizes reads; the attribute remains the sole stored representation.

- [ ] **Step 5: Route API, export, type, and byline through the canonical contract**

Import `canonical_verified_at` from `database` in `agent/public_api.py`. Update `_build_source_freshness()`:

```python
    updated_at = entity.get("updatedAt")
    verified_at = canonical_verified_at(entity)
```

Extend `_project_public_entity_media()` with defense-in-depth removal before returning the owned copy:

```python
    projected.pop("verifiedAt", None)
```

Update `normalize_entity_shape()` in `scripts/export_data.py`:

```python
def normalize_entity_shape(e: dict) -> dict:
    out = {k: v for k, v in e.items() if k not in FLAT_COLS and k != "verifiedAt"}
    if "createdAt" not in out and out.get("created_at") is not None:
        out["createdAt"] = out["created_at"]
    return out
```

Delete the top-level `verifiedAt` member and stale comment from `web-nuxt/types/index.ts`. Replace the detail-page computed value with:

```typescript
const entityVerifiedAt = computed(() => sourceFreshness.value?.verified_at || '')
```

Keep the existing verified and unverified Vietnamese byline strings unchanged.

- [ ] **Step 6: Run focused verification and Ruff**

```powershell
python -m pytest agent/tests/test_database.py agent/tests/test_public_api.py agent/tests/test_upgrade_phase1.py tests/test_export_data.py -q
python -m ruff check agent/database.py agent/public_api.py scripts/export_data.py agent/tests/test_database.py agent/tests/test_public_api.py agent/tests/test_upgrade_phase1.py tests/test_export_data.py
Set-Location web-nuxt
npm test -- --run tests/smoke.test.ts
npm run typecheck
npm run build
Set-Location ..
git diff --check
```

Expected: every command exits `0`; no test or build writes `web/data.json`; `git status --short` shows only the owned code/test files plus the two pre-existing untracked WAL/SHM files.

- [ ] **Step 7: Commit the verifiedAt contract**

```powershell
git add agent/database.py agent/public_api.py scripts/export_data.py agent/tests/test_database.py agent/tests/test_public_api.py agent/tests/test_upgrade_phase1.py tests/test_export_data.py 'web-nuxt/pages/dia-diem/[id].vue' web-nuxt/types/index.ts web-nuxt/tests/smoke.test.ts
git commit -m "fix: make field verification attribute-authoritative"
```

Expected: the commit succeeds without `--no-verify`, includes paired tests, and leaves `web/data.json`, `agent/knowledge.db-shm`, and `agent/knowledge.db-wal` untouched.

---

### Task 2: Scope Artifact Scanners to Git and Immutable Snapshots

**Files:**
- Modify: `scripts/package_launch_release.py:1-15,128-148,269-286,357-375,527-557,620-630,1305-1350`
- Modify: `tests/launch_safety/test_artifact_packaging.py:1-90`
- Modify: `tests/launch_safety/test_release_package.py:503-565`

**Interfaces:**
- Consumes: candidate pairs `(logical_path: str, source_path: Path)`, `git ls-files -z`, `_LaunchReleaseSnapshot.members`, and `write_deterministic_tar_gz()`.
- Produces: `find_duplicate_artifacts(candidates: Iterable[tuple[str, Path]]) -> list[str]`, `find_tracked_duplicate_artifacts(root: Path) -> list[str]`, and `find_snapshot_duplicate_artifacts(snapshot: _LaunchReleaseSnapshot) -> list[str]`.

- [ ] **Step 1: Replace ambient-tree tests with RED candidate-domain tests**

Update imports in `tests/launch_safety/test_artifact_packaging.py` to include `subprocess`, `find_tracked_duplicate_artifacts`, and `find_snapshot_duplicate_artifacts`. Replace the tests that pass a root to `find_duplicate_artifacts()` with explicit candidates:

```python
def test_candidate_scanner_rejects_alias_symlink_and_non_file(tmp_path: Path) -> None:
    canonical = tmp_path / "config" / "launch-indexing-policy.json"
    canonical.parent.mkdir()
    canonical.write_bytes(b"{}")
    alias = tmp_path / "web-nuxt" / canonical.name
    alias.parent.mkdir()
    alias.symlink_to(canonical)
    directory = tmp_path / "config" / "ai-disclosure.json"
    directory.mkdir()

    assert find_duplicate_artifacts(
        (
            ("config/launch-indexing-policy.json", canonical),
            ("web-nuxt/launch-indexing-policy.json", alias),
            ("config/ai-disclosure.json", directory),
        )
    ) == ["config/ai-disclosure.json", "web-nuxt/launch-indexing-policy.json"]


def test_candidate_scanner_rejects_duplicate_canonical_member(tmp_path: Path) -> None:
    canonical = tmp_path / "config" / "launch-indexing-policy.json"
    canonical.parent.mkdir()
    canonical.write_bytes(b"{}")

    assert find_duplicate_artifacts(
        (
            ("config/launch-indexing-policy.json", canonical),
            ("config/launch-indexing-policy.json", canonical),
        )
    ) == ["config/launch-indexing-policy.json"]
```

Add a temporary Git fixture and repository-domain assertions:

```python
def _git_root(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "config").mkdir(parents=True)
    for name in CANONICAL_ARTIFACTS:
        (root / "config" / name).write_bytes(b"{}")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "config"], check=True)
    return root


def test_tracked_scanner_detects_staged_duplicate(tmp_path: Path) -> None:
    root = _git_root(tmp_path)
    duplicate = root / "web-nuxt" / "launch-indexing-policy.json"
    duplicate.parent.mkdir()
    duplicate.write_bytes(b"{}")
    subprocess.run(["git", "-C", str(root), "add", "web-nuxt"], check=True)

    assert find_tracked_duplicate_artifacts(root) == [
        "web-nuxt/launch-indexing-policy.json"
    ]


def test_tracked_scanner_detects_committed_duplicate(tmp_path: Path) -> None:
    root = _git_root(tmp_path)
    duplicate = root / "web-nuxt" / "launch-indexing-policy.json"
    duplicate.parent.mkdir()
    duplicate.write_bytes(b"{}")
    subprocess.run(["git", "-C", str(root), "add", "web-nuxt"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Scanner Test",
            "-c",
            "user.email=scanner@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )

    assert find_tracked_duplicate_artifacts(root) == [
        "web-nuxt/launch-indexing-policy.json"
    ]


def test_tracked_scanner_ignores_untracked_nested_worktree_noise(tmp_path: Path) -> None:
    root = _git_root(tmp_path)
    noise = root / ".claude" / "worktrees" / "task" / "config"
    noise.mkdir(parents=True)
    (noise / "launch-indexing-policy.json").write_bytes(b"{}")

    assert find_tracked_duplicate_artifacts(root) == []
```

Keep the real repository assertion, but call `find_tracked_duplicate_artifacts(REPO_ROOT)`.

- [ ] **Step 2: Add RED immutable-package tests**

In `tests/launch_safety/test_artifact_packaging.py`, replace the old ambient `web-nuxt` duplicate with a member that `_collect_payload()` actually packages:

```python
def test_backend_archive_rejects_duplicate_artifacts_before_writing(tmp_path: Path):
    root = _release_source(tmp_path)
    (root / "config" / "launch-indexing-policy.json").write_text("{}", encoding="utf-8")
    duplicate = root / "agent" / "launch-indexing-policy.json"
    duplicate.write_text("{}", encoding="utf-8")
    destination = tmp_path / "backend.tar.gz"
    destination.write_bytes(b"previous archive")

    with pytest.raises(ValueError, match="duplicate canonical"):
        build_backend_archive(root, destination)

    assert destination.read_bytes() == b"previous archive"
```

This test proves the package provider validates a member it owns; an untracked file outside the backend payload belongs only in the repository-domain test.

In `tests/launch_safety/test_release_package.py`, add an ambient non-member test:

```python
def test_launch_release_ignores_ambient_non_member_duplicate(tmp_path: Path) -> None:
    root = tmp_path / "source"
    audit = _write_launch_fixture(root)
    ambient = root / "docs" / "launch-indexing-policy.json"
    ambient.parent.mkdir()
    ambient.write_bytes(b"not packaged")

    package = build_launch_release(
        root,
        tmp_path / "release.tar.gz",
        compose_network_audit=audit,
        source_revision="reviewed-source-revision",
    )

    with tarfile.open(package.archive, "r:gz") as bundle:
        assert "docs/launch-indexing-policy.json" not in bundle.getnames()
```

Add a duplicate-snapshot-member test that fails before either output is published:

```python
def test_launch_release_rejects_duplicate_snapshot_member_without_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "source"
    audit = _write_launch_fixture(root)
    destination = tmp_path / "release.tar.gz"
    real_snapshot = release_package._snapshot_launch_release

    def duplicate_snapshot(root_path, payload):
        snapshot = real_snapshot(root_path, payload)
        canonical = next(
            member
            for member in snapshot.members
            if member.arcname == "config/launch-indexing-policy.json"
        )
        duplicate = release_package._SnapshotMember(
            canonical.source,
            "web-nuxt/launch-indexing-policy.json",
        )
        return release_package._LaunchReleaseSnapshot(
            snapshot.root,
            snapshot.members + (duplicate,),
            snapshot.sources,
        )

    monkeypatch.setattr(
        release_package,
        "_snapshot_launch_release",
        duplicate_snapshot,
    )

    with pytest.raises(ValueError, match="duplicate canonical"):
        build_launch_release(
            root,
            destination,
            compose_network_audit=audit,
            source_revision="reviewed-source-revision",
        )

    assert not destination.exists()
    assert not destination.with_name(destination.name + ".sha256").exists()
    assert list(tmp_path.glob(".*.tmp")) == []
```

- [ ] **Step 3: Run scanner tests and confirm RED**

```powershell
python -m pytest tests/launch_safety/test_artifact_packaging.py tests/launch_safety/test_release_package.py -q -k "canonical or duplicate or snapshot or ambient or worktree or exact_packaged"
```

Expected: failures show the old root-based signature, ambient `rglob()` discovery, and snapshot validation still calling the repository-tree scanner.

- [ ] **Step 4: Implement the pure validator and Git-index provider**

Add `subprocess`, `Iterable`, and `PurePosixPath` imports in `scripts/package_launch_release.py`. Replace the root walker with:

```python
def find_duplicate_artifacts(
    candidates: Iterable[tuple[str, Path]],
) -> list[str]:
    invalid: set[str] = set()
    canonical_counts = {name: 0 for name in CANONICAL_ARTIFACTS}
    for logical_path, source_path in candidates:
        logical = PurePosixPath(logical_path.replace("\\", "/"))
        name = logical.name
        if name not in canonical_counts:
            continue
        expected = PurePosixPath("config") / name
        if logical == expected:
            canonical_counts[name] += 1
            if canonical_counts[name] > 1:
                invalid.add(logical.as_posix())
        else:
            invalid.add(logical.as_posix())
        if source_path.is_symlink() or not source_path.is_file():
            invalid.add(logical.as_posix())
    return sorted(invalid)


def find_tracked_duplicate_artifacts(root: Path) -> list[str]:
    root = _lexical_path(root)
    completed = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--cached"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    logical_paths = [
        os.fsdecode(raw)
        for raw in completed.stdout.split(b"\0")
        if raw
    ]
    return find_duplicate_artifacts(
        (
            logical,
            root.joinpath(*PurePosixPath(logical).parts),
        )
        for logical in logical_paths
    )
```

Do not catch a failed Git command and fall back to `rglob()`. Repository hygiene must fail visibly if it cannot read the index.

- [ ] **Step 5: Implement snapshot validation and immutable backend packaging**

Define the snapshot provider immediately after `_LaunchReleaseSnapshot` is available:

```python
def find_snapshot_duplicate_artifacts(
    snapshot: _LaunchReleaseSnapshot,
) -> list[str]:
    return find_duplicate_artifacts(
        (member.arcname, member.source.path)
        for member in snapshot.members
    )
```

Remove duplicate discovery from `_preflight()`. In `build_backend_archive()`, capture and validate the payload before creating or replacing output:

```python
    _preflight(root, destination)
    snapshot = _snapshot_tar_payload(_collect_payload(root))
    duplicates = find_snapshot_duplicate_artifacts(snapshot)
    if duplicates:
        raise ValueError(
            "duplicate canonical launch artifacts: " + ", ".join(duplicates)
        )
```

Write the backend archive from the same snapshot:

```python
        write_deterministic_tar_gz(temporary, snapshot, {})
        os.replace(temporary, destination)
```

In `_validated_canonical_artifacts()`, replace `find_duplicate_artifacts(root)` with `find_snapshot_duplicate_artifacts(snapshot)`. Keep `_snapshot_raw()` as the byte authority for the two canonical JSON artifacts. Do not add an ambient filesystem scan anywhere in the package path.

- [ ] **Step 6: Run focused scanner/package verification**

```powershell
python -m pytest tests/launch_safety/test_artifact_packaging.py tests/launch_safety/test_release_package.py -q
python -m ruff check scripts/package_launch_release.py tests/launch_safety/test_artifact_packaging.py tests/launch_safety/test_release_package.py
git diff --check
```

Expected: all commands exit `0`; the real repository check ignores untracked `.claude/worktrees`; package tests still prove exact archived bytes, deterministic output, symlink rejection, and unchanged destinations on failure.

- [ ] **Step 7: Commit scanner domain separation**

```powershell
git add scripts/package_launch_release.py tests/launch_safety/test_artifact_packaging.py tests/launch_safety/test_release_package.py
git commit -m "fix: scope release artifact scanners to owned inputs"
```

Expected: the commit succeeds with paired tests and no unrelated runtime files staged.

---

### Task 3: Verify Plan A and Record Its Result

**Files:**
- Modify after verification: `docs/superpowers/plans/2026-07-27-trust-scanner-correctness.md`

**Interfaces:**
- Consumes: the two green implementation commits from Tasks 1-2.
- Produces: a revision-bound `STATUS: done` plan result with exact commands, counts, exit codes, and remaining Plan B dependency.

- [ ] **Step 1: Run the complete Plan A backend subset**

```powershell
python -m pytest agent/tests/test_database.py agent/tests/test_public_api.py agent/tests/test_upgrade_phase1.py tests/test_export_data.py tests/launch_safety/test_artifact_packaging.py tests/launch_safety/test_release_package.py -q
```

Expected: exit `0` with no newly skipped or weakened assertions. Record the exact pass/skip counts in the result section.

- [ ] **Step 2: Run the complete frontend gates**

```powershell
Set-Location web-nuxt
npm test
npm run typecheck
npm run build
Set-Location ..
```

Expected: all three commands exit `0`. Record their exact summaries; do not treat warnings as success without identifying whether they were already present.

- [ ] **Step 3: Run repository hard gates**

```powershell
python scripts/checks/run_hard.py --all
git diff --check
git status --short
```

Expected: `run_hard.py` exits `0` with `hard=0` and no ratchet increase; `git diff --check` exits `0`; status contains no owned uncommitted code/test changes and still leaves `agent/knowledge.db-shm` and `agent/knowledge.db-wal` untracked.

- [ ] **Step 4: Mark this plan done with exact evidence**

Change the status line to `STATUS: done`. Append a `## KẾT QUẢ` section whose bullets copy the literal revision, commit ids, command lines, exit codes, and test summaries printed by Steps 1-3. Use this shape, replacing the descriptive phrases with measured values rather than leaving a template marker:

```markdown
## KẾT QUẢ

- Revision verified: the literal output of `git rev-parse HEAD` after Task 2.
- Implementation commits: the two literal hashes printed by `git log --oneline` for the verifiedAt and scanner commits.
- Backend focused gate: the exact command from Step 1, literal exit `0`, and its measured counts.
- Frontend gates: `npm test`, `npm run typecheck`, and `npm run build`, each with literal exit `0` and measured summaries.
- Repository gates: `python scripts/checks/run_hard.py --all` -> exit `0`, `hard=0`, no ratchet increase; `git diff --check` -> exit `0`.
- Data/operations: no DB or `web/data.json` rewrite, no push, no deploy, no production mutation; pre-existing WAL/SHM files remain untouched.
- Next dependency: execute `docs/superpowers/plans/2026-07-27-bound-complete-pinned-egress.md`.
```

Copy the measured values into the bullets before staging. Do not check all execution boxes retroactively; `## KẾT QUẢ` is the completion authority.

- [ ] **Step 5: Commit the Plan A evidence**

```powershell
git add docs/superpowers/plans/2026-07-27-trust-scanner-correctness.md
git commit -m "docs: record trust scanner verification"
```

Expected: the commit succeeds and Plan B can start from this verified revision.

## KẾT QUẢ

- Revision verified: `git rev-parse HEAD` -> `f5b26a6160da71330cff92484f43e5c99fe818fd`.
- Implementation commits: `fe84a09ed090bfc8198cb49b267b7896567ec0b9 fix: make field verification attribute-authoritative`; `f5b26a6160da71330cff92484f43e5c99fe818fd fix: scope release artifact scanners to owned inputs`.
- Backend focused gate: `python -m pytest agent/tests/test_database.py agent/tests/test_public_api.py agent/tests/test_upgrade_phase1.py tests/test_export_data.py tests/launch_safety/test_artifact_packaging.py tests/launch_safety/test_release_package.py -q` -> exit `0`; `248 passed, 1 skipped, 1 xfailed in 43.53s` (the skip and xfail are existing platform/design cases; no Task 3 assertions were changed).
- Frontend gates: `npm test` -> exit `0`; `37` test files passed and `912` tests passed in `34.33s`; `npm run typecheck` -> exit `0`; `nuxt typecheck` completed with no diagnostics; `npm run build` -> exit `0`; `746 modules transformed`, `Σ Total size: 6.45 MB (1.62 MB gzip)`, `Build complete!`, and launch-readiness manifest generated for `f5b26a6160da71330cff92484f43e5c99fe818fd`. Existing Nuxt/Vite sourcemap, >500 kB chunk-size, and Node `DEP0155` dependency warnings were observed; no implementation or assertion failure occurred.
- Repository gates: `python scripts/checks/run_hard.py --all` -> exit `0`, `hard=0`, ratchet không tăng (the output also reports R50.3 `7 < baseline 8`); `git diff --check` -> exit `0`; `git status --short` -> only `?? agent/knowledge.db-shm` and `?? agent/knowledge.db-wal`.
- Data/operations: no DB or `web/data.json` rewrite, no push, no deploy, no production mutation; pre-existing WAL/SHM files remain untouched.
- Final combined verification after Plan B: revision `de7efa3fbc26cb04430bc3e6f98afe50fef48724`; focused pinned gate `303 passed in 22.36s`; frontend test ownership/hook stability commit `de7efa3f` made the exact `npm test` exit `0` with `37` files/`912` tests passed in `30.49s`; typecheck and build exited `0` (`746 modules`, `6.45 MB`, manifest generated for `de7efa3f`). Hard gate `hard=0` with no ratchet increase; official bounded backend exit `0` in `6901.2s` with Phase A `8633 passed, 58 skipped, 111 deselected, 1 xfailed` and Phase B `284 passed, 19 skipped`. No data rewrite, push, deploy, production mutation, secret change, or indexing change occurred.
