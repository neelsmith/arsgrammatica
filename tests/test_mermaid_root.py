"""
Tests for mermaid.py's show_root support (default True) -- separate from
test_mermaid_coloring.py's coloring-specific tests and
test_mermaid_ranking.py's ranking/aat_depth-specific tests, since these
specifically exercise the dedicated 'root' node/edge output, not node/edge
selection, coloring, or ranking. See dot.py's tokengraph_to_dot() for the
DOT-side counterpart, tested the same way in test_dot.py's own "Drawing
the 'root' node (show_root parameter)" section.
"""

import re

import pytest

from arsgrammatica import tokengraph_to_mermaid
from arsgrammatica.models import TokenAnalysis
from conftest import run_gold_example
from fixtures.gold_examples import GOLD_EXAMPLES


def _example(slug):
    return next(e for e in GOLD_EXAMPLES if e.slug == slug)


def test_show_root_default_true_draws_root_node_and_edge():
    example = _example("unit_verb_hercules_cum")
    tokens, result = run_gold_example(example)
    diagram, warnings = tokengraph_to_mermaid(result.tokengraph)
    assert not warnings
    assert '    root(["root"])' in diagram.splitlines()
    assert "t5 -->|unit verb| root" in diagram


def test_show_root_false_omits_root_node_and_edge():
    """show_root=False reproduces this function's behavior before this
    parameter existed: the 'root' relation is skipped silently, with no
    node and no edge for it at all."""
    example = _example("unit_verb_hercules_cum")
    tokens, result = run_gold_example(example)
    diagram, warnings = tokengraph_to_mermaid(result.tokengraph, show_root=False)
    assert not warnings
    assert "root(" not in diagram
    assert "--> root" not in diagram
    assert "-->|unit verb| root" not in diagram


@pytest.mark.parametrize("example", GOLD_EXAMPLES, ids=lambda e: e.slug)
def test_show_root_adds_no_new_warnings(example):
    """Drawing the root node/edges is purely additive -- it must never
    introduce a warning that show_root=False doesn't already have."""
    tokens, result = run_gold_example(example)
    _plain_diagram, plain_warnings = tokengraph_to_mermaid(
        result.tokengraph, show_root=False
    )
    _root_diagram, root_warnings = tokengraph_to_mermaid(
        result.tokengraph, show_root=True
    )
    assert root_warnings == plain_warnings, example.slug


def test_root_node_never_colored():
    """The 'root' node is a plain, uncolored oval regardless of
    color_by_verbal_unit -- it must never be assigned to any verbal unit's
    classDef/class, unlike every real token node."""
    example = _example("unit_verb_hercules_cum")
    tokens, result = run_gold_example(example)
    diagram, _warnings = tokengraph_to_mermaid(result.tokengraph, color_by_verbal_unit=True)
    for line in diagram.splitlines():
        m = re.match(r"\s*class ([\w,]+) (vu\d+|implied);", line)
        if m:
            ids = m.group(1).split(",")
            assert "root" not in ids


def test_multiple_independent_verbs_share_one_root_node():
    """"Ille fidem suam infirmare noluit, Hermionenque ab Oreste adduxit":
    noluit (t4) and adduxit (t10) are both independent root verbs -- both
    should draw an edge into the SAME single 'root' node, not one each."""
    example = _example("coordinating_conjunction_verbs_ille_hermionenque")
    tokens, result = run_gold_example(example)
    diagram, warnings = tokengraph_to_mermaid(result.tokengraph)
    assert not warnings
    lines = diagram.splitlines()
    assert lines.count('    root(["root"])') == 1
    assert "t4 -->|unit verb| root" in diagram
    assert "t10 -->|unit verb| root" in diagram


def test_root_omitted_when_no_independent_verb_is_present():
    """A tokengraph with no 'root'-anchored token at all (e.g. one sentence
    slice out of a larger passage, where the independent verb belongs to a
    different sentence) must never get an orphan 'root' node -- show_root
    only adds the node when there's at least one edge to draw into it."""
    tokengraph = [
        TokenAnalysis(
            id="t0", token="Hercules", tokentype="lexical",
            relatedtoken1="t1", relationship1="subject",
        ),
        TokenAnalysis(
            id="t1", token="pergit", tokentype="lexical", verbalunitid="t1",
            relatedtoken1="t2", relationship1="direct quote",
        ),
        TokenAnalysis(
            id="t2", token="venit", tokentype="lexical", verbalunitid="t2",
        ),
    ]
    diagram, warnings = tokengraph_to_mermaid(tokengraph)
    assert not warnings
    assert "root(" not in diagram
    assert "root" not in diagram


def test_root_survives_aat_depth_zero_filtering():
    """An independent verb's own anchor is always AAT-depth 0, so it (and
    its 'root' edge) must never be excluded by aat_depth filtering --
    show_root and aat_depth compose freely."""
    example = _example("unit_verb_hercules_cum")
    tokens, result = run_gold_example(example)
    diagram, warnings = tokengraph_to_mermaid(result.tokengraph, aat_depth=0)
    assert warnings == []
    assert '    root(["root"])' in diagram.splitlines()
    assert "t5 -->|unit verb| root" in diagram
