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
def upload(client):
    """
    Upload a generated PNG page to a project and return the stored page name.
    """

    def up(pid: str, name: str = "1.png", width: int = 40, height: int = 60) -> str:
        res = client.post(f"/api/projects/{pid}/pages", files={"file": (name, png_bytes(width, height), "image/png")})
        assert res.status_code == 200
        return res.json()["name"]

    return up


def box(id: str = "b1", **fields) -> dict:
    """
    A bubble in project.json form.
    """
    return {"id": id, "x": 0, "y": 0, "w": 10, "h": 10, **fields}
