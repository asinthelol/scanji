import pytest

from .conftest import box


@pytest.fixture
def project(client, make_project):
    """
    Save a project with the given pages -> bubbles and return its id.
    """

    def make(pages: dict, title: str = "Chapter 1", **settings) -> str:
        pid = make_project(title)
        body = client.get(f"/api/projects/{pid}").json()
        body["pages"] = pages
        if settings:
            body["export"] = settings
        assert client.put(f"/api/projects/{pid}", json=body).status_code == 200
        return pid

    return make


def export(client, pid: str) -> str:
    res = client.get(f"/api/projects/{pid}/export")
    assert res.status_code == 200
    return res.text


def test_export_is_plain_lines_without_numbering(client, project):
    pid = project({"1.png": [box("a", final="Hello"), box("b", final="World")]})
    assert export(client, pid) == "# Chapter 1\n\n## 1.png\nHello\nWorld\n"


def test_export_prefers_final_then_draft_then_suggestion(client, project):
    pid = project(
        {
            "1.png": [
                box("a", final="F", draft="D", suggestion="S"),
                box("b", draft="D", suggestion="S"),
                box("c", suggestion="S"),
            ]
        }
    )
    assert export(client, pid).splitlines()[3:] == ["F", "D", "S"]


def test_export_skips_empty_bubbles_and_empty_pages(client, project):
    pid = project(
        {"1.png": [box("a", final="Hi"), box("b"), box("c", final="   ")], "2.png": [box("d")], "3.png": []}
    )
    text = export(client, pid)
    assert "Hi" in text
    assert "2.png" not in text and "3.png" not in text
    assert "\n\n\n" not in text  # no blank line standing in for an empty bubble


def test_export_trims_whitespace(client, project):
    pid = project({"1.png": [box("a", final="  padded \n")]})
    assert export(client, pid).splitlines()[3] == "padded"


def test_export_lists_pages_in_natural_order(client, project):
    pid = project({"11.png": [box("a", final="eleven")], "2.png": [box("b", final="two")]})
    text = export(client, pid)
    assert text.index("2.png") < text.index("11.png")


def test_custom_heading_templates(client, project):
    pid = project(
        {"1.png": [box("a", final="Hi")]}, title="Vol 2", title_heading="== {title} ==", page_heading="[{page}]"
    )
    assert export(client, pid) == "== Vol 2 ==\n\n[1.png]\nHi\n"


def test_blank_templates_omit_the_heading_lines(client, project):
    pid = project({"1.png": [box("a", final="Hi"), box("b", final="There")]}, title_heading="", page_heading="")
    assert export(client, pid) == "Hi\nThere\n"


def test_templates_without_placeholders_are_used_verbatim(client, project):
    pid = project({"1.png": [box("a", final="Hi")]}, title_heading="SCRIPT", page_heading="---")
    assert export(client, pid) == "SCRIPT\n\n---\nHi\n"


def test_export_is_scoped_to_its_project(client, project):
    a = project({"1.png": [box("a", final="from A")]}, title="A")
    b = project({"1.png": [box("a", final="from B")]}, title="B")
    assert "from A" in export(client, a) and "from B" not in export(client, a)
    assert "from B" in export(client, b)


def test_export_unknown_project_is_404(client):
    assert client.get("/api/projects/nope/export").status_code == 404
