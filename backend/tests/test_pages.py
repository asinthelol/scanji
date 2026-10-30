from .conftest import png_bytes


def test_upload_registers_page_and_serves_it(client, workspace, upload):
    pid, cid = workspace
    assert upload(pid, cid, "1.png") == "1.png"
    assert client.get(f"/api/projects/{pid}").json()["chapters"][0]["pages"] == {"1.png": []}
    res = client.get(f"/api/projects/{pid}/chapters/{cid}/pages/1.png")
    assert res.status_code == 200
    assert res.content == png_bytes()


def test_upload_keeps_existing_bubbles(client, workspace, upload, set_pages):
    pid, cid = workspace
    upload(pid, cid, "1.png")
    set_pages(pid, cid, {"1.png": [{"id": "a", "x": 0, "y": 0, "w": 5, "h": 5, "final": "keep me"}]})

    upload(pid, cid, "2.png")
    pages = client.get(f"/api/projects/{pid}").json()["chapters"][0]["pages"]
    assert pages["1.png"][0]["final"] == "keep me"
    assert "2.png" in pages


def test_same_filename_is_renamed_not_overwritten(client, workspace, upload):
    pid, cid = workspace
    names = [upload(pid, cid, "p.png", 10, 10), upload(pid, cid, "p.png", 20, 20), upload(pid, cid, "p.png", 30, 30)]
    assert names == ["p.png", "p-1.png", "p-2.png"]
    assert client.get(f"/api/projects/{pid}/chapters/{cid}/pages/p.png").content == png_bytes(10, 10)
    assert client.get(f"/api/projects/{pid}/chapters/{cid}/pages/p-1.png").content == png_bytes(20, 20)


def test_pages_are_listed_in_natural_order(client, workspace, upload):
    pid, cid = workspace
    for name in ["11.png", "1.png", "2.png"]:
        upload(pid, cid, name)
    pages = client.get(f"/api/projects/{pid}").json()["chapters"][0]["pages"]
    assert list(pages) == ["1.png", "2.png", "11.png"]


def test_non_image_upload_is_rejected(client, workspace):
    pid, cid = workspace
    res = client.post(f"/api/projects/{pid}/chapters/{cid}/pages", files={"file": ("x.png", b"not an image", "image/png")})
    assert res.status_code == 400
    assert client.get(f"/api/projects/{pid}").json()["chapters"][0]["pages"] == {}


def test_upload_filename_cannot_escape_the_chapter_folder(workspace, upload, data_dir):
    pid, cid = workspace
    assert upload(pid, cid, "../../evil.png") == "evil.png"
    assert not (data_dir / "evil.png").exists()
    assert (data_dir / "projects" / pid / "pages" / cid / "evil.png").exists()


def test_the_same_page_name_can_exist_in_two_chapters(client, make_project, make_chapter, upload):
    pid = make_project()
    one, two = make_chapter(pid, "Chapter 1"), make_chapter(pid, "Chapter 2")
    assert upload(pid, one, "1.png", 10, 10) == upload(pid, two, "1.png", 20, 20) == "1.png"
    assert client.get(f"/api/projects/{pid}/chapters/{one}/pages/1.png").content == png_bytes(10, 10)
    assert client.get(f"/api/projects/{pid}/chapters/{two}/pages/1.png").content == png_bytes(20, 20)


def test_pages_belong_to_their_own_chapter(client, make_project, make_chapter, upload):
    pid = make_project()
    one, two = make_chapter(pid, "Chapter 1"), make_chapter(pid, "Chapter 2")
    upload(pid, one, "1.png")
    chapters = {c["id"]: c for c in client.get(f"/api/projects/{pid}").json()["chapters"]}
    assert chapters[two]["pages"] == {}
    assert client.get(f"/api/projects/{pid}/chapters/{two}/pages/1.png").status_code == 404


def test_pages_belong_to_their_own_project(client, make_project, make_chapter, upload):
    a, b = make_project("A"), make_project("B")
    cid = make_chapter(a)
    make_chapter(b)  # same chapter id in both projects
    upload(a, cid, "1.png")
    assert client.get(f"/api/projects/{b}/chapters/{cid}/pages/1.png").status_code == 404


def test_upload_and_fetch_for_unknown_project_or_chapter_is_404(client, workspace):
    pid, _ = workspace
    files = {"file": ("1.png", png_bytes(), "image/png")}
    assert client.post("/api/projects/nope/chapters/chapter-1/pages", files=files).status_code == 404
    assert client.post(f"/api/projects/{pid}/chapters/nope/pages", files=files).status_code == 404
    assert client.get(f"/api/projects/{pid}/chapters/nope/pages/1.png").status_code == 404


def test_missing_page_is_404(client, workspace):
    pid, cid = workspace
    assert client.get(f"/api/projects/{pid}/chapters/{cid}/pages/nope.png").status_code == 404
