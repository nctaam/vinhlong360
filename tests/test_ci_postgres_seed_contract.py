import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
SEED_COMMAND = "python agent/database.py --replace"
DESTRUCTIVE_ENV = {
    "DESTRUCTIVE_OPS_LOCKED": "0",
    "ALLOW_DESTRUCTIVE_DB_REPLACE": "1",
}


def _workflow() -> str:
    return CI_WORKFLOW.read_text(encoding="utf-8")


def _job(workflow: str, name: str) -> str:
    match = re.search(
        rf"^  {re.escape(name)}:\n(?P<body>.*?)(?=^  [a-z0-9_-]+:\n|\Z)",
        workflow,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match is not None, f"missing CI job: {name}"
    return match.group(0)


def _steps(job: str) -> list[str]:
    return re.findall(
        r"^      - name:.*?(?=^      - name:|\Z)",
        job,
        flags=re.MULTILINE | re.DOTALL,
    )


def test_postgres_job_seeds_knowledge_after_migrations_before_tests() -> None:
    workflow = _workflow()
    postgres_job = _job(workflow, "test-pg")

    assert "    services:\n      postgres:\n" in postgres_job

    seed_locations = [
        (job_name, index, step)
        for job_name in re.findall(r"^  ([a-z0-9_-]+):$", workflow, re.MULTILINE)
        for index, step in enumerate(_steps(_job(workflow, job_name)))
        if SEED_COMMAND in step
    ]
    assert len(seed_locations) == 1

    job_name, seed_index, seed_step = seed_locations[0]
    assert job_name == "test-pg"
    assert f"        run: {SEED_COMMAND}\n" in seed_step
    env_match = re.search(
        r"^        env:\n(?P<env>(?:^          .*\n)+)",
        seed_step,
        flags=re.MULTILINE,
    )
    assert env_match is not None
    assert set(env_match.group("env").splitlines()) == {
        '          DESTRUCTIVE_OPS_LOCKED: "0"',
        '          ALLOW_DESTRUCTIVE_DB_REPLACE: "1"',
    }

    steps = _steps(postgres_job)
    migration_index = next(
        index
        for index, step in enumerate(steps)
        if "python scripts/apply_migrations.py --init-baseline" in step
    )
    test_index = next(
        index
        for index, step in enumerate(steps)
        if "pytest tests/ agent/tests/" in step
    )
    assert migration_index < seed_index < test_index


def test_destructive_seed_authority_is_step_scoped_and_sqlite_stays_locked() -> None:
    workflow = _workflow()
    postgres_job = _job(workflow, "test-pg")
    sqlite_job = _job(workflow, "test")

    postgres_job_env = postgres_job.split("    steps:\n", 1)[0]
    assert all(name not in postgres_job_env for name in DESTRUCTIVE_ENV)
    assert workflow.count('ALLOW_DESTRUCTIVE_DB_REPLACE: "1"') == 1
    assert workflow.count('DESTRUCTIVE_OPS_LOCKED: "0"') == 1

    non_seed_steps = [
        step
        for job_name in re.findall(r"^  ([a-z0-9_-]+):$", workflow, re.MULTILINE)
        for step in _steps(_job(workflow, job_name))
        if SEED_COMMAND not in step
    ]
    for step in non_seed_steps:
        assert 'DESTRUCTIVE_OPS_LOCKED: "0"' not in step
        assert "ALLOW_DESTRUCTIVE_DB_REPLACE" not in step

    sqlite_test_step = next(
        step
        for step in _steps(sqlite_job)
        if "pytest tests/ agent/tests/" in step
    )
    assert 'DESTRUCTIVE_OPS_LOCKED: "1"' in sqlite_test_step
    assert "ALLOW_DESTRUCTIVE_DB_REPLACE" not in sqlite_test_step
    assert SEED_COMMAND not in sqlite_job
