"""
Structural test for the pipeline that does NOT require network access to the
school litellm proxy. It uses dspy's DummyLM to stand in for a real model,
returning a hand-written (but valid) analysis for the notes.md example
sentence:

    Hercules cum gregem perlustrasset, pergit ad proximam speluncam.

This proves that: the tokenizer segments correctly, the Signature/pydantic
models accept and validate a well-formed response, and analyze_passage()'s
id-validation logic runs cleanly on good input and actually catches bad
input. It does NOT prove the real LM will produce good analyses -- that
still needs a live run against your configured model (see
latin_syntax_dspy.py's __main__ block).

Run with: python test_pipeline.py
"""

import dspy
from dspy.utils.dummies import DummyLM

from arsgrammatica import analyze, validate, print_analysis, tokenize, tokengraph_to_mermaid

PASSAGE = "Hercules cum gregem perlustrasset, pergit ad proximam speluncam."

# Ids, from the tokenizer, for this sentence:
#   t0 Hercules  t1 cum  t2 gregem  t3 perlustrasset  t4 ,
#   t5 pergit    t6 ad   t7 proximam  t8 speluncam    t9 .

CANNED_ANSWER = {
    "reasoning": (
        "perlustrasset is the dependent verb of the cum-clause, linked to cum as "
        "its unit verb; cum is the subordinating conjunction linked to the main "
        "verb pergit; gregem is the direct object of perlustrasset; Hercules is "
        "the subject of pergit; ad is an adverbial preposition modifying pergit, "
        "governing speluncam as its object."
    ),
    "verbalunits": [
        {"id": "t3", "syntactic_type": "dependent", "semantic_type": "transitive active"},
        {"id": "t5", "syntactic_type": "independent", "semantic_type": "intransitive"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Hercules", "tokentype": "lexical", "lemma": "Hercules",
         "relatedtoken1": "t5", "relationship1": "subject"},
        {"id": "t1", "token": "cum", "tokentype": "lexical", "lemma": "cum",
         "relatedtoken1": "t5", "relationship1": "subordinating conjunction"},
        {"id": "t2", "token": "gregem", "tokentype": "lexical", "lemma": "grex",
         "relatedtoken1": "t3", "relationship1": "direct object"},
        {"id": "t3", "token": "perlustrasset", "tokentype": "lexical", "lemma": "perlustro",
         "verbalunitid": "t3", "relatedtoken1": "t1", "relationship1": "unit verb"},
        {"id": "t4", "token": ",", "tokentype": "punctuation"},
        {"id": "t5", "token": "pergit", "tokentype": "lexical", "lemma": "pergo",
         "verbalunitid": "t5"},
        {"id": "t6", "token": "ad", "tokentype": "lexical", "lemma": "ad",
         "relatedtoken1": "t5", "relationship1": "adverbial"},
        {"id": "t7", "token": "proximam", "tokentype": "lexical", "lemma": "proximus"},
        {"id": "t8", "token": "speluncam", "tokentype": "lexical", "lemma": "spelunca",
         "relatedtoken1": "t6", "relationship1": "object of preposition"},
        {"id": "t9", "token": ".", "tokentype": "punctuation"},
    ],
}


def test_good_answer():
    dspy.configure(lm=DummyLM([CANNED_ANSWER]))
    tokens = tokenize(PASSAGE)
    result = analyze(passage=PASSAGE, tokens=tokens)
    problems = validate(tokens, result)
    assert not problems, f"unexpected validation problems: {problems}"
    print("test_good_answer: PASSED (no validation problems)\n")
    print_analysis(tokens, result)


def test_bad_answer_is_caught():
    """A response that refers to a nonexistent token id should be flagged
    by validate(), not silently accepted."""
    bad_answer = dict(CANNED_ANSWER)
    bad_answer["tokengraph"] = list(CANNED_ANSWER["tokengraph"])
    bad_answer["tokengraph"][0] = {
        **CANNED_ANSWER["tokengraph"][0],
        "relatedtoken1": "t99",  # does not exist
    }
    dspy.configure(lm=DummyLM([bad_answer]))
    tokens = tokenize(PASSAGE)
    result = analyze(passage=PASSAGE, tokens=tokens)
    problems = validate(tokens, result)
    assert problems, "expected validate() to catch the bogus id 't99', but it found nothing"
    print("test_bad_answer_is_caught: PASSED")
    for p in problems:
        print(f"  - {p}")


def test_mermaid_diagram():
    dspy.configure(lm=DummyLM([CANNED_ANSWER]))
    tokens = tokenize(PASSAGE)
    result = analyze(passage=PASSAGE, tokens=tokens)

    diagram, warnings = tokengraph_to_mermaid(result.tokengraph)
    assert not warnings, f"unexpected mermaid warnings: {warnings}"

    # Punctuation tokens (",", ".") must not become nodes.
    assert 't4["' not in diagram
    assert 't9["' not in diagram
    # Every non-punctuation token should be a node.
    for tok in result.tokengraph:
        if tok.tokentype != "punctuation":
            assert f'{tok.id}["' in diagram, f"missing node for {tok.id}"
    # Spot-check a couple of expected edges.
    assert 't3 -->|unit verb| t1' in diagram
    assert 't2 -->|direct object| t3' in diagram

    print("test_mermaid_diagram: PASSED\n")
    print(diagram)


if __name__ == "__main__":
    test_good_answer()
    print()
    test_bad_answer_is_caught()
    print()
    test_mermaid_diagram()
