"""
Tests for pipeline.py's analyze_passage() -- the convenience wrapper that
replaces the old tokenizer.py-backed analyze_passage() that used to live in
latin_syntax_dspy.py. Not named test_pipeline.py to avoid confusion with the
pre-pytest-suite script of that name that this whole tests/ directory
already superseded.
 
analyze_passage() is now a thin single-string convenience wrapper around
analyze_sources(): it wraps `passage` as one CitedText and returns exactly
what analyze_sources() returns, (sentences, results), one entry per
sentence segmentation finds -- no restriction to a single sentence anymore.
(An earlier version raised ValueError on multi-sentence input and returned
a single (tokens, result) pair instead; that restriction is gone.)
 
Two things worth checking that nothing else in the suite exercises:
  - the single-sentence case still returns one-element (sentences, results)
    lists, with the right tokens/citation/verbalunits;
  - the multi-sentence case analyzes every sentence it finds, in order,
    with each sentence's own SyntaxAnalysis result lining up positionally.
"""
 
import dspy
from dspy.utils.dummies import DummyLM
 
from arsgrammatica import analyze_passage
 
_ONE_SENTENCE = {
    "reasoning": "One sentence, four tokens.",
    "sentences": [
        {"tokens": [
            {"id": "t0", "text": "arma", "citation": "ex.1"},
            {"id": "t1", "text": "virumque", "citation": "ex.1"},
            {"id": "t2", "text": "cano", "citation": "ex.1"},
            {"id": "t3", "text": ".", "citation": "ex.1"},
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
 
_TWO_SENTENCES = {
    "reasoning": "Two sentences.",
    "sentences": [
        {"tokens": [{"id": "t0", "text": "ita", "citation": "ex.2"},
                     {"id": "t1", "text": ".", "citation": "ex.2"}]},
        {"tokens": [{"id": "t2", "text": "vale", "citation": "ex.2"},
                     {"id": "t3", "text": ".", "citation": "ex.2"}]},
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
 
 
def test_analyze_passage_single_sentence_returns_one_sentence_and_result():
    dspy.configure(lm=DummyLM([_ONE_SENTENCE, _ONE_SENTENCE_ANALYSIS]))
 
    sentences, results = analyze_passage("arma virumque cano.", citation="ex.1")
 
    assert len(sentences) == 1
    assert len(results) == 1
    tokens = sentences[0].tokens
    assert [t.id for t in tokens] == ["t0", "t1", "t2", "t3"]
    assert [t.text for t in tokens] == ["arma", "virumque", "cano", "."]
    assert all(t.citation == "ex.1" for t in tokens)
    assert results[0].verbalunits[0].id == "t2"
 
 
def test_analyze_passage_multi_sentence_analyzes_every_sentence_in_order():
    dspy.configure(lm=DummyLM([_TWO_SENTENCES, _ITA_ANALYSIS, _VALE_ANALYSIS]))
 
    sentences, results = analyze_passage("ita. vale.", citation="ex.2")
 
    assert len(sentences) == 2
    assert len(results) == 2
 
    assert [t.id for t in sentences[0].tokens] == ["t0", "t1"]
    assert [t.id for t in sentences[1].tokens] == ["t2", "t3"]
 
    # results line up positionally with sentences: results[0] is "ita."'s
    # analysis (no verbal unit), results[1] is "vale."'s (one, at t2).
    assert results[0].verbalunits == []
    assert results[1].verbalunits[0].id == "t2"