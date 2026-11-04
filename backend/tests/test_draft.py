import anthropic
import httpx
import pytest

from backend.schemas import DraftReq
from backend.services import llm

REPLY = '{"literal": "word for word", "suggestion": "Good morning", "notes": "casual", "flags": ["tone mismatch"]}'


class FakeClient:
    """Stands in for anthropic.Anthropic; records calls and replies with `reply` or raises `error`."""

    def __init__(self, reply: str = REPLY, error: Exception | None = None):
        self.calls: list[dict] = []
        self.reply, self.error = reply, error
        self.messages = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        block = type("Block", (), {"type": "text", "text": self.reply})()
        return type("Msg", (), {"content": [block]})()


@pytest.fixture
def fake(monkeypatch):
    def install(**kwargs) -> FakeClient:
        client = FakeClient(**kwargs)
        monkeypatch.setattr(llm, "get_client", lambda: client)
        return client

    return install


def api_error(cls, status: int):
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return cls("boom", response=httpx.Response(status, request=request), body=None)


# ---- the route ----


def test_draft_returns_the_parsed_fields(client, fake):
    fake()
    res = client.post("/api/draft", json={"ja": "おはよう"})
    assert res.json() == {
        "literal": "word for word",
        "suggestion": "Good morning",
        "notes": "casual",
        "flags": ["tone mismatch"],
    }


def test_prompt_contains_everything_the_model_needs(client, fake):
    sdk = fake()
    client.post(
        "/api/draft",
        json={
            "ja": "おはよう",
            "draft": "Morning!",
            "context": "School comedy",
            "glossary": [{"ja": "先輩", "en": "senpai", "note": "keep honorific"}, {"ja": "春平", "en": "Shunpei"}],
            "neighbors": ["前の台詞", "次の台詞"],
        },
    )
    (call,) = sdk.calls
    prompt = call["messages"][0]["content"]
    assert "School comedy" in prompt
    assert "- 先輩 = senpai (keep honorific)" in prompt
    assert "- 春平 = Shunpei\n" in prompt
    assert "- 前の台詞" in prompt and "- 次の台詞" in prompt
    assert "おはよう" in prompt and "Morning!" in prompt
    assert "glossary exactly" in call["system"]
    assert call["model"] == llm.MODEL


def test_empty_optional_fields_are_marked_none(client, fake):
    sdk = fake()
    client.post("/api/draft", json={"ja": "おはよう"})
    assert sdk.calls[0]["messages"][0]["content"].count("(none)") == 4  # context, glossary, neighbors, draft


def test_draft_requires_japanese_text(client, fake):
    fake()
    assert client.post("/api/draft", json={}).status_code == 422


def test_non_json_reply_falls_back_to_plain_suggestion(client, fake):
    fake(reply="Good morning!")
    body = client.post("/api/draft", json={"ja": "おはよう"}).json()
    assert body["suggestion"] == "Good morning!"
    assert body["notes"] == "model returned non-JSON"
    assert body["flags"] == []


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (api_error(anthropic.AuthenticationError, 401), 500),
        (api_error(anthropic.RateLimitError, 429), 429),
        (anthropic.APIConnectionError(request=httpx.Request("POST", "https://x")), 502),
        (api_error(anthropic.InternalServerError, 500), 502),
    ],
)
def test_api_failures_become_clear_http_errors(client, fake, error, status):
    fake(error=error)
    res = client.post("/api/draft", json={"ja": "おはよう"})
    assert res.status_code == status
    assert res.json()["detail"]  # a message the UI can show in a toast


def test_missing_api_key_is_reported(client, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(llm, "_client", None)
    res = client.post("/api/draft", json={"ja": "おはよう"})
    assert res.status_code == 500
    assert "ANTHROPIC_API_KEY" in res.json()["detail"]


# ---- parse_reply ----


def test_parse_plain_json():
    assert llm.parse_reply(REPLY)["suggestion"] == "Good morning"


def test_parse_strips_code_fences():
    assert llm.parse_reply(f"```json\n{REPLY}\n```")["flags"] == ["tone mismatch"]


def test_parse_ignores_prose_around_the_json():
    assert llm.parse_reply(f"Sure, here you go:\n{REPLY}\nHope that helps!")["literal"] == "word for word"


@pytest.mark.parametrize(
    ("flags", "expected"),
    [("one problem", ["one problem"]), (None, []), ({"a": 1}, []), (["a", "", None, 3], ["a", "3"]), ([], [])],
)
def test_parse_normalizes_flags_to_a_list_of_strings(flags, expected):
    import json

    assert llm.parse_reply(json.dumps({"suggestion": "x", "flags": flags}))["flags"] == expected


def test_parse_fills_missing_keys_with_empty_strings():
    assert llm.parse_reply('{"suggestion": "x"}') == {"literal": "", "suggestion": "x", "notes": "", "flags": []}


@pytest.mark.parametrize("text", ["plain text", "[1, 2]", '{"broken": ', "", "{}}{"])
def test_parse_falls_back_on_anything_unusable(text):
    out = llm.parse_reply(text)
    assert out["notes"] == "model returned non-JSON"
    assert out["suggestion"] == text


def test_build_prompt_handles_glossary_without_notes():
    prompt = llm.build_prompt(DraftReq(ja="x", glossary=[{"ja": "a", "en": "b"}]))
    assert "- a = b\n" in prompt and "()" not in prompt


# ---- replies cut off by the token limit ----

CUT_IN_FLAGS = (
    '```json\n{"literal": "word for word", "suggestion": "Good morning", "notes": "casual, \\"quoted\\" bit", '
    '"flags": ["tone mismatch", "omits the \\"honorific\\"", "a flag that never fini'
)


def test_cut_off_in_the_flags_keeps_everything_that_finished():
    out = llm.parse_reply(CUT_IN_FLAGS)
    assert out["literal"] == "word for word"
    assert out["suggestion"] == "Good morning"
    assert out["notes"].startswith('casual, "quoted" bit')  # escapes are decoded
    assert out["notes"].endswith("[The reply was cut off, so this may be incomplete.]")
    assert out["flags"] == ["tone mismatch", 'omits the "honorific"']  # the unfinished flag is dropped


def test_cut_off_in_the_notes_keeps_literal_and_suggestion():
    out = llm.parse_reply('{"literal": "word for word", "suggestion": "Good morning", "notes": "this goes on and on')
    assert (out["literal"], out["suggestion"]) == ("word for word", "Good morning")
    assert out["notes"] == "[The reply was cut off, so this may be incomplete.]"
    assert out["flags"] == []


def test_cut_off_before_the_suggestion_falls_back_to_plain_text():
    text = '{"literal": "word for word", "suggestion": "Good mor'
    out = llm.parse_reply(text)
    assert out["notes"] == "model returned non-JSON" and out["suggestion"] == text


def test_keys_inside_a_notes_string_are_not_mistaken_for_fields():
    text = '{"literal": "x", "suggestion": "real", "notes": "he said \\"suggestion\\": \\"fake\\" and then"'
    assert llm.parse_reply(text)["suggestion"] == "real"


def test_cut_off_reply_still_renders_through_the_route(client, fake):
    fake(reply=CUT_IN_FLAGS)
    body = client.post("/api/draft", json={"ja": "おはよう"}).json()
    assert body["suggestion"] == "Good morning" and body["flags"][0] == "tone mismatch"


def test_the_reply_budget_leaves_room_for_long_notes(client, fake):
    sdk = fake()
    client.post("/api/draft", json={"ja": "おはよう"})
    assert sdk.calls[0]["max_tokens"] >= 2000
