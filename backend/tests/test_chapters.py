import pytest

from backend import storage

from .conftest import box


def chapters(client, pid):
    return client.get(f"/api/projects/{pid}").json()["chapters"]


def test_new_projects_have_no_chapters(client, make_project):
    assert chapters(client, make_project()) == []


def test_create_returns_id_and_title(client, make_project):
    pid = make_project()
    res = client.post(f"/api/projects/{pid}/chapters", json={"title": "  Chapter 12: The Bus  "})
    assert res.status_code == 201
    assert res.json() == {"id": "chapter-12-the-bus", "title": "Chapter 12: The Bus"}
    assert chapters(client, pid) == [{"id": "chapter-12-the-bus", "title": "Chapter 12: The Bus", "pages": {}}]


def test_create_rejects_blank_name(client, make_project):
    pid = make_project()
    assert client.post(f"/api/projects/{pid}/chapters", json={"title": "  "}).status_code == 400


def test_create_in_unknown_project_is_404(client):
    assert client.post("/api/projects/nope/chapters", json={"title": "x"}).status_code == 404


def test_duplicate_titles_get_unique_ids(client, make_project, make_chapter):
    pid = make_project()
    assert [make_chapter(pid, "Same"), make_chapter(pid, "Same")] == ["same", "same-2"]


def test_non_ascii_titles_fall_back_to_a_safe_id(client, make_project, make_chapter):
    pid = make_project()
    assert make_chapter(pid, "第1話") == "1"  # the digit survives
    assert make_chapter(pid, "最終話") == "chapter"


def test_chapters_are_listed_in_natural_order(client, make_project, make_chapter):
    pid = make_project()
    for title in ["Chapter 10", "Chapter 2", "Chapter 1"]:
        make_chapter(pid, title)
    assert [c["title"] for c in chapters(client, pid)] == ["Chapter 1", "Chapter 2", "Chapter 10"]


def test_chapter_ids_are_unique_per_project_not_global(client, make_project, make_chapter):
    assert make_chapter(make_project("A"), "Chapter 1") == make_chapter(make_project("B"), "Chapter 1")


def test_delete_removes_chapter_and_its_images(client, workspace, upload, data_dir):
    pid, cid = workspace
    upload(pid, cid)
    assert client.delete(f"/api/projects/{pid}/chapters/{cid}").status_code == 200
    assert chapters(client, pid) == []
    assert not (data_dir / "projects" / pid / "pages" / cid).exists()
    assert client.get(f"/api/projects/{pid}/chapters/{cid}/pages/1.png").status_code == 404


def test_delete_leaves_other_chapters_alone(client, make_project, make_chapter, upload):
    pid = make_project()
    keep, drop = make_chapter(pid, "Keep"), make_chapter(pid, "Drop")
    upload(pid, keep)
    client.delete(f"/api/projects/{pid}/chapters/{drop}")
    assert [c["id"] for c in chapters(client, pid)] == [keep]
    assert client.get(f"/api/projects/{pid}/chapters/{keep}/pages/1.png").status_code == 200


def test_delete_unknown_chapter_is_404(client, make_project):
    pid = make_project()
    assert client.delete(f"/api/projects/{pid}/chapters/nope").status_code == 404
    assert client.delete("/api/projects/nope/chapters/nope").status_code == 404


@pytest.mark.parametrize("bad", ["..", "../x", "a/b", "", ".", "-lead", "UPPER"])
def test_chapter_dir_only_accepts_plain_slugs(workspace, bad):
    pid, _ = workspace
    with pytest.raises(Exception) as err:
        storage.chapter_dir(pid, bad)
    assert err.value.status_code == 404


def test_chapters_share_the_project_glossary_and_context(client, make_project, make_chapter):
    pid = make_project()
    make_chapter(pid, "One")
    make_chapter(pid, "Two")
    body = client.get(f"/api/projects/{pid}").json()
    body.update(context="school comedy", glossary=[{"ja": "先輩", "en": "senpai", "note": ""}])
    client.put(f"/api/projects/{pid}", json=body)
    saved = client.get(f"/api/projects/{pid}").json()
    assert saved["context"] == "school comedy" and saved["glossary"][0]["en"] == "senpai"
    assert len(saved["chapters"]) == 2


# ---- saving a project must not undo chapter changes made through the chapter routes ----


def test_a_stale_save_cannot_drop_a_new_chapter(client, make_project, make_chapter):
    pid = make_project()
    stale = client.get(f"/api/projects/{pid}").json()  # the page was loaded before the chapter existed
    cid = make_chapter(pid, "New")
    assert client.put(f"/api/projects/{pid}", json=stale).status_code == 200
    assert [c["id"] for c in chapters(client, pid)] == [cid]


def test_a_stale_save_cannot_bring_back_a_deleted_chapter(client, make_project, make_chapter, data_dir):
    pid = make_project()
    cid = make_chapter(pid, "Doomed")
    stale = client.get(f"/api/projects/{pid}").json()
    client.delete(f"/api/projects/{pid}/chapters/{cid}")
    assert client.put(f"/api/projects/{pid}", json=stale).status_code == 200
    assert chapters(client, pid) == []


def test_save_cannot_rename_or_invent_chapters(client, make_project, make_chapter):
    pid = make_project()
    cid = make_chapter(pid, "Real")
    body = client.get(f"/api/projects/{pid}").json()
    body["chapters"][0]["title"] = "HACKED"
    body["chapters"].append({"id": "invented", "title": "Invented", "pages": {"x.png": []}})
    client.put(f"/api/projects/{pid}", json=body)
    saved = chapters(client, pid)
    assert [(c["id"], c["title"]) for c in saved] == [(cid, "Real")]


def test_save_updates_only_the_chapters_it_sends(client, make_project, make_chapter, set_pages):
    pid = make_project()
    one, two = make_chapter(pid, "One"), make_chapter(pid, "Two")
    set_pages(pid, two, {"1.png": [box("keep", final="untouched")]})
    body = client.get(f"/api/projects/{pid}").json()
    body["chapters"] = [c for c in body["chapters"] if c["id"] == one]  # a client that only knows chapter one
    body["chapters"][0]["pages"] = {"9.png": []}
    client.put(f"/api/projects/{pid}", json=body)
    by_id = {c["id"]: c for c in chapters(client, pid)}
    assert list(by_id[one]["pages"]) == ["9.png"]
    assert by_id[two]["pages"]["1.png"][0]["final"] == "untouched"
