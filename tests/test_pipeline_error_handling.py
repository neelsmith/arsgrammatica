"""
Tests for pipeline.py's analyze_sources() -- specifically its
`on_sentence_error` parameter, added so a caller wide enough to analyze
many passages in one run (see utilities/analyze_ctsdata_to_files.py's own
use of it) can survive one sentence's own SentenceAnalysis call failing
outright -- even after token_budget.analyze_with_retry()'s own retries are
exhausted -- instead of the whole analyze_sources() call raising and
losing every OTHER sentence along with it.

`analyze_with_retry()` itself is monkeypatched here (not driven through a
real DummyLM failure) since the exact SHAPE of what it might raise doesn't
matter to analyze_sources() at all -- only that raising ANYTHING, for
exactly one sentence, is caught and reported (via the callback) rather than
propagated when `on_sentence_error` is given, and still propagates
immediately -- this function's ORIGINAL, unaffected behavior -- when it's
not. Named test_pipeline_error_handling.py rather than test_pipeline.py for
the same reason test_pipeline_selection.py isn't either -- see that file's
own docstring.

Citations here ("ex.1"/"ex.2") are deliberately not CTS URNs -- same
convention test_pipeline_selection.py itself uses -- so
assign_passage_scoped_ids() leaves every token's bare segmentation id
("t0"/"t1"/...) untouched, keeping the canned SentenceAnalysis fixture
below simple.
"""

import dspy
import pytest
from dspy.utils.dummies import DummyLM

import arsgrammatica.pipeline as pipeline_module
from arsgrammatica import analyze_sources
from arsgrammatica.models import CitedText

_TWO_SENTENCE_SEG = {
    "reasoning": "Two passages, one sentence each.",
    "sentences": [
        {"tokens": [{"id": "t0", "text": "ita", "citation": "ex.1"},
                     {"id": "t1", "text": ".", "citation": "ex.1"}]},
        {"tokens": [{"id": "t2", "text": "vale", "citation": "ex.2"},
                     {"id": "t3", "text": ".", "citation": "ex.2"}]},
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

_CITED_TEXTS = [
    CitedText(citation="ex.1", text="ita."),
    CitedText(citation="ex.2", text="vale."),
]


def test_on_sentence_error_skips_the_failing_sentence_and_keeps_the_rest(monkeypatch):
    real_analyze_with_retry = pipeline_module.analyze_with_retry

    def flaky_analyze_with_retry(*, passage, tokens):
        # ex.1's sentence raises before ever reaching a real analyze()
        # call at all -- so DummyLM's own canned-answer list below only
        # ever needs to cover the segmentation call plus ex.2's own
        # SentenceAnalysis call, not one for ex.1 too.
        if tokens and tokens[0].citation == "ex.1":
            raise RuntimeError("simulated LM failure for ex.1")
        return real_analyze_with_retry(passage=passage, tokens=tokens)

    monkeypatch.setattr(pipeline_module, "analyze_with_retry", flaky_analyze_with_retry)
    dspy.configure(lm=DummyLM([_TWO_SENTENCE_SEG, _VALE_ANALYSIS]))

    caught = []
    sentences, results = analyze_sources(
        _CITED_TEXTS,
        on_sentence_error=lambda sentence, exc: caught.append((sentence, exc)),
    )

    # Only ex.2's sentence survives -- ex.1's is left out of BOTH returned
    # lists (they stay the same length as each other), not padded with a
    # placeholder.
    assert len(sentences) == 1
    assert len(results) == 1
    assert sentences[0].tokens[0].citation == "ex.2"
    assert results[0].verbalunits[0].id == "t2"

    assert len(caught) == 1
    failed_sentence, exc = caught[0]
    assert failed_sentence.tokens[0].citation == "ex.1"
    assert isinstance(exc, RuntimeError)
    assert "simulated LM failure for ex.1" in str(exc)


def test_every_sentence_can_fail_leaving_both_lists_empty(monkeypatch):
    def always_fails(*, passage, tokens):
        raise RuntimeError("boom")

    monkeypatch.setattr(pipeline_module, "analyze_with_retry", always_fails)
    dspy.configure(lm=DummyLM([_TWO_SENTENCE_SEG]))

    caught = []
    sentences, results = analyze_sources(
        _CITED_TEXTS,
        on_sentence_error=lambda sentence, exc: caught.append((sentence, exc)),
    )

    assert sentences == []
    assert results == []
    assert len(caught) == 2
    assert [c[0].tokens[0].citation for c in caught] == ["ex.1", "ex.2"]


def test_without_on_sentence_error_a_failure_still_propagates_immediately(monkeypatch):
    # Default behavior (on_sentence_error=None) is exactly what it always
    # was: existing callers (analyze_string(), analyze_selected_passages(),
    # analyze_ctsdata(), syntaxer_main.py, every marimo notebook) that
    # don't pass this parameter must keep seeing the real exception right
    # away, not have it silently swallowed.
    def always_fails(*, passage, tokens):
        raise RuntimeError("boom")

    monkeypatch.setattr(pipeline_module, "analyze_with_retry", always_fails)
    dspy.configure(lm=DummyLM([_TWO_SENTENCE_SEG]))

    with pytest.raises(RuntimeError, match="boom"):
        analyze_sources(_CITED_TEXTS)
