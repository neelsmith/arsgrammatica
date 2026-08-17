"""
Tests for tests/fixtures/harvest.py's gold_example_from_analysis()/
format_gold_example_source() -- turning a real analysis's own
sentences/verbalunits/tokengraph objects into a GoldExample, and rendering
that GoldExample back out as paste-ready Python source.
"""

import ast

import pytest

from arsgrammatica.models import Sentence, Token, TokenAnalysis, VerbalExpression
from fixtures.gold_examples import GOLD_EXAMPLES, GoldExample
from fixtures.harvest import (
    _PLACEHOLDER_REASONING,
    format_gold_example_source,
    gold_example_from_analysis,
)


def _example(slug):
    return next(e for e in GOLD_EXAMPLES if e.slug == slug)


def _real_objects_for(slug):
    """Reconstruct the real pydantic objects (Sentence/VerbalExpression/
    TokenAnalysis) a live analyze() call would have produced for `slug`,
    directly from its own canned_answer -- mirroring
    test_serialization.py's _tokengraph_for()/_verbalunits_for()/
    _sentence_from_tokengraph() helpers."""
    example = _example(slug)
    tokengraph = [TokenAnalysis(**tok) for tok in example.canned_answer["tokengraph"]]
    verbalunits = [VerbalExpression(**vu) for vu in example.canned_answer["verbalunits"]]
    sentences = [
        Sentence(
            tokens=[
                Token(id=tok.id, text=tok.token)
                for tok in tokengraph
                if tok.token is not None
            ]
        )
    ]
    return sentences, verbalunits, tokengraph


@pytest.mark.parametrize(
    "slug",
    [
        "unit_verb_hercules_cum",
        "enclitic_arma_virumque_cano",
        "apposition_neptunus_aegeus_filius",
        "implied_sum_omnia_praeclara_rara",
        "continuation_indirect_discourse_tarquinios_adsuesse",
    ],
    ids=lambda s: s,
)
def test_round_trips_a_real_gold_fixture(slug):
    """Rebuilding a GoldExample from a fixture's own real objects should
    reproduce that fixture's canned_answer and passage exactly -- the
    strongest evidence gold_example_from_analysis() does the pydantic ->
    dict conversion the same way every hand-written fixture already looks,
    including the implied-token and enclitic-overflow shapes."""
    original = _example(slug)
    sentences, verbalunits, tokengraph = _real_objects_for(slug)

    got = gold_example_from_analysis(
        slug=slug,
        tags=original.tags,
        sentences=sentences,
        verbalunits=verbalunits,
        tokengraph=tokengraph,
        reasoning=original.canned_answer["reasoning"],
    )

    assert got.canned_answer["tokengraph"] == original.canned_answer["tokengraph"]
    assert got.canned_answer["verbalunits"] == original.canned_answer["verbalunits"]
    assert got.canned_answer["reasoning"] == original.canned_answer["reasoning"]
    assert got.passage == original.passage
    assert got.tags == original.tags


def test_reasoning_defaults_to_an_obvious_placeholder():
    sentences, verbalunits, tokengraph = _real_objects_for("unit_verb_hercules_cum")
    got = gold_example_from_analysis(
        slug="x", tags=[], sentences=sentences, verbalunits=verbalunits, tokengraph=tokengraph
    )
    assert got.canned_answer["reasoning"] == _PLACEHOLDER_REASONING


def test_explicit_passage_overrides_the_reconstructed_one():
    sentences, verbalunits, tokengraph = _real_objects_for("unit_verb_hercules_cum")
    got = gold_example_from_analysis(
        slug="x",
        tags=[],
        sentences=sentences,
        verbalunits=verbalunits,
        tokengraph=tokengraph,
        passage="Some other wording entirely.",
    )
    assert got.passage == "Some other wording entirely."


def test_empty_tokengraph_raises():
    with pytest.raises(ValueError, match="non-empty tokengraph"):
        gold_example_from_analysis(
            slug="x", tags=[], sentences=[Sentence(tokens=[])], verbalunits=[], tokengraph=[]
        )


def test_malformed_analysis_is_rejected_by_default():
    """A tokengraph referencing an id that isn't in `tokens` and isn't an
    implied token should be caught by validate() -- exactly the same
    problem test_validate.py's test_bad_answer_is_caught() exercises --
    rather than silently becoming a fixture."""
    tokens = [Token(id="t0", text="Rara")]
    sentences = [Sentence(tokens=tokens)]
    tokengraph = [
        TokenAnalysis(
            id="t0", token="Rara", tokentype="lexical",
            relatedtoken1="t99", relationship1="predicate",
        )
    ]
    with pytest.raises(ValueError, match="validate\\(\\) found problems"):
        gold_example_from_analysis(
            slug="x", tags=[], sentences=sentences, verbalunits=[], tokengraph=tokengraph
        )

    # skip_validation=True bypasses the check entirely.
    got = gold_example_from_analysis(
        slug="x", tags=[], sentences=sentences, verbalunits=[], tokengraph=tokengraph,
        skip_validation=True,
    )
    assert got.canned_answer["tokengraph"][0]["relatedtoken1"] == "t99"


def test_implied_token_is_omitted_from_validate_input_but_still_round_trips():
    """sentences' own tokens never include an implied token (see
    conftest.py's tokens_from_canned_answer()) -- validate() must still
    accept the implied entry as legitimate, and it must still appear,
    with token=None, in the resulting canned_answer."""
    sentences, verbalunits, tokengraph = _real_objects_for("implied_sum_omnia_praeclara_rara")
    # Confirm the implied token really was excluded from `sentences` by
    # the test helper above, matching the real pipeline's behavior.
    all_ids = {tok.id for sentence in sentences for tok in sentence.tokens}
    implied_ids = [tok.id for tok in tokengraph if tok.token is None]
    assert implied_ids and all(i not in all_ids for i in implied_ids)

    got = gold_example_from_analysis(
        slug="x", tags=[], sentences=sentences, verbalunits=verbalunits, tokengraph=tokengraph,
    )
    implied_entry = next(
        e for e in got.canned_answer["tokengraph"] if e["id"] == implied_ids[0]
    )
    assert implied_entry["token"] is None


# ---------------------------------------------------------------------------
# format_gold_example_source()
# ---------------------------------------------------------------------------


def test_format_gold_example_source_is_valid_python():
    sentences, verbalunits, tokengraph = _real_objects_for("unit_verb_hercules_cum")
    example = gold_example_from_analysis(
        slug="unit_verb_hercules_cum",
        tags=["unit verb", "subordinating conjunction"],
        sentences=sentences,
        verbalunits=verbalunits,
        tokengraph=tokengraph,
        reasoning="Because.",
    )
    source = format_gold_example_source(example, "_MY_ANSWER")
    # The rendered block is two Python statements separated by a blank
    # line: the "_MY_ANSWER = {...}" dict literal, and a bare
    # "GoldExample(...)," call meant to be pasted straight into
    # GOLD_EXAMPLES's own "[...]" -- wrap the latter in a list literal so
    # it parses as a standalone statement too.
    answer_block, example_block = source.split("\n\n\n")
    ast.parse(answer_block)
    ast.parse("_x = [" + example_block + "]")


def test_format_gold_example_source_round_trips_through_exec():
    """Executing the rendered source (with GoldExample injected into the
    namespace, exactly as gold_examples.py itself would have it in scope)
    should reconstruct an equal GoldExample."""
    sentences, verbalunits, tokengraph = _real_objects_for("apposition_neptunus_aegeus_filius")
    original = _example("apposition_neptunus_aegeus_filius")
    example = gold_example_from_analysis(
        slug=original.slug,
        tags=original.tags,
        sentences=sentences,
        verbalunits=verbalunits,
        tokengraph=tokengraph,
        reasoning=original.canned_answer["reasoning"],
    )
    source = format_gold_example_source(example, "_MY_ANSWER")

    answer_block, example_block = source.split("\n\n\n")
    namespace = {"GoldExample": GoldExample}
    exec(answer_block + "\n_RESULT = [" + example_block + "]", namespace)

    assert namespace["_RESULT"] == [example]
