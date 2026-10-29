import pytest

from backend.services.reading_order import reading_order


def R(x, y, w=40, h=40):
    return (x, y, w, h)


# ---- reading order ----


def test_single_row_reads_right_to_left():
    assert reading_order([R(10, 10), R(200, 12), R(400, 8)]) == [2, 1, 0]


def test_stack_reads_top_to_bottom():
    assert reading_order([R(10, 300), R(10, 10), R(10, 150)]) == [1, 2, 0]


def test_aligned_panel_rows_read_row_by_row_right_to_left():
    # 2 columns x 2 rows: 0=left-top 1=left-bottom 2=right-top 3=right-bottom
    assert reading_order([R(100, 10), R(100, 200), R(500, 10), R(500, 200)]) == [2, 0, 3, 1]


def test_tall_right_panel_is_read_before_the_stack_on_its_left():
    right_tall = R(500, 10, 40, 400)
    left_top, left_bottom = R(100, 10), R(100, 300)
    assert reading_order([left_top, left_bottom, right_tall]) == [2, 0, 1]


def test_overlapping_boxes_fall_back_to_a_stable_order():
    assert reading_order([R(0, 0, 100, 100), R(50, 50, 100, 100)]) == [0, 1]


def test_empty_and_single():
    assert reading_order([]) == []
    assert reading_order([R(1, 1)]) == [0]


def test_result_is_a_permutation():
    rects = [R(x, y) for x, y in [(5, 5), (80, 3), (40, 90), (200, 95), (150, 10), (10, 200)]]
    assert sorted(reading_order(rects)) == list(range(len(rects)))


# ---- routes ----


def test_reading_order_route_returns_ids(client):
    boxes = [{"id": "left", "x": 10, "y": 10, "w": 5, "h": 5}, {"id": "right", "x": 300, "y": 10, "w": 5, "h": 5}]
    assert client.post("/api/reading-order", json={"boxes": boxes}).json() == {"ids": ["right", "left"]}


def test_reading_order_of_nothing(client):
    assert client.post("/api/reading-order", json={"boxes": []}).json() == {"ids": []}


@pytest.fixture
def fake_detector(monkeypatch):
    """Replace the RT-DETR model with a recorder returning canned boxes."""
    calls = []

    def detect(img, threshold, include_free):
        calls.append({"size": img.size, "threshold": threshold, "include_free": include_free})
        return [{"x": 1.0, "y": 2.0, "w": 10.0, "h": 12.0, "kind": "text_bubble", "score": 0.9}]

    monkeypatch.setattr("backend.routers.detect.detect_text", detect)
    return calls


def test_detect_runs_on_the_project_page(client, fake_detector, make_project, upload):
    pid = make_project()
    name = upload(pid, "1.png", width=120, height=200)
    res = client.post(f"/api/projects/{pid}/detect", json={"page": name})
    assert res.json()["boxes"][0]["kind"] == "text_bubble"
    assert fake_detector == [{"size": (120, 200), "threshold": 0.5, "include_free": False}]


def test_detect_passes_options_through(client, fake_detector, make_project, upload):
    pid = make_project()
    name = upload(pid)
    client.post(f"/api/projects/{pid}/detect", json={"page": name, "threshold": 0.3, "include_free": True})
    assert fake_detector[0]["threshold"] == 0.3 and fake_detector[0]["include_free"] is True


def test_detect_missing_page_or_project_is_404(client, fake_detector, make_project):
    pid = make_project()
    assert client.post(f"/api/projects/{pid}/detect", json={"page": "nope.png"}).status_code == 404
    assert client.post("/api/projects/nope/detect", json={"page": "1.png"}).status_code == 404
    assert fake_detector == []
