import pytest

from backend.services import dictionary

TAGS = {"v1": "Ichidan verb", "v5k": "Godan verb with 'ku' ending", "n": "noun (common) (futsuumeishi)", "adj-i": "adjective (keiyoushi)"}


def word(id, kanji, kana, glosses, pos="n", common=True):
    """
    A JMdict-simplified entry; `glosses` is a list of senses, each a list of gloss strings.
    """
    return {
        "id": str(id),
        "kanji": [{"text": k, "common": common} for k in kanji],
        "kana": [{"text": k, "common": common} for k in kana],
        "sense": [{"partOfSpeech": [pos], "gloss": [{"lang": "eng", "text": g} for g in sense]} for sense in glosses],
    }


WORDS = [
    word(1, ["食べる"], ["たべる"], [["to eat"]], "v1"),
    word(2, ["飲む"], ["のむ"], [["to drink"]], "v1"),
    word(3, [], ["ドリンク"], [["drink"]]),
    word(4, ["遣る"], ["やる"], [["to do"], ["to drink"]], "v1", common=False),  # "drink" only in a later sense
    word(5, ["行く"], ["いく"], [["to go"]], "v5k"),
    word(6, ["高い"], ["たかい"], [["high", "tall"]], "adj-i"),
    word(7, ["珈琲"], ["コーヒー"], [["coffee"]]),
    word(8, ["猫缶"], ["ねこかん"], [["cat food"]]),
]


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """
    A temp database path and a fresh state.
    """
    monkeypatch.setattr(dictionary, "DB_PATH", tmp_path / "dictionary" / "jmdict.db")
    monkeypatch.setattr(dictionary, "_state", {"status": "missing", "message": ""})


@pytest.fixture
def ready():
    dictionary.build_db({"tags": TAGS, "words": WORDS}, dictionary.DB_PATH)


@pytest.fixture
def no_download(monkeypatch):
    """
    Replace the background thread, recording how often a download would have started.
    """
    starts = []

    class FakeThread:
        def __init__(self, target, daemon):
            pass

        def start(self):
            starts.append(1)

    monkeypatch.setattr(dictionary.threading, "Thread", FakeThread)
    return starts


def first_forms(result):
    return [(e["kanji"] or e["kana"])[0] for e in result["entries"]]


# ---- normalizing ----


@pytest.mark.parametrize(
    ("raw", "folded"),
    [("コーヒー", "こーひー"), ("ｺｰﾋｰ", "こーひー"), ("  Drink ", "drink"), ("ＡＢＣ", "abc"), ("食べる", "食べる")],
)
def test_normalize(raw, folded):
    assert dictionary.normalize(raw) == folded


# ---- searching ----


def test_finds_by_kanji_reading_and_katakana(ready):
    assert first_forms(dictionary.lookup("食べる")) == ["食べる"]
    assert first_forms(dictionary.lookup("たべる")) == ["食べる"]
    assert first_forms(dictionary.lookup("コーヒー")) == ["珈琲"]
    assert first_forms(dictionary.lookup("こーひー")) == ["珈琲"]


def test_entries_carry_forms_senses_and_readable_part_of_speech(ready):
    (entry,) = dictionary.lookup("食べる")["entries"]
    assert entry["kanji"] == ["食べる"] and entry["kana"] == ["たべる"]
    assert entry["senses"] == [{"pos": ["Ichidan verb"], "gloss": ["to eat"]}]
    assert entry["common"] is True


def test_english_search_ignores_the_leading_to(ready):
    assert first_forms(dictionary.lookup("eat")) == ["食べる"]
    assert first_forms(dictionary.lookup("to eat")) == ["食べる"]
    assert first_forms(dictionary.lookup("EAT")) == ["食べる"]


def test_english_search_ranks_first_sense_matches_before_later_senses(ready):
    forms = first_forms(dictionary.lookup("drink"))
    assert set(forms[:2]) == {"飲む", "ドリンク"}
    assert forms[2] == "遣る"  # only its second sense says "to drink"


def test_exact_matches_come_before_longer_ones(ready):
    assert first_forms(dictionary.lookup("high"))[0] == "高い"
    forms = first_forms(dictionary.lookup("の"))  # prefix of のむ
    assert forms == ["飲む"]


def test_no_match_gives_no_entries(ready):
    assert dictionary.lookup("zzzz")["entries"] == []


def test_blank_query_gives_no_entries(ready):
    assert dictionary.lookup("   ")["entries"] == []


def test_results_are_capped(tmp_path):
    many = [word(i, [], [f"あ{i}"], [[f"thing {i}"]]) for i in range(1, dictionary.MAX_ENTRIES + 20)]
    dictionary.build_db({"tags": TAGS, "words": many}, dictionary.DB_PATH)
    assert len(dictionary.lookup("あ")["entries"]) == dictionary.MAX_ENTRIES


# ---- words without an entry of their own ----


@pytest.mark.parametrize(
    ("conjugated", "expected", "stem"),
    [("食べた", "食べる", "食べ"), ("食べさせられた", "食べる", "食べ"), ("行かない", "行く", "行"), ("高かった", "高い", "高")],
)
def test_conjugated_forms_find_their_dictionary_form(ready, conjugated, expected, stem):
    result = dictionary.lookup(conjugated)
    assert result["fallback"] == "inflection" and result["stem"] == stem
    assert expected in first_forms(result)


def test_unknown_japanese_falls_back_to_words_that_start_the_same(ready):
    result = dictionary.lookup("猫缶詰め")
    assert (result["fallback"], result["stem"]) == ("prefix", "猫缶")
    assert first_forms(result) == ["猫缶"]


def test_found_words_do_not_use_a_fallback(ready):
    assert dictionary.lookup("食べる")["fallback"] == ""


def test_english_never_falls_back(ready):
    result = dictionary.lookup("eaten")  # would match the "ea" start of "eat" if it did
    assert result["entries"] == [] and result["fallback"] == ""


# ---- building ----


def test_build_replaces_the_old_database_and_leaves_no_partial_file(ready):
    dictionary.build_db({"tags": TAGS, "words": WORDS[:1]}, dictionary.DB_PATH)
    assert first_forms(dictionary.lookup("飲む")) == []
    assert [p.name for p in dictionary.DB_PATH.parent.iterdir()] == ["jmdict.db"]


def test_failed_build_is_not_mistaken_for_a_finished_one():
    broken = {"tags": TAGS, "words": [WORDS[0], {"id": "9"}]}  # second entry has no senses
    with pytest.raises(KeyError):
        dictionary.build_db(broken, dictionary.DB_PATH)
    assert not dictionary.DB_PATH.exists()


# ---- first-run setup ----


def test_first_lookup_starts_one_background_download(no_download):
    first = dictionary.lookup("食べる")
    assert first["status"] == "downloading" and first["entries"] == []
    dictionary.lookup("食べる")
    dictionary.lookup("飲む")
    assert len(no_download) == 1  # polling must not start more downloads


def test_setup_downloads_and_indexes(monkeypatch):
    monkeypatch.setattr(dictionary, "_download_latest", lambda: {"tags": TAGS, "words": WORDS})
    dictionary._prepare()
    assert dictionary.status()["status"] == "ready"
    assert first_forms(dictionary.lookup("食べる")) == ["食べる"]


def test_a_failed_download_reports_the_error_and_is_retried(monkeypatch, no_download):
    def offline():
        raise OSError("no network")

    monkeypatch.setattr(dictionary, "_download_latest", offline)
    dictionary._prepare()
    assert dictionary._state["status"] == "error"
    assert "no network" in dictionary._state["message"]
    assert not dictionary.DB_PATH.exists()

    assert dictionary.status()["status"] == "downloading"  # the next lookup tries again
    assert len(no_download) == 1


def test_existing_data_is_used_without_downloading(ready, no_download):
    assert dictionary.status()["status"] == "ready"
    assert no_download == []


# ---- the route ----


def test_route_returns_entries(client, ready):
    body = client.get("/api/dictionary", params={"q": "食べる"}).json()
    assert body["status"] == "ready"
    assert body["entries"][0]["senses"][0]["gloss"] == ["to eat"]
    assert body["fallback"] == "" and body["stem"] == ""


def test_route_without_a_query_is_empty(client, ready):
    assert client.get("/api/dictionary").json()["entries"] == []


def test_route_reports_progress_while_setting_up(client, no_download):
    body = client.get("/api/dictionary", params={"q": "食べる"}).json()
    assert body["status"] == "downloading" and body["entries"] == [] and body["message"]
