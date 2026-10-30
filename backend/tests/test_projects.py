import os

import pytest
from fastapi import HTTPException

from backend import storage

from .conftest import box


def test_list_starts_empty(client):
    assert client.get("/api/projects").json() == []


def test_create_returns_id_and_title(client):
    res = client.post("/api/projects", json={"title": "  My Series  "})
    assert res.status_code == 201
    assert res.json() == {"id": "my-series", "title": "My Series"}


def test_create_rejects_blank_name(client):
    assert client.post("/api/projects", json={"title": "   "}).status_code == 400


def test_duplicate_names_get_unique_ids(client, make_project):
    assert [make_project("Same"), make_project("Same"), make_project("Same")] == ["same", "same-2", "same-3"]
    assert {p["title"] for p in client.get("/api/projects").json()} == {"Same"}


def test_non_ascii_names_fall_back_to_a_safe_id(client, make_project):
    pid = make_project("ふたりバス")
    assert pid == "project"
    assert client.get(f"/api/projects/{pid}").json()["title"] == "ふたりバス"


def test_get_unknown_project_is_404(client):
    assert client.get("/api/projects/nope").status_code == 404


@pytest.mark.parametrize("bad", ["%2e%2e", "..%2F..%2Fetc", "a%20b", ".hidden", "UPPER"])
def test_malformed_ids_are_rejected_over_http(client, make_project, bad):
    make_project()
    assert client.get(f"/api/projects/{bad}").status_code == 404
    # 405 when an encoded slash makes the path miss the project routes entirely
    assert client.delete(f"/api/projects/{bad}").status_code in (404, 405)


@pytest.mark.parametrize("bad", ["..", "../x", "a/b", "a\\b", "", ".", "-lead", "x y"])
def test_project_dir_only_accepts_plain_slugs(bad):
    with pytest.raises(HTTPException) as err:
        storage.project_dir(bad)
    assert err.value.status_code == 404


def test_delete_cannot_remove_anything_outside_projects(client, make_project, data_dir):
    make_project()
    (data_dir / "precious.txt").write_text("keep")
    client.delete("/api/projects/%2e%2e")
    assert (data_dir / "precious.txt").exists() and (data_dir / "projects").exists()


def test_put_saves_everything_but_the_title(client, make_project):
    pid = make_project("Original")
    body = client.get(f"/api/projects/{pid}").json()
    body.update(title="HACKED", context="school comedy", glossary=[{"ja": "先輩", "en": "senpai", "note": ""}])
    body["pages"]["1.png"] = [box(flags=["too literal"], final="Hi")]
    assert client.put(f"/api/projects/{pid}", json=body).status_code == 200

    saved = client.get(f"/api/projects/{pid}").json()
    assert saved["title"] == "Original"
    assert saved["context"] == "school comedy"
    assert saved["glossary"][0]["en"] == "senpai"
    assert saved["pages"]["1.png"][0]["flags"] == ["too literal"]  # flags used to be dropped on save


def test_put_stores_pages_in_natural_order(client, make_project, data_dir):
    pid = make_project()
    body = client.get(f"/api/projects/{pid}").json()
    body["pages"] = {"11.jpg": [], "2.jpg": [], "1.jpg": []}
    client.put(f"/api/projects/{pid}", json=body)

    assert list(client.get(f"/api/projects/{pid}").json()["pages"]) == ["1.jpg", "2.jpg", "11.jpg"]
    # also on disk, not only in the API response
    import json

    on_disk = json.loads((data_dir / "projects" / pid / "project.json").read_text(encoding="utf-8"))
    assert list(on_disk["pages"]) == ["1.jpg", "2.jpg", "11.jpg"]


def test_put_rejects_malformed_body(client, make_project):
    pid = make_project()
    assert client.put(f"/api/projects/{pid}", json={"pages": {"1.png": [{"id": "x"}]}}).status_code == 422


def test_summaries_count_pages_and_bubbles(client, make_project):
    pid = make_project("Counted")
    body = client.get(f"/api/projects/{pid}").json()
    body["pages"] = {"1.png": [box("a"), box("b")], "2.png": [box("c")]}
    client.put(f"/api/projects/{pid}", json=body)

    (summary,) = client.get("/api/projects").json()
    assert (summary["id"], summary["pages"], summary["bubbles"]) == (pid, 2, 3)


def test_most_recently_edited_project_is_listed_first(client, make_project, data_dir):
    old, new = make_project("Old"), make_project("New")
    for pid, mtime in [(old, 1_000_000), (new, 2_000_000)]:
        os.utime(data_dir / "projects" / pid / "project.json", (mtime, mtime))
    assert [p["id"] for p in client.get("/api/projects").json()] == [new, old]

    os.utime(data_dir / "projects" / old / "project.json", (3_000_000, 3_000_000))
    assert [p["id"] for p in client.get("/api/projects").json()] == [old, new]


def test_delete_removes_project_and_its_files(client, make_project, upload, data_dir):
    pid = make_project()
    upload(pid)
    assert client.delete(f"/api/projects/{pid}").status_code == 200
    assert client.get(f"/api/projects/{pid}").status_code == 404
    assert not (data_dir / "projects" / pid).exists()
    assert client.get("/api/projects").json() == []


def test_delete_leaves_other_projects_alone(client, make_project, upload):
    keep, drop = make_project("Keep"), make_project("Drop")
    upload(keep)
    client.delete(f"/api/projects/{drop}")
    assert client.get(f"/api/projects/{keep}/pages/1.png").status_code == 200


def test_delete_unknown_project_is_404(client):
    assert client.delete("/api/projects/nope").status_code == 404
