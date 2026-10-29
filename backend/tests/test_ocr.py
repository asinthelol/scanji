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
def page(make_project, upload):
    pid = make_project()
    return pid, upload(pid, "1.png", width=200, height=300)


def test_ocr_reads_the_selected_region(client, fake_ocr, page):
    pid, name = page
    res = client.post(f"/api/projects/{pid}/ocr", json={"page": name, "x": 10, "y": 20, "w": 50, "h": 80})
    assert res.json() == {"ja": "こんにちは"}
    assert fake_ocr[0].size == (50, 80)  # the crop is in natural pixels, exactly the box


def test_ocr_truncates_each_edge_to_whole_pixels(client, fake_ocr, page):
    pid, name = page
    # edges 10.9 -> 10 and 61.3 -> 61, so 51 wide; 20.9 -> 20 and 101.3 -> 101, so 81 tall
    client.post(f"/api/projects/{pid}/ocr", json={"page": name, "x": 10.9, "y": 20.9, "w": 50.4, "h": 80.4})
    assert fake_ocr[0].size == (51, 81)


def test_ocr_rejects_collapsed_regions(client, fake_ocr, page):
    """A zero-size box (from the old scale bug) must be a clear 400, not an OCR call."""
    pid, name = page
    res = client.post(f"/api/projects/{pid}/ocr", json={"page": name, "x": 0, "y": 0, "w": 0, "h": 0})
    assert res.status_code == 400
    assert "too small" in res.json()["detail"]
    assert fake_ocr == []


def test_ocr_missing_page_is_404(client, fake_ocr, make_project):
    pid = make_project()
    res = client.post(f"/api/projects/{pid}/ocr", json={"page": "nope.png", "x": 0, "y": 0, "w": 50, "h": 50})
    assert res.status_code == 404


def test_ocr_cannot_read_pages_of_another_project(client, fake_ocr, make_project, upload):
    a, b = make_project("A"), make_project("B")
    name = upload(a)
    res = client.post(f"/api/projects/{b}/ocr", json={"page": name, "x": 0, "y": 0, "w": 20, "h": 20})
    assert res.status_code == 404


def test_ocr_page_name_cannot_escape_the_pages_folder(client, fake_ocr, page):
    pid, _ = page
    res = client.post(f"/api/projects/{pid}/ocr", json={"page": "../project.json", "x": 0, "y": 0, "w": 20, "h": 20})
    assert res.status_code == 404


def test_ocr_unknown_project_is_404(client, fake_ocr):
    res = client.post("/api/projects/nope/ocr", json={"page": "1.png", "x": 0, "y": 0, "w": 20, "h": 20})
    assert res.status_code == 404
