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


def migrate():
    storage.migrate_legacy()
    storage.migrate_chapters()


def test_migration_moves_legacy_data_into_a_project(legacy):
    migrate()

    assert not (legacy / "project.json").exists()
    assert not (legacy / "pages").exists()
    (summary,) = storage.list_projects()
    assert summary["title"] == "Old Series"
    folder = legacy / "projects" / summary["id"]
    assert (folder / "pages" / "chapter-1" / "1.png").exists()


def test_migration_registers_images_missing_from_the_project(legacy):
    migrate()
    (summary,) = storage.list_projects()
    project = storage.load_project(summary["id"])
    pages = project["chapters"][0]["pages"]
    assert list(pages) == ["1.png", "2.png", "orphan.png"]  # orphan added, notes.txt ignored
    assert pages["2.png"] == [{"id": "a"}]  # existing bubbles untouched
    assert project["context"] == "ctx"
    assert "pages" not in project


def test_migration_is_a_no_op_without_legacy_data(data_dir):
    storage.migrate_legacy()
    assert storage.list_projects() == []


def test_migration_runs_once(legacy):
    migrate()
    migrate()
    assert len(storage.list_projects()) == 1
    (summary,) = storage.list_projects()
    assert summary["chapters"] == 1 and summary["pages"] == 3


def test_migration_does_not_clobber_an_existing_project_with_the_same_name(legacy):
    existing = storage.create_project("Old Series")
    migrate()
    ids = {p["id"] for p in storage.list_projects()}
    assert ids == {existing, f"{existing}-2"}


def flat_project(data_dir, name="old"):
    """A project from before chapters: pages straight in project.json, images straight in pages/."""
    folder = data_dir / "projects" / name
    (folder / "pages").mkdir(parents=True)
    for image in ["1.png", "2.png", "stray.png"]:
        (folder / "pages" / image).write_bytes(png_bytes())
    project = {
        "title": "Old",
        "context": "ctx",
        "glossary": [],
        "pages": {"2.png": [{"id": "a", "x": 0, "y": 0, "w": 1, "h": 1}], "1.png": []},
    }
    (folder / "project.json").write_text(json.dumps(project), encoding="utf-8")
    return folder


def test_flat_projects_become_one_chapter(data_dir):
    folder = flat_project(data_dir)
    storage.migrate_chapters()

    project = storage.load_project("old")
    (chapter,) = project["chapters"]
    assert (chapter["id"], chapter["title"]) == ("chapter-1", "Chapter 1")
    assert list(chapter["pages"]) == ["1.png", "2.png", "stray.png"]
    assert chapter["pages"]["2.png"][0]["id"] == "a"
    assert "pages" not in project and project["context"] == "ctx"
    assert sorted(f.name for f in (folder / "pages" / "chapter-1").iterdir()) == ["1.png", "2.png", "stray.png"]
    assert [f.name for f in (folder / "pages").iterdir()] == ["chapter-1"]


def test_chapter_migration_is_idempotent_and_leaves_new_projects_alone(data_dir, client, make_project, make_chapter):
    flat_project(data_dir)
    pid = make_project("Fresh")
    make_chapter(pid, "Mine")
    storage.migrate_chapters()
    first = (data_dir / "projects" / "old" / "project.json").read_text(encoding="utf-8")
    storage.migrate_chapters()
    assert (data_dir / "projects" / "old" / "project.json").read_text(encoding="utf-8") == first
    assert [c["id"] for c in storage.load_project(pid)["chapters"]] == ["mine"]


def test_served_pages_still_work_after_migrating(data_dir):
    flat_project(data_dir)
    with TestClient(app) as client:
        assert client.get("/api/projects/old/chapters/chapter-1/pages/1.png").content == png_bytes()


def test_importing_the_app_does_not_migrate(legacy):
    """Migration belongs to startup; a plain TestClient (no lifespan) must leave data alone."""
    flat_project(legacy)
    TestClient(app).get("/api/projects")
    assert (legacy / "project.json").exists()
    assert "pages" in json.loads((legacy / "projects" / "old" / "project.json").read_text(encoding="utf-8"))


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
