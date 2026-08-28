"""
Tests for graphs.py's tokengraph_to_networkx()/graph_metrics().

Covers: node/edge parity with mermaid.py's tokengraph_to_mermaid() across
every gold fixture (same nodes, same labels, same edges, same skipped-edge
warnings); GraphMetrics correctness on small, fully hand-computed
fixtures, including a coordinating-conjunction-style extra edge (nonzero
cyclomatic_number); and the degrade-visibly edge cases graph_metrics()
must not raise on -- an empty/all-punctuation tokengraph and a malformed
cycle.
"""

import pytest

from arsgrammatica import token_label
from arsgrammatica.graphs import graph_metrics, tokengraph_to_networkx
from arsgrammatica.models import TokenAnalysis
from conftest import run_gold_example
from fixtures.gold_examples import GOLD_EXAMPLES


# ---------------------------------------------------------------------------
# tokengraph_to_networkx(): parity with tokengraph_to_mermaid()'s own
# node/edge selection, across every gold fixture.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("example", GOLD_EXAMPLES, ids=lambda e: e.slug)
def test_nodes_exclude_punctuation_and_use_the_same_label_as_mermaid(example):
    _tokens, result = run_gold_example(example)
    tokengraph = result.tokengraph

    G, _warnings = tokengraph_to_networkx(tokengraph)

    expected_ids = {tok.id for tok in tokengraph if tok.tokentype != "punctuation"}
    assert set(G.nodes) == expected_ids

    for tok in tokengraph:
        if tok.id in expected_ids:
            assert G.nodes[tok.id]["label"] == token_label(tok), tok.id
            assert G.nodes[tok.id]["tokentype"] == tok.tokentype, tok.id


@pytest.mark.parametrize("example", GOLD_EXAMPLES, ids=lambda e: e.slug)
def test_edges_and_warnings_match_relatedtoken_fields_directly(example):
    """Independently re-derive the expected edges/warnings straight from
    each token's own relatedtoken1/relationship1 and relatedtoken2/
    relationship2 fields (not by calling tokengraph_to_mermaid()), so this
    doesn't just check tokengraph_to_networkx() against a sibling
    implementation that could share the same bug."""
    _tokens, result = run_gold_example(example)
    tokengraph = result.tokengraph
    node_ids = {tok.id for tok in tokengraph if tok.tokentype != "punctuation"}

    expected_edges = set()
    expected_warnings = []
    for tok in tokengraph:
        if tok.id not in node_ids:
            continue
        for related_field, label_field in (
            ("relatedtoken1", "relationship1"),
            ("relatedtoken2", "relationship2"),
        ):
            related_id = getattr(tok, related_field)
            relationship = getattr(tok, label_field)
            if related_id is None or relationship is None:
                continue
            if related_id == "root":
                continue
            if related_id not in node_ids:
                expected_warnings.append(
                    f"skipped edge {tok.id} -[{relationship}]-> {related_id}: "
                    f"target is punctuation or not in tokengraph"
                )
                continue
            expected_edges.add((tok.id, related_id, relationship))

    G, warnings = tokengraph_to_networkx(tokengraph)
    got_edges = {(u, v, r) for u, v, r in G.edges(data="relationship")}

    assert got_edges == expected_edges
    assert warnings == expected_warnings


def test_root_sentinel_produces_no_edge_and_no_warning():
    tokengraph = [
        TokenAnalysis(id="t0", token="venit", tokentype="lexical",
                      verbalunitid="t0", relatedtoken1="root", relationship1="unit verb"),
    ]
    G, warnings = tokengraph_to_networkx(tokengraph)
    assert G.number_of_edges() == 0
    assert warnings == []


def test_edge_to_punctuation_or_missing_target_is_skipped_with_a_warning():
    tokengraph = [
        TokenAnalysis(id="t0", token="foo", tokentype="lexical",
                      relatedtoken1="t1", relationship1="direct object",
                      relatedtoken2="t99", relationship2="dative"),
        TokenAnalysis(id="t1", token=".", tokentype="punctuation"),
    ]
    G, warnings = tokengraph_to_networkx(tokengraph)
    assert G.number_of_edges() == 0
    assert len(warnings) == 2
    assert "t0 -[direct object]-> t1" in warnings[0]
    assert "t0 -[dative]-> t99" in warnings[1]


def test_implied_token_gets_its_placeholder_label():
    tokengraph = [
        TokenAnalysis(id="t0", token="Rara", tokentype="lexical",
                      relatedtoken1="t0_implied", relationship1="predicate"),
        TokenAnalysis(id="t0_implied", token=None, tokentype="implied sum",
                      verbalunitid="t0_implied", relatedtoken1="root", relationship1="unit verb"),
    ]
    G, _warnings = tokengraph_to_networkx(tokengraph)
    assert G.nodes["t0_implied"]["label"] == "elided sum"


# ---------------------------------------------------------------------------
# graph_metrics(): correctness on small, fully hand-computed fixtures.
# ---------------------------------------------------------------------------


def test_metrics_on_a_simple_chain_are_a_pure_tree():
    """"bona puella venit" -- a plain 3-token dependency chain, no
    coordination or other overflow edges, so this should read as a pure
    tree: cyclomatic_number 0, one leaf (the adjective, nothing points at
    it), longest_chain 2 (two edges from leaf to root)."""
    tokengraph = [
        TokenAnalysis(id="t0", token="bona", tokentype="lexical",
                      relatedtoken1="t1", relationship1="adjectival"),
        TokenAnalysis(id="t1", token="puella", tokentype="lexical",
                      relatedtoken1="t2", relationship1="subject"),
        TokenAnalysis(id="t2", token="venit", tokentype="lexical",
                      verbalunitid="t2", relatedtoken1="root", relationship1="unit verb"),
    ]
    G, warnings = tokengraph_to_networkx(tokengraph)
    assert warnings == []
    metrics = graph_metrics(G)

    assert metrics.node_count == 3
    assert metrics.edge_count == 2
    assert metrics.cyclomatic_number == 0
    assert metrics.is_acyclic is True
    assert metrics.longest_chain == 2
    assert metrics.leaf_count == 1
    assert metrics.leaf_fraction == pytest.approx(1 / 3)
    assert metrics.mean_dependents == pytest.approx(2 / 3)
    assert metrics.max_dependents == 1
    assert metrics.relationship_counts == {"adjectival": 1, "subject": 1}


def test_metrics_on_a_coordinating_conjunction_show_nonzero_cyclomatic_number():
    """"Arma virumque cano" -- 'que' coordinates 'Arma' and 'virum', each
    of which is a direct object of 'cano'. The coordinating conjunction's
    own two out-edges are the one construction in this scheme that
    genuinely makes a token's structure more than a tree, so this fixture
    should show cyclomatic_number == 1 (one edge beyond a 3-edge spanning
    tree of 4 nodes)."""
    tokengraph = [
        TokenAnalysis(id="t0", token="Arma", tokentype="lexical",
                      relatedtoken1="t3", relationship1="direct object"),
        TokenAnalysis(id="t1", token="virum", tokentype="lexical",
                      relatedtoken1="t3", relationship1="direct object"),
        TokenAnalysis(id="t2", token="que", tokentype="enclitic",
                      relatedtoken1="t0", relationship1="coordinating conjunction",
                      relatedtoken2="t1", relationship2="coordinating conjunction"),
        TokenAnalysis(id="t3", token="cano", tokentype="lexical",
                      verbalunitid="t3", relatedtoken1="root", relationship1="unit verb"),
    ]
    G, warnings = tokengraph_to_networkx(tokengraph)
    assert warnings == []
    metrics = graph_metrics(G)

    assert metrics.node_count == 4
    assert metrics.edge_count == 4
    assert metrics.cyclomatic_number == 1
    assert metrics.is_acyclic is True
    assert metrics.longest_chain == 2
    assert metrics.leaf_count == 1  # only 'que' has no dependents of its own
    assert metrics.leaf_fraction == pytest.approx(0.25)
    assert metrics.mean_dependents == pytest.approx(1.0)
    assert metrics.max_dependents == 2  # 'cano' is pointed at by both 'Arma' and 'virum'
    assert metrics.relationship_counts == {
        "direct object": 2,
        "coordinating conjunction": 2,
    }


def test_metrics_on_an_empty_tokengraph_are_all_zero_not_raised():
    G, warnings = tokengraph_to_networkx([])
    assert warnings == []
    metrics = graph_metrics(G)

    assert metrics.node_count == 0
    assert metrics.edge_count == 0
    assert metrics.cyclomatic_number == 0
    assert metrics.is_acyclic is True
    assert metrics.longest_chain is None
    assert metrics.leaf_count == 0
    assert metrics.leaf_fraction == 0.0
    assert metrics.mean_dependents == 0.0
    assert metrics.max_dependents == 0
    assert metrics.relationship_counts == {}


def test_metrics_on_an_all_punctuation_tokengraph_are_all_zero_not_raised():
    tokengraph = [TokenAnalysis(id="t0", token=".", tokentype="punctuation")]
    G, warnings = tokengraph_to_networkx(tokengraph)
    assert warnings == []
    metrics = graph_metrics(G)
    assert metrics.node_count == 0
    assert metrics.longest_chain is None


def test_metrics_on_a_malformed_cycle_report_it_rather_than_raising():
    """A cycle should never occur in a well-formed analysis (mirroring
    compute_subordination_depths()'s own cycle-detection warning), but
    graph_metrics() must degrade visibly -- is_acyclic False,
    longest_chain None -- rather than raising, same as the rest of this
    codebase's warnings-not-exceptions convention for malformed input."""
    tokengraph = [
        TokenAnalysis(id="t0", token="a", tokentype="lexical",
                      relatedtoken1="t1", relationship1="subject"),
        TokenAnalysis(id="t1", token="b", tokentype="lexical",
                      relatedtoken1="t0", relationship1="direct object"),
    ]
    G, warnings = tokengraph_to_networkx(tokengraph)
    assert warnings == []
    metrics = graph_metrics(G)

    assert metrics.node_count == 2
    assert metrics.edge_count == 2
    assert metrics.cyclomatic_number == 1
    assert metrics.is_acyclic is False
    assert metrics.longest_chain is None
