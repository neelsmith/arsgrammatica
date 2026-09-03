"""
Tests for pipeline.py's analyze_ctsdata() -- the convenience wrapper that
reads a whole `#!ctsdata` (CEX) source file straight into analyze_sources(),
so a caller with a file on disk doesn't need to call read_ctsdata() and
analyze_sources() separately by hand.

Mirrors test_analyze_string.py's DummyLM two-stage pattern (one
segmentation call, then one SentenceAnalysis call per sentence), but
starting from a file written to `tmp_path` (same convention
test_ctsdata.py uses for read_ctsdata() itself) rather than an in-memory
string or CitedText list.

Three things worth checking that no other test exercises together:
  - reading a real CEX file and analyzing every passage in it end to end,
    with citations flowing through from the file's own urns;
  - the `delimiter` argument is actually passed through to read_ctsdata();
  - a malformed/missing file raises read_ctsdata()'s own error WITHOUT
    ever touching the LM (no DummyLM configured for that test).
"""

import dspy
import pytest
from dspy.utils.dummies import DummyLM

from arsgrammatica import analyze_ctsdata


def _write(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content)
    return str(path)


_ONE_PASSAGE_CONTENT = (
    "#!ctsdata\n"
    "urn|text\n"
    "urn:cts:compnov:test.aeneid:1.1|arma virumque cano.\n"
)

_ONE_SENTENCE_SEG = {
    "reasoning": "One passage, one sentence.",
    "sentences": [
        {"tokens": [
            {"id": "t0", "text": "arma", "citation": "urn:cts:compnov:test.aeneid:1.1"},
            {"id": "t1", "text": "virumque", "citation": "urn:cts:compnov:test.aeneid:1.1"},
            {"id": "t2", "text": "cano", "citation": "urn:cts:compnov:test.aeneid:1.1"},
            {"id": "t3", "text": ".", "citation": "urn:cts:compnov:test.aeneid:1.1"},
        ]},
    ],
}

_ONE_SENTENCE_ANALYSIS = {
    "reasoning": "cano is the main verb; arma and virumque are its objects.",
    "verbalunits": [
        {"id": "t2", "syntactic_type": "independent", "semantic_type": "transitive active"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "arma", "tokentype": "lexical",
         "relatedtoken1": "t2", "relationship1": "direct object"},
        {"id": "t1", "token": "virumque", "tokentype": "lexical",
         "relatedtoken1": "t2", "relationship1": "direct object"},
        {"id": "t2", "token": "cano", "tokentype": "lexical", "verbalunitid": "t2"},
        {"id": "t3", "token": ".", "tokentype": "punctuation"},
    ],
}

_TWO_PASSAGES_CONTENT = (
    "#!ctsdata\n"
    "urn|text\n"
    "urn:cts:compnov:test.example:1|ita.\n"
    "urn:cts:compnov:test.example:2|vale.\n"
)

_TWO_SENTENCES_SEG = {
    "reasoning": "Two passages, one sentence each.",
    "sentences": [
        {"tokens": [{"id": "t0", "text": "ita", "citation": "urn:cts:compnov:test.example:1"},
                     {"id": "t1", "text": ".", "citation": "urn:cts:compnov:test.example:1"}]},
        {"tokens": [{"id": "t2", "text": "vale", "citation": "urn:cts:compnov:test.example:2"},
                     {"id": "t3", "text": ".", "citation": "urn:cts:compnov:test.example:2"}]},
    ],
}

_ITA_ANALYSIS = {
    "reasoning": "No finite verb in this fragment; ita is an adverb, no verbal units.",
    "verbalunits": [],
    "tokengraph": [
        {"id": "t0", "token": "ita", "tokentype": "lexical"},
        {"id": "t1", "token": ".", "tokentype": "punctuation"},
    ],
}

_VALE_ANALYSIS = {
    "reasoning": "vale is an imperative verbal expression.",
    "verbalunits": [
        {"id": "t2", "syntactic_type": "independent", "semantic_type": "intransitive"},
    ],
    "tokengraph": [
        {"id": "t2", "token": "vale", "tokentype": "lexical", "verbalunitid": "t2"},
        {"id": "t3", "token": ".", "tokentype": "punctuation"},
    ],
}


def test_reads_and_analyzes_a_single_passage_file(tmp_path):
    dspy.configure(lm=DummyLM([_ONE_SENTENCE_SEG, _ONE_SENTENCE_ANALYSIS]))
    path = _write(tmp_path, "corpus.cex", _ONE_PASSAGE_CONTENT)

    sentences, results = analyze_ctsdata(path)

    assert len(sentences) == 1
    assert len(results) == 1
    tokens = sentences[0].tokens
    assert [t.id for t in tokens] == ["t0", "t1", "t2", "t3"]
    assert all(t.citation == "urn:cts:compnov:test.aeneid:1.1" for t in tokens)
    assert results[0].verbalunits[0].id == "t2"


def test_analyzes_every_passage_in_file_order(tmp_path):
    dspy.configure(lm=DummyLM([_TWO_SENTENCES_SEG, _ITA_ANALYSIS, _VALE_ANALYSIS]))
    path = _write(tmp_path, "corpus.cex", _TWO_PASSAGES_CONTENT)

    sentences, results = analyze_ctsdata(path)

    assert len(sentences) == 2
    assert len(results) == 2
    assert sentences[0].tokens[0].citation == "urn:cts:compnov:test.example:1"
    assert sentences[1].tokens[0].citation == "urn:cts:compnov:test.example:2"
    assert results[0].verbalunits == []
    assert results[1].verbalunits[0].id == "t2"


def test_custom_delimiter_is_passed_through_to_read_ctsdata(tmp_path):
    content = (
        "#!ctsdata\n"
        "urn;text\n"
        "urn:cts:compnov:test.example:1;vale.\n"
    )
    path = _write(tmp_path, "corpus.cex", content)
    # This is a single-passage file, so segmentation restarts token
    # numbering at t0/t1 -- _VALE_ANALYSIS's ids (t2/t3) don't apply here,
    # so a fresh analysis fixture matching THIS test's own token ids is
    # needed rather than reusing it.
    dspy.configure(lm=DummyLM([
        {
            "reasoning": "One passage, one sentence.",
            "sentences": [
                {"tokens": [{"id": "t0", "text": "vale", "citation": "urn:cts:compnov:test.example:1"},
                             {"id": "t1", "text": ".", "citation": "urn:cts:compnov:test.example:1"}]},
            ],
        },
        {
            "reasoning": "vale is an imperative verbal expression.",
            "verbalunits": [
                {"id": "t0", "syntactic_type": "independent", "semantic_type": "intransitive"},
            ],
            "tokengraph": [
                {"id": "t0", "token": "vale", "tokentype": "lexical", "verbalunitid": "t0"},
                {"id": "t1", "token": ".", "tokentype": "punctuation"},
            ],
        },
    ]))

    sentences, results = analyze_ctsdata(path, delimiter=";")

    assert len(sentences) == 1
    assert sentences[0].tokens[0].citation == "urn:cts:compnov:test.example:1"
    assert results[0].verbalunits[0].id == "t0"


def test_missing_file_raises_without_touching_the_lm(tmp_path):
    # No dspy.configure() at all -- if this reached analyze_sources(), it
    # would fail for lack of a configured LM instead of the FileNotFoundError
    # this test actually expects, so an unexpected LM call would surface as
    # a different, more confusing failure.
    missing_path = str(tmp_path / "does_not_exist.cex")
    with pytest.raises(FileNotFoundError):
        analyze_ctsdata(missing_path)


def test_malformed_file_raises_without_touching_the_lm(tmp_path):
    path = _write(tmp_path, "bad.cex", "not a ctsdata file at all\n")
    with pytest.raises(ValueError, match=r"ctsdata"):
        analyze_ctsdata(path)
