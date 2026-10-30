import pytest


@pytest.fixture
def fake_ocr(monkeypatch):
    """
    Replace manga-ocr (a few hundred MB of model) with a recorder.
    """
    crops = []

    def ocr(image):
        crops.append(image)
        return "こんにちは"

    monkeypatch.setattr("backend.routers.ocr.get_ocr", lambda: ocr)
    return crops


@pytest.fixture
def page(workspace, upload):
    pid, cid = workspace
    return pid, cid, upload(pid, cid, "1.png", width=200, height=300)


def ocr_url(pid, cid):
    return f"/api/projects/{pid}/chapters/{cid}/ocr"


def test_ocr_reads_the_selected_region(client, fake_ocr, page):
    pid, cid, name = page
    res = client.post(ocr_url(pid, cid), json={"page": name, "x": 10, "y": 20, "w": 50, "h": 80})
    assert res.json() == {"ja": "こんにちは"}
    assert fake_ocr[0].size == (50, 80)  # the crop is in natural pixels, exactly the box


def test_ocr_truncates_each_edge_to_whole_pixels(client, fake_ocr, page):
    pid, cid, name = page
    # edges 10.9 -> 10 and 61.3 -> 61, so 51 wide; 20.9 -> 20 and 101.3 -> 101, so 81 tall
    client.post(ocr_url(pid, cid), json={"page": name, "x": 10.9, "y": 20.9, "w": 50.4, "h": 80.4})
    assert fake_ocr[0].size == (51, 81)


def test_ocr_rejects_collapsed_regions(client, fake_ocr, page):
    """A zero-size box (from the old scale bug) must be a clear 400, not an OCR call."""
    pid, cid, name = page
    res = client.post(ocr_url(pid, cid), json={"page": name, "x": 0, "y": 0, "w": 0, "h": 0})
    assert res.status_code == 400
    assert "too small" in res.json()["detail"]
    assert fake_ocr == []


def test_ocr_missing_page_is_404(client, fake_ocr, workspace):
    pid, cid = workspace
    res = client.post(ocr_url(pid, cid), json={"page": "nope.png", "x": 0, "y": 0, "w": 50, "h": 50})
    assert res.status_code == 404


def test_ocr_cannot_read_pages_of_another_chapter(client, fake_ocr, make_project, make_chapter, upload):
    pid = make_project()
    one, two = make_chapter(pid, "Chapter 1"), make_chapter(pid, "Chapter 2")
    name = upload(pid, one)
    res = client.post(ocr_url(pid, two), json={"page": name, "x": 0, "y": 0, "w": 20, "h": 20})
    assert res.status_code == 404


def test_ocr_cannot_read_pages_of_another_project(client, fake_ocr, make_project, make_chapter, upload):
    a, b = make_project("A"), make_project("B")
    cid = make_chapter(a)
    make_chapter(b)  # same chapter id in both projects
    name = upload(a, cid)
    res = client.post(ocr_url(b, cid), json={"page": name, "x": 0, "y": 0, "w": 20, "h": 20})
    assert res.status_code == 404


def test_ocr_page_name_cannot_escape_the_chapter_folder(client, fake_ocr, page):
    pid, cid, _ = page
    res = client.post(ocr_url(pid, cid), json={"page": "../../project.json", "x": 0, "y": 0, "w": 20, "h": 20})
    assert res.status_code == 404


def test_ocr_unknown_project_or_chapter_is_404(client, fake_ocr, workspace):
    pid, _ = workspace
    body = {"page": "1.png", "x": 0, "y": 0, "w": 20, "h": 20}
    assert client.post(ocr_url("nope", "chapter-1"), json=body).status_code == 404
    assert client.post(ocr_url(pid, "nope"), json=body).status_code == 404
