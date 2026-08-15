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
    tokens, result = run_gold_example(example)
    diagram, _warnings = tokengraph_to_mermaid(result.tokengraph)
 
    # Every "class <ids> vuN;" line's ids, keyed by which class they got.
    class_of = {}
    for line in diagram.splitlines():
        m = re.match(r"\s*class ([\w,]+) (vu\d+);", line)
        if m:
            ids = m.group(1).split(",")
            class_name = m.group(2)
            for tid in ids:
                assert tid not in class_of, f"{example.slug}: {tid} assigned to more than one class"
                class_of[tid] = class_name
 
    # Every class used must have a matching classDef line.
    classdefs = set(re.findall(r"classDef (vu\d+) ", diagram))
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