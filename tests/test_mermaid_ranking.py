"""
Tests for mermaid.py's rank_by_depth support (default True) -- separate
from test_mermaid_coloring.py's coloring-specific tests and
test_gold_examples.py's generic renders-cleanly checks, since these
specifically exercise the invisible-link (`~~~`) output that groups
same-depth verbal-unit anchors together, not node/edge rendering or
coloring.

Also covers `aat_depth` (a SECOND, INDEPENDENT feature that happens to
share rank_by_depth's own compute_aat_depths() numbers, now used to DROP
nodes instead of just aligning them) in its own section below -- see
dot.py's tokengraph_to_dot() for the DOT-side counterpart, tested the same
way in test_dot.py.
"""

import re

import pytest

from arsgrammatica import tokengraph_to_mermaid, validate
from arsgrammatica.models import TokenAnalysis
from arsgrammatica.verbal_units import (
    assign_verbal_units,
    compute_aat_depths,
    compute_subordination_depths,
    max_aat_depth,
)
from conftest import run_gold_example
from fixtures.gold_examples import GOLD_EXAMPLES


def _example(slug):
    return next(e for e in GOLD_EXAMPLES if e.slug == slug)


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


# ---------------------------------------------------------------------------
# AAT-depth filtering (`aat_depth` parameter) -- a SECOND, INDEPENDENT
# feature from the ranking tests above, sharing the same
# compute_aat_depths() numbers but now dropping nodes rather than aligning
# them. Every token takes the AAT depth of the verbal unit it belongs to
# (verbal_units.assign_verbal_units()), so a whole clause's verb and all
# of its ordinary dependents share ONE aat_depth and are kept or dropped
# together -- unlike dot.py's own graph-distance `depth`, where each
# dependent is its own hop deeper than its governor. See
# tokengraph_to_mermaid()'s own docstring for the full rationale, and
# test_dot.py's mirrored "AAT-depth filtering" section for the DOT-side
# counterpart of every test below.
# ---------------------------------------------------------------------------


def test_aat_depth_zero_shows_the_whole_root_clause():
    """"Hercules cum gregem perlustrasset, pergit ad proximam speluncam":
    pergit's own verbal unit (t5) is depth 0 and includes Hercules (t0),
    ad (t6), and speluncam (t8) as ordinary dependents; perlustrasset's
    unit (t3, depth 1) is entirely separate. aat_depth=0 must keep EVERY
    token in pergit's clause, not just pergit itself -- the exact
    distinction from dot.py's graph-distance `depth=0`, which would show
    only the bare root verb. t7 ("proximam", no verbal-unit assignment at
    all) is kept too, via the same "unresolved defaults to depth 0"
    fallback used throughout this codebase."""
    example = _example("unit_verb_hercules_cum")
    tokens, result = run_gold_example(example)
    diagram, warnings = tokengraph_to_mermaid(result.tokengraph, aat_depth=0)
    assert warnings == []
    for kept_id in ("t0", "t5", "t6", "t7", "t8"):
        assert re.search(rf'^    {kept_id}[\[\(]', diagram, re.MULTILINE), kept_id
    for dropped_id in ("t1", "t2", "t3"):
        assert f"{dropped_id}[" not in diagram and f"{dropped_id}(" not in diagram, dropped_id


def test_aat_depth_at_or_beyond_passage_max_matches_aat_depth_none():
    example = _example("unit_verb_hercules_cum")
    tokens, result = run_gold_example(example)
    maxd = max_aat_depth(result.tokengraph)
    diagram_max, warnings_max = tokengraph_to_mermaid(result.tokengraph, aat_depth=maxd)
    diagram_none, warnings_none = tokengraph_to_mermaid(result.tokengraph, aat_depth=None)
    assert diagram_max == diagram_none
    assert warnings_max == warnings_none


def test_aat_depth_negative_raises():
    example = _example("unit_verb_hercules_cum")
    tokens, result = run_gold_example(example)
    with pytest.raises(ValueError, match="aat_depth must be >= 0"):
        tokengraph_to_mermaid(result.tokengraph, aat_depth=-1)


def test_aat_depth_and_coloring_compose():
    example = _example("unit_verb_hercules_cum")
    tokens, result = run_gold_example(example)
    diagram, _warnings = tokengraph_to_mermaid(result.tokengraph, aat_depth=0)
    assert "classDef vu0" in diagram  # kept nodes still get colored


def test_aat_depth_and_ranking_compose():
    """A `~~~` chain must never name an anchor `aat_depth` filtering has
    excluded."""
    example = _example("coordinating_conjunction_dedit_et_dixit_esse")
    tokens, result = run_gold_example(example)
    diagram, _warnings = tokengraph_to_mermaid(result.tokengraph, aat_depth=1)
    node_ids = set(re.findall(r'^    (\S+?)[\[\(]', diagram, re.MULTILINE))
    chain_lines = [line for line in diagram.splitlines() if "~~~" in line]
    chained_ids = {tid for line in chain_lines for tid in line.strip().split(" ~~~ ")}
    assert chained_ids <= node_ids


def test_aat_depth_dangling_edge_from_kept_node_is_skipped_with_a_warning():
    """Same hand-built coordinating-conjunction fixture as
    test_dot.py's test_aat_depth_dangling_edge_from_kept_node_is_skipped_with_a_warning:
    "que" resolves into "cano"'s unit (depth 0) but its relatedtoken2 edge
    points at "virum", which anchors its OWN separate verbal unit (depth
    1) -- at aat_depth=0, "que" is kept but "virum" is excluded, so that
    edge must be skipped with a warning rather than left dangling."""
    tokengraph = [
        TokenAnalysis(
            id="t5", token="cano", tokentype="lexical", verbalunitid="t5",
            relatedtoken1="root", relationship1="unit verb",
        ),
        TokenAnalysis(
            id="t0", token="arma", tokentype="lexical",
            relatedtoken1="t5", relationship1="direct object",
        ),
        TokenAnalysis(
            id="t1", token="que", tokentype="enclitic",
            relatedtoken1="t0", relationship1="coordinating conjunction",
            relatedtoken2="t2", relationship2="coordinating conjunction",
        ),
        TokenAnalysis(
            id="t2", token="virum", tokentype="lexical", verbalunitid="t2",
            relatedtoken1="t5", relationship1="direct object",
        ),
    ]
    diagram, warnings = tokengraph_to_mermaid(tokengraph, aat_depth=0, color_by_verbal_unit=False)

    assert re.search(r'^    t1[\[\(]', diagram, re.MULTILINE)
    assert not re.search(r'^    t2[\[\(]', diagram, re.MULTILINE)
    assert "--> t2" not in diagram  # the dangling edge itself must not appear
    assert any(
        "t1 -[coordinating conjunction]-> t2" in w
        and "excluded by the aat_depth cutoff" in w
        for w in warnings
    )


@pytest.mark.parametrize("example", GOLD_EXAMPLES, ids=lambda e: e.slug)
def test_aat_depth_filtering_never_leaves_a_dangling_edge(example):
    """Property check across every gold example, at every AAT-depth level
    from 0 up to that passage's own max_aat_depth(): no edge may be left
    whose source or target has no node line of its own."""
    tokens, result = run_gold_example(example)
    tokengraph = result.tokengraph
    maxd = max_aat_depth(tokengraph)
    if maxd is None:
        return

    for cap in range(0, maxd + 1):
        diagram, _warnings = tokengraph_to_mermaid(tokengraph, aat_depth=cap)
        node_ids = set(re.findall(r'^    (\S+?)[\[\(]', diagram, re.MULTILINE))
        for source, target in re.findall(r"^    (\S+) -->\|[^|]*\| (\S+)", diagram, re.MULTILINE):
            assert source in node_ids, f"{example.slug} aat_depth={cap}: edge source {source} has no node"
            assert target in node_ids, f"{example.slug} aat_depth={cap}: edge target {target} has no node"


@pytest.mark.parametrize("example", GOLD_EXAMPLES, ids=lambda e: e.slug)
def test_aat_depth_zero_never_drops_a_token_from_its_own_clause(example):
    """Structural check across the whole fixture set: at aat_depth=0, every
    KEPT verbal-unit anchor's own dependents (per assign_verbal_units())
    must also be kept -- confirming the filter drops or keeps a whole
    clause together, never splits one apart."""
    tokens, result = run_gold_example(example)
    tokengraph = result.tokengraph
    diagram, _warnings = tokengraph_to_mermaid(tokengraph, aat_depth=0)
    node_ids = set(re.findall(r'^    (\S+?)[\[\(]', diagram, re.MULTILINE))

    depths = compute_aat_depths(tokengraph)
    assignment = assign_verbal_units(tokengraph)
    for tok in tokengraph:
        if tok.tokentype == "punctuation":
            continue
        unit_id = assignment.get(tok.id)
        unit_depth = depths.get(unit_id, 0) if unit_id is not None else 0
        if unit_depth == 0:
            assert tok.id in node_ids, f"{example.slug}: {tok.id} should survive aat_depth=0"
