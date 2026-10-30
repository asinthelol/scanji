"""Every test uses a throwaway data folder."""
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend import storage
from backend.main import app


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    projects = tmp_path / "projects"
    projects.mkdir()
    monkeypatch.setattr(storage, "PROJECTS", projects)
    monkeypatch.setattr(storage, "LEGACY_PROJECT_FILE", tmp_path / "project.json")
    monkeypatch.setattr(storage, "LEGACY_PAGES", tmp_path / "pages")
    return tmp_path


@pytest.fixture
def client():
    return TestClient(app)


def png_bytes(width: int = 40, height: int = 60) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), "white").save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture
def make_project(client):
    """
    Create a project through the API and return its id.
    """

    def make(title: str = "Test Series") -> str:
        res = client.post("/api/projects", json={"title": title})
        assert res.status_code == 201
        return res.json()["id"]

    return make


@pytest.fixture
def make_chapter(client):
    """
    Create a chapter through the API and return its id.
    """

    def make(pid: str, title: str = "Chapter 1") -> str:
        res = client.post(f"/api/projects/{pid}/chapters", json={"title": title})
        assert res.status_code == 201
        return res.json()["id"]

    return make


@pytest.fixture
def upload(client):
    """
    Upload a generated PNG page to a chapter and return the stored page name.
    """

    def up(pid: str, cid: str, name: str = "1.png", width: int = 40, height: int = 60) -> str:
        res = client.post(
            f"/api/projects/{pid}/chapters/{cid}/pages", files={"file": (name, png_bytes(width, height), "image/png")}
        )
        assert res.status_code == 200
        return res.json()["name"]

    return up


@pytest.fixture
def set_pages(client):
    """
    Save `pages` (name -> bubbles) as the contents of a chapter.
    """

    def save(pid: str, cid: str, pages: dict) -> None:
        body = client.get(f"/api/projects/{pid}").json()
        next(c for c in body["chapters"] if c["id"] == cid)["pages"] = pages
        assert client.put(f"/api/projects/{pid}", json=body).status_code == 200

    return save


@pytest.fixture
def workspace(make_project, make_chapter):
    """
    A project with one chapter: (project id, chapter id).
    """
    pid = make_project()
    return pid, make_chapter(pid)


def box(id: str = "b1", **fields) -> dict:
    """
    A bubble in project.json form.
    """
    return {"id": id, "x": 0, "y": 0, "w": 10, "h": 10, **fields}
