"""
Tests for arsgrammatica/lewis_short.py: read_lewis_short(), LewisShortEntry,
and LewisShortLexicon's get()/lookup().

Uses a small hand-built fixture shaped like the real ls-articles.cex file
(verified separately, against the real ~28MB/51,596-row file, to have
exactly this header, exactly 4 columns per row, and never a blank key/entry
-- see lewis_short.py's own module docstring) rather than the real file
itself, which isn't checked into this repo (same convention as every other
CEX corpus this codebase reads: read_ctsdata()'s own tests use a small
hand-built fixture too, not a real downloaded corpus).

Covers: a basic read; every malformed-file error read_lewis_short() can
raise; LewisShortLexicon.get()'s literal exact-only lookup; lookup()'s
three real behaviors -- an exact hit short-circuiting fuzzy matching
entirely, case/diacritic-insensitive matching still counting as exact, and
the fuzzy-ranked fallback (including the homonym-tie case: two keys like
'abdico1'/'abdico2' both scoring identically for the bare lemma 'abdico',
since Lewis & Short's own spelling gives no way to prefer one) -- plus
LewisShortLexicon.__init__()'s duplicate-key check.

Also covers read_lewis_short_from_url()/LewisShortLexicon.from_url(): the
default `url`/timeout actually reach urllib.request.urlopen(), the fetched
body is parsed with the exact same validation as the file-based reader
(a mocked urlopen returning malformed content still raises the right
ValueError), and a custom url/timeout are passed through -- all against a
MOCKED urlopen (monkeypatched), never the real network, since this
sandbox's own network access can't reach shot.holycross.edu at all (see
lewis_short.py's own docstring for read_lewis_short_from_url()). One
`network`-marked test at the bottom of this file hits the REAL published
URL and is skipped by default (same convention as tests/
test_segmentation_live.py's `live` marker for real LM calls) -- run it
with `pytest -m network` from a network that can actually reach the
endpoint, to verify what the mocked tests above can't.
"""

import pytest

from arsgrammatica.lewis_short import (
    LEWIS_SHORT_URL,
    LewisShortEntry,
    LewisShortLexicon,
    read_lewis_short,
    read_lewis_short_from_url,
)

_HEADER = "seq|urn|key|entry"


def _write_raw(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return str(path)


def _fixture_content():
    rows = [
        "1|urn:cite2:hmt:ls.markdown:n0|amo|amo, avi, atum, 1, v. a., to love.",
        "2|urn:cite2:hmt:ls.markdown:n1|abdico1|ab-dico, are, 1, v. a., to disown.",
        "3|urn:cite2:hmt:ls.markdown:n2|abdico2|ab-dico, dixi, dictum, 3, v. a., to abdicate.",
        "4|urn:cite2:hmt:ls.markdown:n3|Aaron|Aaron, indecl. n., a Hebrew name.",
        "5|urn:cite2:hmt:ls.markdown:n4|amodo|a modo, from now on.",
    ]
    return _HEADER + "\n" + "\n".join(rows) + "\n"


def _write_fixture(tmp_path, name="ls-articles.cex"):
    return _write_raw(tmp_path, name, _fixture_content())


# ---------------------------------------------------------------------------
# read_lewis_short()
# ---------------------------------------------------------------------------


def test_reads_every_row_in_file_order(tmp_path):
    path = _write_fixture(tmp_path)
    entries = read_lewis_short(path)

    assert entries == [
        LewisShortEntry(seq=1, urn="urn:cite2:hmt:ls.markdown:n0", key="amo",
                         entry="amo, avi, atum, 1, v. a., to love."),
        LewisShortEntry(seq=2, urn="urn:cite2:hmt:ls.markdown:n1", key="abdico1",
                         entry="ab-dico, are, 1, v. a., to disown."),
        LewisShortEntry(seq=3, urn="urn:cite2:hmt:ls.markdown:n2", key="abdico2",
                         entry="ab-dico, dixi, dictum, 3, v. a., to abdicate."),
        LewisShortEntry(seq=4, urn="urn:cite2:hmt:ls.markdown:n3", key="Aaron",
                         entry="Aaron, indecl. n., a Hebrew name."),
        LewisShortEntry(seq=5, urn="urn:cite2:hmt:ls.markdown:n4", key="amodo",
                         entry="a modo, from now on."),
    ]


def test_custom_delimiter(tmp_path):
    content = "seq;urn;key;entry\n1;urn:cite2:hmt:ls.markdown:n0;amo;to love\n"
    path = _write_raw(tmp_path, "ls.cex", content)
    entries = read_lewis_short(path, delimiter=";")
    assert entries == [LewisShortEntry(seq=1, urn="urn:cite2:hmt:ls.markdown:n0", key="amo", entry="to love")]


def test_empty_file_raises(tmp_path):
    path = _write_raw(tmp_path, "empty.cex", "")
    with pytest.raises(ValueError, match="empty"):
        read_lewis_short(path)


def test_wrong_header_raises(tmp_path):
    content = "seq|urn|headword|text\n1|urn:x|amo|to love\n"
    path = _write_raw(tmp_path, "bad.cex", content)
    with pytest.raises(ValueError, match="header"):
        read_lewis_short(path)


def test_header_only_no_data_rows_raises(tmp_path):
    path = _write_raw(tmp_path, "bad.cex", _HEADER + "\n")
    with pytest.raises(ValueError, match="no data rows"):
        read_lewis_short(path)


def test_wrong_column_count_raises(tmp_path):
    content = _HEADER + "\n1|urn:x|amo\n"  # only 3 columns
    path = _write_raw(tmp_path, "bad.cex", content)
    with pytest.raises(ValueError, match="3 column"):
        read_lewis_short(path)


def test_blank_key_raises(tmp_path):
    content = _HEADER + "\n1|urn:x||to love\n"
    path = _write_raw(tmp_path, "bad.cex", content)
    with pytest.raises(ValueError, match="empty key"):
        read_lewis_short(path)


def test_blank_entry_raises(tmp_path):
    content = _HEADER + "\n1|urn:x|amo|\n"
    path = _write_raw(tmp_path, "bad.cex", content)
    with pytest.raises(ValueError, match="empty entry"):
        read_lewis_short(path)


def test_non_integer_seq_raises(tmp_path):
    content = _HEADER + "\nfirst|urn:x|amo|to love\n"
    path = _write_raw(tmp_path, "bad.cex", content)
    with pytest.raises(ValueError, match="not an integer"):
        read_lewis_short(path)


# ---------------------------------------------------------------------------
# LewisShortLexicon.get()
# ---------------------------------------------------------------------------


def test_get_is_literal_and_exact_only(tmp_path):
    lex = LewisShortLexicon.from_file(_write_fixture(tmp_path))

    assert lex.get("amo").entry.startswith("amo, avi")
    assert lex.get("abdico1") is not None
    # No bare "abdico" key exists (only the numbered homonyms) -- get() is
    # literal, so it must NOT find one via any normalization.
    assert lex.get("abdico") is None
    # get() is case-sensitive, unlike lookup().
    assert lex.get("AMO") is None


def test_duplicate_key_raises_on_construction(tmp_path):
    content = _HEADER + "\n1|urn:x|amo|first.\n2|urn:y|amo|second.\n"
    path = _write_raw(tmp_path, "dup.cex", content)
    entries = read_lewis_short(path)
    with pytest.raises(ValueError, match="duplicate key"):
        LewisShortLexicon(entries)


# ---------------------------------------------------------------------------
# LewisShortLexicon.lookup()
# ---------------------------------------------------------------------------


def test_lookup_exact_match_short_circuits_fuzzy(tmp_path):
    lex = LewisShortLexicon.from_file(_write_fixture(tmp_path))
    matches = lex.lookup("amo")
    assert len(matches) == 1
    assert matches[0].entry.key == "amo"
    assert matches[0].score == 1.0


def test_lookup_is_case_insensitive_and_still_exact(tmp_path):
    lex = LewisShortLexicon.from_file(_write_fixture(tmp_path))
    matches = lex.lookup("Amo")
    assert len(matches) == 1
    assert matches[0].entry.key == "amo"
    assert matches[0].score == 1.0


def test_lookup_is_diacritic_insensitive_and_still_exact(tmp_path):
    lex = LewisShortLexicon.from_file(_write_fixture(tmp_path))
    matches = lex.lookup("amō")  # "amō" -- macron over the o
    assert len(matches) == 1
    assert matches[0].entry.key == "amo"
    assert matches[0].score == 1.0


def test_lookup_bare_homonym_lemma_ties_both_numbered_forms(tmp_path):
    lex = LewisShortLexicon.from_file(_write_fixture(tmp_path))
    matches = lex.lookup("abdico")

    # No bare "abdico" key exists, so this falls into the fuzzy branch --
    # both numbered forms differ from "abdico" only by their trailing
    # digit, so they score identically and both come back, tied for first.
    assert [m.entry.key for m in matches] == ["abdico1", "abdico2"]
    assert matches[0].score == matches[1].score
    assert 0.9 < matches[0].score < 1.0


def test_lookup_typo_falls_back_to_ranked_fuzzy_matches(tmp_path):
    lex = LewisShortLexicon.from_file(_write_fixture(tmp_path))
    matches = lex.lookup("amoo")  # not a real key at all

    assert matches  # something in the fixture should be close enough
    keys = [m.entry.key for m in matches]
    assert keys[0] in ("amodo", "amo")
    # Descending score order.
    scores = [m.score for m in matches]
    assert scores == sorted(scores, reverse=True)
    # Every fuzzy score is a genuine ratio below 1.0 -- distinguishable
    # from an exact hit.
    assert all(0.0 <= s < 1.0 for s in scores)


def test_lookup_respects_limit(tmp_path):
    lex = LewisShortLexicon.from_file(_write_fixture(tmp_path))
    matches = lex.lookup("amoo", limit=1)
    assert len(matches) == 1


def test_lookup_no_match_returns_empty_list(tmp_path):
    lex = LewisShortLexicon.from_file(_write_fixture(tmp_path))
    assert lex.lookup("xyzzyqqqnotlatin") == []


def test_lookup_blank_lemma_raises(tmp_path):
    lex = LewisShortLexicon.from_file(_write_fixture(tmp_path))
    with pytest.raises(ValueError, match="blank"):
        lex.lookup("   ")


def test_lexicon_len_and_iter(tmp_path):
    lex = LewisShortLexicon.from_file(_write_fixture(tmp_path))
    assert len(lex) == 5
    assert {e.key for e in lex} == {"amo", "abdico1", "abdico2", "Aaron", "amodo"}


# ---------------------------------------------------------------------------
# read_lewis_short_from_url() / LewisShortLexicon.from_url() -- mocked
# urlopen, never the real network (see module docstring).
# ---------------------------------------------------------------------------


class _FakeResponse:
    """Minimal stand-in for what urllib.request.urlopen() returns -- a
    context manager whose read() gives back the fetched bytes."""

    def __init__(self, data: bytes):
        self._data = data

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def read(self) -> bytes:
        return self._data


def test_read_lewis_short_from_url_uses_default_url_and_timeout(monkeypatch):
    calls = {}

    def fake_urlopen(url, timeout=None):
        calls["url"] = url
        calls["timeout"] = timeout
        return _FakeResponse(_fixture_content().encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    entries = read_lewis_short_from_url()

    assert calls["url"] == LEWIS_SHORT_URL
    assert calls["timeout"] == 60.0
    assert len(entries) == 5
    assert entries[0].key == "amo"


def test_read_lewis_short_from_url_passes_through_custom_url_and_timeout(monkeypatch):
    def fake_urlopen(url, timeout=None):
        assert url == "https://example.org/ls-articles.cex"
        assert timeout == 5
        return _FakeResponse(_fixture_content().encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    entries = read_lewis_short_from_url("https://example.org/ls-articles.cex", timeout=5)
    assert len(entries) == 5


def test_read_lewis_short_from_url_uses_same_validation_as_the_file_reader(monkeypatch):
    # Wrong header column name ("headword" instead of "key") -- same
    # ValueError _parse_lewis_short_lines() would raise for a local file.
    bad_content = "seq|urn|headword|entry\n1|urn:x|amo|to love\n"

    def fake_urlopen(url, timeout=None):
        return _FakeResponse(bad_content.encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    with pytest.raises(ValueError, match="header"):
        read_lewis_short_from_url()


def test_lexicon_from_url(monkeypatch):
    def fake_urlopen(url, timeout=None):
        return _FakeResponse(_fixture_content().encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    lex = LewisShortLexicon.from_url()
    assert len(lex) == 5
    assert lex.get("amo") is not None
    assert lex.lookup("Amo")[0].score == 1.0


@pytest.mark.network
def test_network_fetch_of_the_real_dictionary():
    """Hits the REAL published URL -- skipped by default (see this file's
    own module docstring); run with `pytest -m network` from a network
    that can actually reach shot.holycross.edu (this sandbox's own network
    access could not, when this test was written -- see lewis_short.py's
    read_lewis_short_from_url() docstring)."""
    lex = LewisShortLexicon.from_url()
    assert len(lex) > 50000
    assert lex.get("amo") is not None
    assert lex.lookup("abdico")[0].entry.key.startswith("abdico")
