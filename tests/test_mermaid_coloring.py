"""
Tests for mermaid.py's color_by_verbal_unit support (default True) --
separate from test_gold_examples.py's generic renders-cleanly checks, since
these specifically exercise the classDef/class coloring output, not just
node/edge rendering.
"""
 
import re
 
import pytest
 
from arsgrammatica import tokengraph_to_mermaid, validate
from conftest import run_gold_example
from fixtures.gold_examples import GOLD_EXAMPLES
 
 
@pytest.mark.parametrize("example", GOLD_EXAMPLES, ids=lambda e: e.slug)
def test_coloring_adds_no_new_warnings(example):
    """Coloring is a purely additive rendering step -- it must never
    introduce a warning that plain rendering (color_by_verbal_unit=False)
    doesn't already have, for any well-formed gold fixture."""
    tokens, result = run_gold_example(example)
    _plain_diagram, plain_warnings = tokengraph_to_mermaid(
        result.tokengraph, color_by_verbal_unit=False
    )
    _colored_diagram, colored_warnings = tokengraph_to_mermaid(
        result.tokengraph, color_by_verbal_unit=True
    )
    assert colored_warnings == plain_warnings, example.slug
 
 
@pytest.mark.parametrize("example", GOLD_EXAMPLES, ids=lambda e: e.slug)
def test_every_colored_node_gets_exactly_one_class(example):
    """Covers both verbal-unit classes (vuN) and the dedicated `implied`
    class an implied/elided token always gets instead (see
    tokengraph_to_mermaid()'s own docstring) -- every node should still end
    up in exactly one class either way."""
    tokens, result = run_gold_example(example)
    diagram, _warnings = tokengraph_to_mermaid(result.tokengraph)

    # Every "class <ids> vuN;"/"class <ids> implied;" line's ids, keyed by
    # which class they got.
    class_of = {}
    for line in diagram.splitlines():
        m = re.match(r"\s*class ([\w,]+) (vu\d+|implied);", line)
        if m:
            ids = m.group(1).split(",")
            class_name = m.group(2)
            for tid in ids:
                assert tid not in class_of, f"{example.slug}: {tid} assigned to more than one class"
                class_of[tid] = class_name

    # Every class used must have a matching classDef line.
    classdefs = set(re.findall(r"classDef (vu\d+|implied) ", diagram))
    assert set(class_of.values()) <= classdefs, example.slug
 
 
def test_disabling_coloring_reproduces_the_old_plain_diagram():
    example = next(e for e in GOLD_EXAMPLES if e.slug == "unit_verb_hercules_cum")
    tokens, result = run_gold_example(example)
    diagram, _warnings = tokengraph_to_mermaid(result.tokengraph, color_by_verbal_unit=False)
    assert "classDef" not in diagram
    assert "class " not in diagram
    assert diagram.startswith("graph BT")
 
 
def test_orientation_and_coloring_compose():
    example = next(e for e in GOLD_EXAMPLES if e.slug == "unit_verb_hercules_cum")
    tokens, result = run_gold_example(example)
    diagram, _warnings = tokengraph_to_mermaid(result.tokengraph, orientation="LR")
    assert diagram.startswith("graph LR")
    assert "classDef vu0" in diagram
 
 
def test_implied_token_gets_its_own_dedicated_class_and_label():
    """An implied token (here, the elided 'sum' in "omnia praeclara rara")
    always gets the special `implied` class -- colored with
    verbal_units._IMPLIED_TOKEN_COLOR, NOT whatever `_VERBAL_UNIT_PALETTE`
    color its own verbal unit (which it anchors) would otherwise get -- and
    its node label is "elided sum" (mermaid.py's own _IMPLIED_TOKEN_LABELS,
    keyed by its tokentype "implied sum"), since it has no surface text of
    its own. It's also drawn as a rounded-corner rectangle, `id("label")`,
    rather than the plain `id["label"]` rectangle every other node uses.
    This is the ONE place an implied token is shown at all --
    tokengraph_to_html() omits it entirely (see test_rendering.py's
    test_implied_tokens_are_omitted_from_html_entirely)."""
    example = next(e for e in GOLD_EXAMPLES if e.slug == "implied_sum_omnia_praeclara_rara")
    tokens, result = run_gold_example(example)
    diagram, warnings = tokengraph_to_mermaid(result.tokengraph)
    assert not warnings

    implied_ids = [tok.id for tok in result.tokengraph if tok.tokentype == "implied sum"]
    assert implied_ids, "fixture should contain an implied sum token"

    assert 'classDef implied fill:#ffc107,stroke:#7a5200,color:#000000;' in diagram
    implied_class_lines = [
        line for line in diagram.splitlines() if line.strip().endswith("implied;")
    ]
    assert len(implied_class_lines) == 1
    assert set(implied_class_lines[0].split()[1].split(",")) == set(implied_ids)

    for tid in implied_ids:
        assert f'{tid}("elided sum")' in diagram
    # No vuN classDef should also claim an implied token.
    for line in diagram.splitlines():
        if re.match(r"\s*class ([\w,]+) vu\d+;", line):
            ids = line.split()[1].split(",")
            for tid in implied_ids:
                assert tid not in ids


def test_implied_subject_token_gets_dedicated_class_and_fallback_label():
    """'implied subject' (see models.py's TokenAnalysis/IMPLIED_TOKENTYPES)
    gets the same dedicated `implied` amber class as 'implied sum' above,
    even though it never anchors a verbal unit of its own (unlike
    'implied sum') -- the coloring is about the token's own KIND, not
    about which clause it's in. It has no entry in mermaid.py's own
    _IMPLIED_TOKEN_LABELS, so its node label falls back to its tokentype
    string verbatim, "implied subject" (see that mapping's own comment).
    It also gets the rounded-corner rectangle shape, `id("label")`, same
    as any other implied token. Recordatus (the participle) keeps its own
    ordinary vuN class and plain `id["label"]` rectangle, unaffected by
    its antecedent being implied."""
    example = next(
        e for e in GOLD_EXAMPLES if e.slug == "implied_subject_recordatus_somniorum_ait"
    )
    tokens, result = run_gold_example(example)
    diagram, warnings = tokengraph_to_mermaid(result.tokengraph)
    assert not warnings

    implied_ids = [tok.id for tok in result.tokengraph if tok.tokentype == "implied subject"]
    assert implied_ids == ["t0_implied"]

    assert 'classDef implied fill:#ffc107,stroke:#7a5200,color:#000000;' in diagram
    implied_class_lines = [
        line for line in diagram.splitlines() if line.strip().endswith("implied;")
    ]
    assert len(implied_class_lines) == 1
    assert set(implied_class_lines[0].split()[1].split(",")) == set(implied_ids)

    assert 't0_implied("implied subject")' in diagram

    # No vuN classDef should also claim the implied-subject token, but
    # Recordatus (its own real verbal-unit anchor) should still have one.
    vu_class_ids = set()
    for line in diagram.splitlines():
        if re.match(r"\s*class ([\w,]+) vu\d+;", line):
            vu_class_ids.update(line.split()[1].split(","))
    assert "t0_implied" not in vu_class_ids
    assert "t0" in vu_class_ids


def test_aside_example_gets_three_distinct_colors():
    """aside_equidem_pace_dixerim has three verbal units (spero's main
    clause, dixerim's aside, esse's indirect statement) -- confirms
    multiple simultaneous colors actually show up in one diagram, not just
    single-unit sentences."""
    example = next(e for e in GOLD_EXAMPLES if e.slug == "aside_equidem_pace_dixerim")
    tokens, result = run_gold_example(example)
    diagram, warnings = tokengraph_to_mermaid(result.tokengraph)
    assert not warnings
    assert "classDef vu0" in diagram
    assert "classDef vu1" in diagram
    assert "classDef vu2" in diagram
    assert "classDef vu3" not in diagram
    # nos (t7) has no verbal unit -- must not be assigned any class.
    for line in diagram.splitlines():
        if line.strip().startswith("class "):
            assert "t7" not in line.split()[1].split(",")