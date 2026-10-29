from .conftest import png_bytes


def test_upload_registers_page_and_serves_it(client, make_project, upload):
    pid = make_project()
    assert upload(pid, "1.png") == "1.png"
    assert client.get(f"/api/projects/{pid}").json()["pages"] == {"1.png": []}
    res = client.get(f"/api/projects/{pid}/pages/1.png")
    assert res.status_code == 200
    assert res.content == png_bytes()


def test_upload_keeps_existing_bubbles(client, make_project, upload):
    pid = make_project()
    upload(pid, "1.png")
    body = client.get(f"/api/projects/{pid}").json()
    body["pages"]["1.png"] = [{"id": "a", "x": 0, "y": 0, "w": 5, "h": 5, "final": "keep me"}]
    client.put(f"/api/projects/{pid}", json=body)

    upload(pid, "2.png")
    pages = client.get(f"/api/projects/{pid}").json()["pages"]
    assert pages["1.png"][0]["final"] == "keep me"
    assert "2.png" in pages


def test_same_filename_is_renamed_not_overwritten(client, make_project, upload):
    pid = make_project()
    assert [upload(pid, "p.png", 10, 10), upload(pid, "p.png", 20, 20), upload(pid, "p.png", 30, 30)] == [
        "p.png",
        "p-1.png",
        "p-2.png",
    ]
    assert client.get(f"/api/projects/{pid}/pages/p.png").content == png_bytes(10, 10)
    assert client.get(f"/api/projects/{pid}/pages/p-1.png").content == png_bytes(20, 20)


def test_pages_are_listed_in_natural_order(client, make_project, upload):
    pid = make_project()
    for name in ["11.png", "1.png", "2.png"]:
        upload(pid, name)
    assert list(client.get(f"/api/projects/{pid}").json()["pages"]) == ["1.png", "2.png", "11.png"]


def test_non_image_upload_is_rejected(client, make_project):
    pid = make_project()
    res = client.post(f"/api/projects/{pid}/pages", files={"file": ("x.png", b"not an image", "image/png")})
    assert res.status_code == 400
    assert client.get(f"/api/projects/{pid}").json()["pages"] == {}


def test_upload_filename_cannot_escape_the_pages_folder(client, make_project, upload, data_dir):
    pid = make_project()
    assert upload(pid, "../../evil.png") == "evil.png"
    assert not (data_dir / "evil.png").exists()
    assert (data_dir / "projects" / pid / "pages" / "evil.png").exists()


def test_pages_belong_to_their_own_project(client, make_project, upload):
    a, b = make_project("A"), make_project("B")
    upload(a, "1.png")
    assert client.get(f"/api/projects/{b}").json()["pages"] == {}
    assert client.get(f"/api/projects/{b}/pages/1.png").status_code == 404


def test_upload_and_fetch_for_unknown_project_is_404(client):
    res = client.post("/api/projects/nope/pages", files={"file": ("1.png", png_bytes(), "image/png")})
    assert res.status_code == 404
    assert client.get("/api/projects/nope/pages/1.png").status_code == 404


def test_missing_page_is_404(client, make_project):
    pid = make_project()
    assert client.get(f"/api/projects/{pid}/pages/nope.png").status_code == 404
