import json

import pytest

from backend import storage
from backend.main import app
from fastapi.testclient import TestClient

from .conftest import png_bytes


@pytest.mark.parametrize(
    ("name", "slug"),
    [
        ("My Series", "my-series"),
        ("  Chapter #1: The Bus!  ", "chapter-1-the-bus"),
        ("Café Étoile", "cafe-etoile"),
        ("ふたりバス", "project"),
        ("", "project"),
        ("../../etc", "etc"),
    ],
)
def test_slugify(name, slug):
    assert storage.slugify(name) == slug


def test_natural_key_orders_numbers_numerically():
    names = ["10.jpg", "2.jpg", "1.jpg", "b2.jpg", "b10.jpg", "A1.jpg"]
    assert sorted(names, key=storage.natural_key) == ["1.jpg", "2.jpg", "10.jpg", "A1.jpg", "b2.jpg", "b10.jpg"]


@pytest.fixture
def legacy(data_dir):
    """The pre-multi-project layout: data/project.json + data/pages/."""
    (data_dir / "pages").mkdir()
    for name in ["1.png", "2.png", "orphan.png"]:
        (data_dir / "pages" / name).write_bytes(png_bytes())
    (data_dir / "pages" / "notes.txt").write_text("not an image")
    project = {"title": "Old Series", "context": "ctx", "glossary": [], "pages": {"2.png": [{"id": "a"}], "1.png": []}}
    (data_dir / "project.json").write_text(json.dumps(project), encoding="utf-8")
    return data_dir


def test_migration_moves_legacy_data_into_a_project(legacy):
    storage.migrate_legacy()

    assert not (legacy / "project.json").exists()
    assert not (legacy / "pages").exists()
    (summary,) = storage.list_projects()
    assert summary["title"] == "Old Series"
    folder = legacy / "projects" / summary["id"]
    assert (folder / "pages" / "1.png").exists()


def test_migration_registers_images_missing_from_the_project(legacy):
    storage.migrate_legacy()
    (summary,) = storage.list_projects()
    pages = storage.load_project(summary["id"])["pages"]
    assert list(pages) == ["1.png", "2.png", "orphan.png"]  # orphan added, notes.txt ignored
    assert pages["2.png"] == [{"id": "a"}]  # existing bubbles untouched
    assert storage.load_project(summary["id"])["context"] == "ctx"


def test_migration_is_a_no_op_without_legacy_data(data_dir):
    storage.migrate_legacy()
    assert storage.list_projects() == []


def test_migration_runs_once(legacy):
    storage.migrate_legacy()
    storage.migrate_legacy()
    assert len(storage.list_projects()) == 1


def test_migration_does_not_clobber_an_existing_project_with_the_same_name(legacy):
    existing = storage.create_project("Old Series")
    storage.migrate_legacy()
    ids = {p["id"] for p in storage.list_projects()}
    assert ids == {existing, f"{existing}-2"}


def test_importing_the_app_does_not_migrate(legacy):
    """Migration belongs to startup; a plain TestClient (no lifespan) must leave data alone."""
    TestClient(app).get("/api/projects")
    assert (legacy / "project.json").exists()


def test_startup_runs_the_migration(legacy):
    with TestClient(app) as client:
        assert [p["title"] for p in client.get("/api/projects").json()] == ["Old Series"]


def test_spa_routes_serve_the_app_but_api_typos_404(client, monkeypatch, tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>app</html>")
    monkeypatch.setattr("backend.main.FRONTEND_DIST", dist)

    assert client.get("/").text == "<html>app</html>"
    assert client.get("/p/some-project").text == "<html>app</html>"  # refresh on a client-side route
    assert client.get("/api/not-a-route").status_code == 404
    assert client.get("/api").status_code == 404  # an API typo must not return the app


def test_missing_frontend_build_explains_itself(client, monkeypatch, tmp_path):
    monkeypatch.setattr("backend.main.FRONTEND_DIST", tmp_path / "missing")
    res = client.get("/")
    assert res.status_code == 503
    assert "npm run build" in res.text
