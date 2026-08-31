"""
Tests for mermaid.py's rank_by_depth support (default True) -- separate
from test_mermaid_coloring.py's coloring-specific tests and
test_gold_examples.py's generic renders-cleanly checks, since these
specifically exercise the invisible-link (`~~~`) output that groups
same-depth verbal-unit anchors together, not node/edge rendering or
coloring.
"""

import pytest

from arsgrammatica import tokengraph_to_mermaid, validate
from arsgrammatica.models import TokenAnalysis
from arsgrammatica.verbal_units import compute_aat_depths, compute_subordination_depths
from conftest import run_gold_example
from fixtures.gold_examples import GOLD_EXAMPLES


@pytest.mark.parametrize("example", GOLD_EXAMPLES, ids=lambda e: e.slug)
def test_ranking_adds_no_new_warnings(example):
    """Ranking is a purely additive layout step -- it must never introduce
    a warning that plain rendering (rank_by_depth=False) doesn't already
    have. compute_aat_depths() (unlike compute_subordination_depths(),
    which some other views still use) never produces a warning at all --
    see test_cyclic_anchors_still_get_ranked_with_no_warning below for the
    one malformed-input case that would have warned under the old
    depth-of-subordination ranking."""
    tokens, result = run_gold_example(example)
    _plain_diagram, plain_warnings = tokengraph_to_mermaid(
        result.tokengraph, rank_by_depth=False
    )
    _ranked_diagram, ranked_warnings = tokengraph_to_mermaid(
        result.tokengraph, rank_by_depth=True
    )
    assert ranked_warnings == plain_warnings, example.slug


def test_two_independent_verbs_get_chained_at_depth_zero():
    """"Ille fidem suam infirmare noluit, Hermionenque ab Oreste adduxit":
    noluit and adduxit are both independent (depth 0) root verbs -- the
    two anchors at the same depth should get one invisible-link line
    chaining them, in the order they first appear."""
    example = next(
        e for e in GOLD_EXAMPLES if e.slug == "coordinating_conjunction_verbs_ille_hermionenque"
    )
    tokens, result = run_gold_example(example)
    diagram, warnings = tokengraph_to_mermaid(result.tokengraph)
    assert not warnings
    assert "    t4 ~~~ t10" in diagram.splitlines()


def test_multiple_depth_groups_each_get_their_own_chain():
    """"Ille moriens, cum sciret sagittas hydrae Lernaeae felle tinctas,
    sanguinem suum exceptum Deianirae dedit et id philtrum esse dixit":
    dedit/dixit are both depth 0 (two independent, coordinated verbs);
    moriens/sciret/esse are all depth 1 (moriens and sciret each one level
    below dedit, esse one level below dixit via its own indirect
    statement); tinctas is depth 2, alone, so it gets no chain at all.
    Each depth with more than one anchor gets its own invisible-link line,
    in first-appearance order; a depth with only one anchor (tinctas) gets
    none."""
    example = next(
        e for e in GOLD_EXAMPLES if e.slug == "coordinating_conjunction_dedit_et_dixit_esse"
    )
    tokens, result = run_gold_example(example)
    diagram, warnings = tokengraph_to_mermaid(result.tokengraph)
    assert not warnings
    lines = diagram.splitlines()
    assert "    t1 ~~~ t4 ~~~ t19" in lines  # moriens, sciret, esse -- all depth 1
    assert "    t15 ~~~ t20" in lines  # dedit, dixit -- both depth 0
    # tinctas (t9) is the only anchor at depth 2 -- nothing to chain it to.
    chain_lines = [line for line in lines if "~~~" in line]
    assert len(chain_lines) == 2
    chained_ids = {tid for line in chain_lines for tid in line.strip().split(" ~~~ ")}
    assert "t9" not in chained_ids


def test_disabling_ranking_reproduces_the_old_unranked_diagram():
    example = next(
        e for e in GOLD_EXAMPLES if e.slug == "coordinating_conjunction_dedit_et_dixit_esse"
    )
    tokens, result = run_gold_example(example)
    diagram, _warnings = tokengraph_to_mermaid(result.tokengraph, rank_by_depth=False)
    assert "~~~" not in diagram


def test_ranking_and_coloring_compose():
    example = next(
        e for e in GOLD_EXAMPLES if e.slug == "coordinating_conjunction_dedit_et_dixit_esse"
    )
    tokens, result = run_gold_example(example)
    diagram, _warnings = tokengraph_to_mermaid(result.tokengraph)
    assert "~~~" in diagram
    assert "classDef vu0" in diagram


def test_cyclic_anchors_still_get_ranked_with_no_warning():
    """Two anchors caught in a relation cycle (see
    test_verbal_units.py's own test_cycle_in_relations_leaves_depth_unresolved_with_warning,
    and test_mutual_cycle_resolves_each_anchor_to_the_other) would leave
    compute_subordination_depths() unable to resolve either one's depth at
    all, with a warning, and tokengraph_to_mermaid() used to surface that
    warning and exclude both anchors from ranking entirely. Since
    rank_by_depth now uses compute_aat_depths() instead (see mermaid.py's
    own docstring for why: it lines this diagram's layout up with what an
    AAT graph of the same sentence would show), the very different
    tradeoff documented there applies here too: NO warning, and both
    anchors DO get a plain int depth and end up in the diagram's ranking
    -- an AATGraph has no way to represent 'this verbal expression's
    subordination couldn't be resolved,' only 'independent' or 'depends on
    this other one,' so this diagram's ranking doesn't either, even though
    the actual numbers a cycle produces are an arbitrary tie-break rather
    than a meaningful depth (see compute_aat_depths()'s own docstring)."""
    tokengraph = [
        TokenAnalysis(
            id="t0", token="a", tokentype="lexical", verbalunitid="t0",
            relatedtoken1="t1", relationship1="unit verb",
        ),
        TokenAnalysis(
            id="t1", token="b", tokentype="lexical", verbalunitid="t1",
            relatedtoken1="t0", relationship1="unit verb",
        ),
    ]
    depths, direct_warnings = compute_subordination_depths(tokengraph)
    assert depths == {"t0": None, "t1": None}
    assert direct_warnings  # compute_subordination_depths() still warns, unchanged

    diagram, warnings = tokengraph_to_mermaid(tokengraph, color_by_verbal_unit=False)
    assert warnings == []
    lines = diagram.splitlines()
    assert not any("~~~" in line and "t0" in line and "t1" in line for line in lines)
    aat_depths = compute_aat_depths(tokengraph)
    assert None not in aat_depths.values()
    assert all(isinstance(d, int) for d in aat_depths.values())
