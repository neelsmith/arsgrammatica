"""
Tests for pipeline.py's analyze_selected_passages() -- selects a subset of
a CitedText list by passage id (CitedText.citation) and runs exactly that
subset through analyze_sources(), the same way marimo/latin_syntaxer_ctsdata.py's
own `selected_rows` cell filters ctsdata_rows before calling
analyze_sources() directly.

Named test_pipeline_selection.py rather than test_pipeline.py for the same
reason test_analyze_string.py isn't named that either -- see that file's own
docstring: there's a pre-pytest-suite script literally named test_pipeline.py
that this whole tests/ directory superseded, and reusing the name invites
confusion.

Three things worth checking, mirroring test_analyze_string.py's DummyLM
two-stage pattern (one segmentation call, then one SentenceAnalysis call per
sentence):
  - selecting a subset analyzes only that subset, and skips the rest;
  - selection follows `cited_texts`' OWN order, not `passage_ids`' order --
    the ordering guarantee this function exists to provide, matching the
    notebook's own documented rationale (segment_sources() treats
    consecutive sources as potentially sharing a sentence, so an
    out-of-file-order source list could segment incorrectly);
  - a passage id with no matching citation raises ValueError naming it,
    without calling the LM at all.
"""

import dspy
import pytest
from dspy.utils.dummies import DummyLM

from arsgrammatica import analyze_selected_passages
from arsgrammatica.models import CitedText

_CITED_TEXTS = [
    CitedText(citation="ex.1", text="arma virumque cano."),
    CitedText(citation="ex.2", text="ita."),
    CitedText(citation="ex.3", text="vale."),
]

_SEG_EX1_ONLY = {
    "reasoning": "One selected passage, one sentence.",
    "sentences": [
        {"tokens": [
            {"id": "t0", "text": "arma", "citation": "ex.1"},
            {"id": "t1", "text": "virumque", "citation": "ex.1"},
            {"id": "t2", "text": "cano", "citation": "ex.1"},
            {"id": "t3", "text": ".", "citation": "ex.1"},
        ]},
    ],
}

_ANALYSIS_EX1 = {
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

# Two selected passages (ex.1, ex.3) out of three, requested out of file
# order ("ex.3" before "ex.1") -- selection must still follow _CITED_TEXTS'
# own order, so the segmentation call sees ex.1's tokens before ex.3's.
_SEG_EX1_AND_EX3 = {
    "reasoning": "Two selected passages, each one sentence, in file order.",
    "sentences": [
        {"tokens": [
            {"id": "t0", "text": "arma", "citation": "ex.1"},
            {"id": "t1", "text": "virumque", "citation": "ex.1"},
            {"id": "t2", "text": "cano", "citation": "ex.1"},
            {"id": "t3", "text": ".", "citation": "ex.1"},
        ]},
        {"tokens": [
            {"id": "t4", "text": "vale", "citation": "ex.3"},
            {"id": "t5", "text": ".", "citation": "ex.3"},
        ]},
    ],
}

_ANALYSIS_EX3 = {
    "reasoning": "vale is an imperative verbal expression.",
    "verbalunits": [
        {"id": "t4", "syntactic_type": "independent", "semantic_type": "intransitive"},
    ],
    "tokengraph": [
        {"id": "t4", "token": "vale", "tokentype": "lexical", "verbalunitid": "t4"},
        {"id": "t5", "token": ".", "tokentype": "punctuation"},
    ],
}


def test_selecting_a_subset_analyzes_only_that_subset():
    dspy.configure(lm=DummyLM([_SEG_EX1_ONLY, _ANALYSIS_EX1]))

    sentences, results = analyze_selected_passages(["ex.1"], _CITED_TEXTS)

    assert len(sentences) == 1
    assert len(results) == 1
    assert all(t.citation == "ex.1" for t in sentences[0].tokens)
    assert results[0].verbalunits[0].id == "t2"


def test_selection_follows_cited_texts_order_not_passage_ids_order():
    dspy.configure(lm=DummyLM([_SEG_EX1_AND_EX3, _ANALYSIS_EX1, _ANALYSIS_EX3]))

    # Deliberately out of file order: ex.3 requested before ex.1.
    sentences, results = analyze_selected_passages(["ex.3", "ex.1"], _CITED_TEXTS)

    assert len(sentences) == 2
    assert len(results) == 2
    # ex.1 still comes first, matching _CITED_TEXTS' own order, not the
    # order the ids were requested in.
    assert sentences[0].tokens[0].citation == "ex.1"
    assert sentences[1].tokens[0].citation == "ex.3"
    assert results[0].verbalunits[0].id == "t2"
    assert results[1].verbalunits[0].id == "t4"


def test_unknown_passage_id_raises_without_calling_the_lm():
    # No DummyLM configured at all -- if this reached analyze_sources(), it
    # would raise for lack of a configured LM instead of the ValueError
    # this test actually expects, so an unexpected LM call would surface
    # here as a different, more confusing failure.
    with pytest.raises(ValueError, match=r"nope"):
        analyze_selected_passages(["ex.1", "nope"], _CITED_TEXTS)
