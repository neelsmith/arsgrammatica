"""
Tests for dot.py's tokengraph_to_dot() -- the Graphviz-DOT counterpart to
mermaid.py's tokengraph_to_mermaid(), covering the same three concerns
test_mermaid_*.py split across test_gold_examples.py (generic
renders-cleanly checks), test_mermaid_coloring.py, and
test_mermaid_ranking.py, adapted to DOT's own syntax:

- coloring is `fillcolor`/`color`/`fontcolor` node attributes instead of
  Mermaid's `classDef`/`class` statements (DOT has no reusable named
  class);
- ranking is a `{rank=same; id1; id2; ...}` subgraph statement instead of
  Mermaid's `~~~` invisible-link chain -- the whole reason dot.py exists
  alongside mermaid.py (see its own module docstring): `rank=same` is a
  hard layout constraint, not a heuristic nudge.

Kept in one file, unlike the three separate mermaid.py test files, since
dot.py is a single, smaller module with much less unique logic of its own
(most of it -- node/edge selection, labeling, color assignment, depth
grouping -- is shared with mermaid.py via token_label()/verbal_units.py
and already covered by the mermaid tests; what's actually dot.py's own is
just how that same data gets written out).
"""

import re

import pytest

from arsgrammatica import tokengraph_to_dot
from arsgrammatica.models import TokenAnalysis
from arsgrammatica.verbal_units import compute_aat_depths, compute_subordination_depths
from conftest import run_gold_example
from fixtures.gold_examples import GOLD_EXAMPLES


# ---------------------------------------------------------------------------
# Generic rendering -- mirrors test_gold_examples.py's
# test_gold_example_renders_mermaid.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("example", GOLD_EXAMPLES, ids=lambda e: e.slug)
def test_gold_example_renders_dot(example):
    tokens, result = run_gold_example(example)
    diagram, warnings = tokengraph_to_dot(result.tokengraph)
    assert not warnings, f"{example.slug}: {warnings}"
    assert diagram.startswith("digraph tokengraph {")
    assert diagram.rstrip().endswith("}")
    for tok in result.tokengraph:
        if tok.tokentype == "punctuation":
            continue
        assert re.search(rf"^\s*{re.escape(tok.id)} \[", diagram, re.MULTILINE), (
            f"{example.slug}: {tok.id} missing its own node line"
        )


def test_hercules_punctuation_excluded_from_nodes():
    tokens, result = run_gold_example(_example("unit_verb_hercules_cum"))
    diagram, _warnings = tokengraph_to_dot(result.tokengraph)

    # Punctuation tokens ("," and ".") must not become nodes.
    assert "t4 [" not in diagram
    assert "t9 [" not in diagram


def _example(slug):
    return next(e for e in GOLD_EXAMPLES if e.slug == slug)


# ---------------------------------------------------------------------------
# Coloring -- mirrors test_mermaid_coloring.py.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("example", GOLD_EXAMPLES, ids=lambda e: e.slug)
def test_coloring_adds_no_new_warnings(example):
    tokens, result = run_gold_example(example)
    _plain, plain_warnings = tokengraph_to_dot(result.tokengraph, color_by_verbal_unit=False)
    _colored, colored_warnings = tokengraph_to_dot(result.tokengraph, color_by_verbal_unit=True)
    assert colored_warnings == plain_warnings, example.slug


def test_disabling_coloring_reproduces_a_plain_diagram():
    tokens, result = run_gold_example(_example("unit_verb_hercules_cum"))
    diagram, _warnings = tokengraph_to_dot(result.tokengraph, color_by_verbal_unit=False)
    assert "fillcolor" not in diagram
    assert diagram.startswith("digraph tokengraph {\n    rankdir=BT;")


def test_orientation_and_coloring_compose():
    tokens, result = run_gold_example(_example("unit_verb_hercules_cum"))
    diagram, _warnings = tokengraph_to_dot(result.tokengraph, orientation="LR")
    assert "rankdir=LR;" in diagram
    assert "fillcolor" in diagram


def test_implied_token_gets_its_own_dedicated_color_and_label():
    """An implied token (here, the elided 'sum' in "omnia praeclara rara")
    always gets the dedicated amber (verbal_units._IMPLIED_TOKEN_COLOR),
    NOT whatever color its own verbal unit (which it anchors) would
    otherwise get -- same convention as tokengraph_to_mermaid(), just as
    inline fillcolor/color/fontcolor attributes instead of a class. Its
    label is "elided sum" (mermaid.token_label()'s own placeholder), and
    it gets `style=rounded` (combined with `filled` here) instead of the
    plain box every other node uses."""
    example = _example("implied_sum_omnia_praeclara_rara")
    tokens, result = run_gold_example(example)
    diagram, warnings = tokengraph_to_dot(result.tokengraph)
    assert not warnings

    implied_ids = [tok.id for tok in result.tokengraph if tok.tokentype == "implied sum"]
    assert implied_ids, "fixture should contain an implied sum token"

    for tid in implied_ids:
        m = re.search(rf'^\s*{re.escape(tid)} \[(.*)\];$', diagram, re.MULTILINE)
        assert m, f"{tid} missing its own node line"
        attrs = m.group(1)
        assert 'label="elided sum"' in attrs
        assert 'fillcolor="#ffc107"' in attrs
        assert 'color="#7a5200"' in attrs
        assert 'fontcolor="#000000"' in attrs
        assert "rounded" in attrs


def test_implied_subject_token_gets_dedicated_color_and_fallback_label():
    """'implied subject' gets the same dedicated amber treatment as
    'implied sum' above, even though it never anchors a verbal unit of its
    own -- the coloring is about the token's own KIND, not which clause
    it's in. It has no entry in mermaid.py's _IMPLIED_TOKEN_LABELS, so its
    label falls back to its tokentype string verbatim. Recordatus (the
    participle that depends on it) keeps its own ordinary verbal-unit
    color, unaffected by its antecedent being implied."""
    example = _example("implied_subject_recordatus_somniorum_ait")
    tokens, result = run_gold_example(example)
    diagram, warnings = tokengraph_to_dot(result.tokengraph)
    assert not warnings

    implied_ids = [tok.id for tok in result.tokengraph if tok.tokentype == "implied subject"]
    assert implied_ids == ["t0_implied"]

    m = re.search(r'^\s*t0_implied \[(.*)\];$', diagram, re.MULTILINE)
    assert m
    attrs = m.group(1)
    assert 'label="implied subject"' in attrs
    assert 'fillcolor="#ffc107"' in attrs

    # Recordatus (t0) itself keeps an ordinary (non-amber) color.
    m2 = re.search(r'^\s*t0 \[(.*)\];$', diagram, re.MULTILINE)
    assert m2
    assert 'fillcolor="#ffc107"' not in m2.group(1)


def test_aside_example_gets_three_distinct_colors():
    """aside_equidem_pace_dixerim has three verbal units (spero's main
    clause, dixerim's aside, esse's indirect statement) -- confirms
    multiple simultaneous colors actually show up in one diagram, not just
    single-unit sentences."""
    example = _example("aside_equidem_pace_dixerim")
    tokens, result = run_gold_example(example)
    diagram, warnings = tokengraph_to_dot(result.tokengraph)
    assert not warnings

    fillcolors = set(re.findall(r'fillcolor="(#[0-9a-fA-F]+)"', diagram))
    # Three verbal units plus (possibly) the dedicated implied-token amber.
    assert len(fillcolors) >= 3

    # nos (t7) has no verbal unit -- must not be colored at all.
    m = re.search(r'^\s*t7 \[(.*)\];$', diagram, re.MULTILINE)
    assert m
    assert "fillcolor" not in m.group(1)


# ---------------------------------------------------------------------------
# Ranking -- mirrors test_mermaid_ranking.py.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("example", GOLD_EXAMPLES, ids=lambda e: e.slug)
def test_ranking_adds_no_new_warnings(example):
    tokens, result = run_gold_example(example)
    _plain, plain_warnings = tokengraph_to_dot(result.tokengraph, rank_by_depth=False)
    _ranked, ranked_warnings = tokengraph_to_dot(result.tokengraph, rank_by_depth=True)
    assert ranked_warnings == plain_warnings, example.slug


def test_two_independent_verbs_get_ranked_together():
    """"Ille fidem suam infirmare noluit, Hermionenque ab Oreste adduxit":
    noluit and adduxit are both independent (depth 0) root verbs -- the
    two anchors at the same depth should get one `rank=same` statement
    forcing them onto the same rank, in the order they first appear."""
    example = _example("coordinating_conjunction_verbs_ille_hermionenque")
    tokens, result = run_gold_example(example)
    diagram, warnings = tokengraph_to_dot(result.tokengraph)
    assert not warnings
    assert "    {rank=same; t4; t10;}" in diagram.splitlines()


def test_multiple_depth_groups_each_get_their_own_rank_statement():
    """"Ille moriens, cum sciret sagittas hydrae Lernaeae felle tinctas,
    sanguinem suum exceptum Deianirae dedit et id philtrum esse dixit":
    dedit/dixit are both depth 0; moriens/sciret/esse are all depth 1;
    tinctas is depth 2, alone, so it gets no rank=same statement of its
    own (nothing to align it with)."""
    example = _example("coordinating_conjunction_dedit_et_dixit_esse")
    tokens, result = run_gold_example(example)
    diagram, warnings = tokengraph_to_dot(result.tokengraph)
    assert not warnings
    lines = diagram.splitlines()
    assert "    {rank=same; t1; t4; t19;}" in lines  # moriens, sciret, esse -- depth 1
    assert "    {rank=same; t15; t20;}" in lines  # dedit, dixit -- depth 0
    rank_lines = [line for line in lines if "rank=same" in line]
    assert len(rank_lines) == 2
    ranked_ids = {tid for line in rank_lines for tid in re.findall(r"t\d+\w*", line)}
    assert "t9" not in ranked_ids  # tinctas -- the only anchor at depth 2


def test_disabling_ranking_produces_no_rank_statements():
    example = _example("coordinating_conjunction_dedit_et_dixit_esse")
    tokens, result = run_gold_example(example)
    diagram, _warnings = tokengraph_to_dot(result.tokengraph, rank_by_depth=False)
    assert "rank=same" not in diagram


def test_ranking_and_coloring_compose():
    example = _example("coordinating_conjunction_dedit_et_dixit_esse")
    tokens, result = run_gold_example(example)
    diagram, _warnings = tokengraph_to_dot(result.tokengraph)
    assert "rank=same" in diagram
    assert "fillcolor" in diagram


def test_cyclic_anchors_still_get_ranked_with_no_warning():
    """Same malformed-input case test_mermaid_ranking.py's own
    test_cyclic_anchors_still_get_ranked_with_no_warning covers: two
    anchors in a direct mutual relation cycle leave
    compute_subordination_depths() unable to resolve either one's depth
    (with a warning), but compute_aat_depths() -- what rank_by_depth
    actually uses -- has no such unresolved state, so both anchors still
    get a plain int depth and no warning, here exactly as in the Mermaid
    diagram."""
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

    diagram, warnings = tokengraph_to_dot(tokengraph, color_by_verbal_unit=False)
    assert warnings == []
    lines = diagram.splitlines()
    assert not any("rank=same" in line and "t0" in line and "t1" in line for line in lines)
    aat_depths = compute_aat_depths(tokengraph)
    assert None not in aat_depths.values()
    assert all(isinstance(d, int) for d in aat_depths.values())


# ---------------------------------------------------------------------------
# Depth filtering (`depth` parameter) -- a SEPARATE feature from the
# rank_by_depth tests above, and a separate depth notion: this uses
# compute_subordination_depths(), the same one
# rendering.tokengraph_to_depth_html()'s own `depth` parameter uses, not
# compute_aat_depths() (what rank_by_depth uses). See tokengraph_to_dot()'s
# own docstring for the full rationale, including why a dropped block can
# leave a KEPT node's edge pointing at an excluded one -- something
# tokengraph_to_depth_html() never has to handle, since it only ever drops
# whole blocks, never a cross-block edge.
# ---------------------------------------------------------------------------


def test_depth_cap_drops_deeper_block_entirely():
    """Same fixture as test_rendering.py's own
    test_depth_html_depth_cap_drops_deeper_blocks_entirely: "Taurum ...
    cum quo Pasiphae concubuit ... ex Creta insula Mycenis uiuum adduxit"
    -- three blocks at depths 0/1/0. depth=0 must drop the middle
    (depth-1) block -- "cum quo Pasiphae concubuit" (t1-t4) -- entirely:
    no node lines, no warnings just from the filtering itself."""
    example = _example("depth_taurum_cum_quo_concubuit")
    tokens, result = run_gold_example(example)
    diagram, warnings = tokengraph_to_dot(result.tokengraph, depth=0)
    assert warnings == []

    for dropped_id in ("t1", "t2", "t3", "t4"):
        assert f"{dropped_id} [" not in diagram, dropped_id
    for kept_id in ("t0", "t5", "t6", "t7", "t8", "t9", "t10"):
        assert re.search(rf"^\s*{kept_id} \[", diagram, re.MULTILINE), kept_id


def test_depth_at_or_beyond_passage_max_matches_depth_none():
    """depth=1 (the passage's own maximum subordination depth) must render
    identically to leaving `depth` unset -- same as
    tokengraph_to_depth_html()'s own behavior."""
    example = _example("depth_taurum_cum_quo_concubuit")
    tokens, result = run_gold_example(example)
    diagram_1, warnings_1 = tokengraph_to_dot(result.tokengraph, depth=1)
    diagram_none, warnings_none = tokengraph_to_dot(result.tokengraph, depth=None)
    assert diagram_1 == diagram_none
    assert warnings_1 == warnings_none


def test_depth_negative_raises():
    example = _example("depth_taurum_cum_quo_concubuit")
    tokens, result = run_gold_example(example)
    with pytest.raises(ValueError, match="depth must be >= 0"):
        tokengraph_to_dot(result.tokengraph, depth=-1)


def test_depth_and_coloring_compose():
    example = _example("depth_taurum_cum_quo_concubuit")
    tokens, result = run_gold_example(example)
    diagram, _warnings = tokengraph_to_dot(result.tokengraph, depth=0)
    assert "fillcolor" in diagram  # kept nodes still get colored


def test_depth_and_ranking_compose():
    """A rank_by_depth `{rank=same; ...}` statement must never name an
    anchor `depth` filtering has excluded."""
    example = _example("coordinating_conjunction_dedit_et_dixit_esse")
    tokens, result = run_gold_example(example)
    # depth=1 keeps everything except the lone depth-2 anchor (tinctas,
    # t9) -- see test_multiple_depth_groups_each_get_their_own_rank_
    # statement above, which already confirms t9 gets no rank=same
    # statement of its own even at depth=None (nothing to align it with).
    diagram, _warnings = tokengraph_to_dot(result.tokengraph, depth=1)
    assert "t9 [" not in diagram
    rank_lines = [line for line in diagram.splitlines() if "rank=same" in line]
    assert not any("t9" in line for line in rank_lines)


def test_depth_dangling_edge_from_kept_node_is_skipped_with_a_warning():
    """A hand-built case exercising the one behavior
    tokengraph_to_depth_html() never has to handle: t3 is assigned to t0's
    depth-0 block (its own relatedtoken1 -> t0), but also carries a
    relatedtoken2 pointing at t2 -- the anchor of the depth-1 block depth=0
    drops. Once t2's whole block is excluded, that edge would dangle;
    tokengraph_to_dot() must skip it (not emit a `t3 -> t2` line pointing
    at a token with no node) and warn, rather than producing DOT Graphviz
    would reject."""
    tokengraph = [
        TokenAnalysis(
            id="t0", token="pergit", tokentype="lexical", verbalunitid="t0",
            relatedtoken1="root", relationship1="unit verb",
        ),
        TokenAnalysis(
            id="t1", token="cum", tokentype="lexical",
            relatedtoken1="t0", relationship1="subordinating conjunction",
        ),
        TokenAnalysis(
            id="t2", token="perlustrasset", tokentype="lexical", verbalunitid="t2",
            relatedtoken1="t1", relationship1="unit verb",
        ),
        TokenAnalysis(
            id="t3", token="stray", tokentype="lexical",
            relatedtoken1="t0", relationship1="subject",
            relatedtoken2="t2", relationship2="coordinating conjunction",
        ),
    ]
    diagram, warnings = tokengraph_to_dot(tokengraph, depth=0, color_by_verbal_unit=False)

    assert "t0 [" in diagram
    assert "t3 [" in diagram
    for dropped_id in ("t1", "t2"):
        assert f"{dropped_id} [" not in diagram
    assert "-> t2" not in diagram  # the dangling edge itself must not appear
    assert any(
        "t3 -[coordinating conjunction]-> t2" in w and "excluded by the depth cutoff" in w
        for w in warnings
    )


@pytest.mark.parametrize("example", GOLD_EXAMPLES, ids=lambda e: e.slug)
def test_depth_filtering_never_leaves_a_dangling_edge(example):
    """Property check across every gold example: capping `depth` at one
    less than the passage's own maximum subordination depth (0 for a
    passage with none) must never leave an edge whose source or target has
    no node line of its own -- the general form of the hand-built case
    above, run against real data instead of a synthetic fixture."""
    tokens, result = run_gold_example(example)
    tokengraph = result.tokengraph
    depths, _warnings = compute_subordination_depths(tokengraph)
    resolved = [d for d in depths.values() if d is not None]
    cap = max(resolved) - 1 if resolved and max(resolved) > 0 else 0

    diagram, _warnings = tokengraph_to_dot(tokengraph, depth=cap)
    node_ids = set(re.findall(r"^\s*(\S+) \[", diagram, re.MULTILINE))
    for source, target in re.findall(r"^\s*(\S+) -> (\S+) \[", diagram, re.MULTILINE):
        assert source in node_ids, f"{example.slug}: edge source {source} has no node"
        assert target in node_ids, f"{example.slug}: edge target {target} has no node"
