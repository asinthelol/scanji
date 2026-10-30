import pytest

from .conftest import box


@pytest.fixture
def chapter(client, make_project, make_chapter, set_pages):
    """
    Save a chapter with the given pages -> bubbles and return (project id, chapter id).
    """

    def make(pages: dict, title: str = "Series", chapter_title: str = "Chapter 1", **settings) -> tuple[str, str]:
        pid = make_project(title)
        cid = make_chapter(pid, chapter_title)
        set_pages(pid, cid, pages)
        if settings:
            body = client.get(f"/api/projects/{pid}").json()
            body["export"] = settings
            assert client.put(f"/api/projects/{pid}", json=body).status_code == 200
        return pid, cid

    return make


def export(client, ids: tuple[str, str]) -> str:
    pid, cid = ids
    res = client.get(f"/api/projects/{pid}/chapters/{cid}/export")
    assert res.status_code == 200
    return res.text


def test_export_is_plain_lines_without_numbering(client, chapter):
    ids = chapter({"1.png": [box("a", final="Hello"), box("b", final="World")]})
    assert export(client, ids) == "# Series - Chapter 1\n\n## 1.png\nHello\nWorld\n"


def test_export_prefers_final_then_draft_then_suggestion(client, chapter):
    ids = chapter(
        {
            "1.png": [
                box("a", final="F", draft="D", suggestion="S"),
                box("b", draft="D", suggestion="S"),
                box("c", suggestion="S"),
            ]
        }
    )
    assert export(client, ids).splitlines()[3:] == ["F", "D", "S"]


def test_export_skips_empty_bubbles_and_empty_pages(client, chapter):
    ids = chapter({"1.png": [box("a", final="Hi"), box("b"), box("c", final="   ")], "2.png": [box("d")], "3.png": []})
    text = export(client, ids)
    assert "Hi" in text
    assert "2.png" not in text and "3.png" not in text
    assert "\n\n\n" not in text  # no blank line standing in for an empty bubble


def test_export_trims_whitespace(client, chapter):
    ids = chapter({"1.png": [box("a", final="  padded \n")]})
    assert export(client, ids).splitlines()[3] == "padded"


def test_export_lists_pages_in_natural_order(client, chapter):
    ids = chapter({"11.png": [box("a", final="eleven")], "2.png": [box("b", final="two")]})
    text = export(client, ids)
    assert text.index("2.png") < text.index("11.png")


def test_custom_heading_templates(client, chapter):
    ids = chapter(
        {"1.png": [box("a", final="Hi")]},
        title="Vol 2",
        chapter_title="The Bus",
        title_heading="== {title} / {chapter} ==",
        page_heading="[{page}]",
    )
    assert export(client, ids) == "== Vol 2 / The Bus ==\n\n[1.png]\nHi\n"


def test_blank_templates_omit_the_heading_lines(client, chapter):
    ids = chapter({"1.png": [box("a", final="Hi"), box("b", final="There")]}, title_heading="", page_heading="")
    assert export(client, ids) == "Hi\nThere\n"


def test_templates_without_placeholders_are_used_verbatim(client, chapter):
    ids = chapter({"1.png": [box("a", final="Hi")]}, title_heading="SCRIPT", page_heading="---")
    assert export(client, ids) == "SCRIPT\n\n---\nHi\n"


def test_export_only_contains_its_own_chapter(client, make_project, make_chapter, set_pages):
    pid = make_project()
    one, two = make_chapter(pid, "Chapter 1"), make_chapter(pid, "Chapter 2")
    set_pages(pid, one, {"1.png": [box("a", final="from one")]})
    set_pages(pid, two, {"1.png": [box("a", final="from two")]})
    assert "from one" in export(client, (pid, one)) and "from two" not in export(client, (pid, one))
    assert "from two" in export(client, (pid, two))


def test_export_is_scoped_to_its_project(client, chapter):
    a = chapter({"1.png": [box("a", final="from A")]}, title="A")
    b = chapter({"1.png": [box("a", final="from B")]}, title="B")
    assert "from A" in export(client, a) and "from B" not in export(client, a)
    assert "from B" in export(client, b)


def test_export_unknown_project_or_chapter_is_404(client, workspace):
    pid, _ = workspace
    assert client.get("/api/projects/nope/chapters/chapter-1/export").status_code == 404
    assert client.get(f"/api/projects/{pid}/chapters/nope/export").status_code == 404
