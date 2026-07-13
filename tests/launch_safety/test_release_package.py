from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_nuxt_compose_build_uses_repository_root_context():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    nuxt_service = compose.split("\n  nuxt:\n", 1)[1].split("\n  nginx:\n", 1)[0]

    assert "context: ." in nuxt_service
    assert "dockerfile: web-nuxt/Dockerfile" in nuxt_service
    assert "context: ./web-nuxt" not in nuxt_service


def test_nuxt_image_builds_from_web_project_and_root_config():
    dockerfile = (ROOT / "web-nuxt" / "Dockerfile").read_text(encoding="utf-8")

    assert "WORKDIR /app/web-nuxt" in dockerfile
    assert "COPY web-nuxt/package*.json ./" in dockerfile
    assert "COPY web-nuxt/ ./" in dockerfile
    assert "COPY config/ /app/config/" in dockerfile
    assert "COPY --from=build /app/web-nuxt/.output ./.output" in dockerfile


def test_backend_image_contains_root_config():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "COPY config/ ./config/" in dockerfile


def test_deploy_packages_and_snapshots_root_config():
    deploy = (ROOT / "scripts" / "deploy.sh").read_text(encoding="utf-8")

    assert 'init.sql config web/data.json' in deploy
    assert "agent web/data.json web/media web-nuxt/.output config" in deploy


def test_docker_context_excludes_secrets_and_local_build_caches():
    ignored = set((ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines())

    assert {
        ".env",
        "**/.env",
        ".git",
        ".pytest_cache",
        ".ruff_cache",
        "web-nuxt/.nuxt",
        "web-nuxt/.output",
    } <= ignored
