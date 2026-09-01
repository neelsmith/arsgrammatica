"""
Represent a `tokengraph` (a list of TokenAnalysis, as produced by
latin_syntax_dspy.analyze_string) as a NetworkX graph, and compute a
handful of size/complexity/shape metrics from it -- the graph-theoretic
counterpart to mermaid.py's visual rendering of the same data, for
programmatic analysis (comparing two analyses' structure, characterizing
a corpus, and eventually topological-equivalence checks) rather than
display.

tokengraph_to_networkx() mirrors tokengraph_to_mermaid() exactly: the same
nodes (non-punctuation tokens, labelled via mermaid.token_label() -- see
that function's own docstring for the implied/elided-token fallback), the
same edges (one per relatedtoken1/relationship1 and relatedtoken2/
relationship2 pair, skipping the 'root' sentinel silently and any
punctuation/missing target with a warning), just built as an
`networkx.MultiDiGraph` instead of Mermaid flowchart source. A
MultiDiGraph (not a plain DiGraph) is used because relatedtoken1 and
relatedtoken2 could in principle both target the same related token with
two different relationship labels -- a plain DiGraph would silently keep
only the second edge in that case.

Edge orientation matters for every metric below: an edge always points
FROM a token TO the token *it* relates to (e.g. a subject noun's edge
points at its verb), the same direction Mermaid draws its arrows in. So a
token with many dependents (e.g. an independent verb, which every one of
its clause's arguments and modifiers ultimately points toward) has high
*in*-degree, not high out-degree; a leaf token with no dependents of its
own has in-degree 0. graph_metrics()'s "dependents"/"leaf" language is
built entirely around this in-degree-as-branching convention.

Most tokengraphs are very nearly out-trees rooted at whichever token(s)
have relatedtoken1 == 'root' (that sentinel is never a real node, so a
root token simply has no outgoing edge at all) -- the same rooted
structure verbal_units.compute_subordination_depths() already assumes.
The handful of constructions that make it more than a tree -- a
coordinating conjunction's relatedtoken1 AND relatedtoken2 both pointing
at the pair it joins, an apposition's second noun pointing back at the
first, and similar overflow uses of relatedtoken2 -- are exactly what
graph_metrics()'s cyclomatic_number counts.
"""

from typing import Dict, List, NamedTuple, Optional, Tuple

import networkx as nx

from .mermaid import token_label
from .models import TokenAnalysis


def tokengraph_to_networkx(tokengraph: List[TokenAnalysis]) -> Tuple[nx.MultiDiGraph, List[str]]:
    """Build a `networkx.MultiDiGraph` from `tokengraph`, using exactly the
    same node/edge selection as tokengraph_to_mermaid() (see this module's
    own docstring) -- so a NetworkX graph built here has the same nodes,
    the same labels, and the same edges as the diagram drawn for the same
    tokengraph, just as a graph object for metric computation rather than
    Mermaid source text.

    Every node carries two attributes: `label` (via mermaid.token_label(),
    the same text/placeholder the diagram shows) and `tokentype` (the
    token's own tokentype string, e.g. for a label-aware isomorphism check
    later that shouldn't have to look anything up in the original
    tokengraph again). Every edge carries one attribute, `relationship`
    (the relatedtoken1/relatedtoken2 pair's own relationship1/
    relationship2 label).

    Returns `(graph, warnings)`; `warnings` mirrors
    tokengraph_to_mermaid()'s own list -- a relatedtoken*/relationship*
    pair pointing at a punctuation token or an id absent from `tokengraph`
    is skipped and reported here, exactly as it is (and isn't drawn)
    there; the 'root' sentinel is skipped silently, the same non-issue it
    is there, since it was never meant to be a node at all.
    """
    node_ids = {tok.id for tok in tokengraph if tok.tokentype != "punctuation"}

    G: nx.MultiDiGraph = nx.MultiDiGraph()
    for tok in tokengraph:
        if tok.id not in node_ids:
            continue
        G.add_node(tok.id, label=token_label(tok), tokentype=tok.tokentype)

    warnings: List[str] = []
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
                # An independent verb's own unit-verb relation, per
                # syntax_model.md -- intentionally not a real node, so not
                # a warning-worthy gap. Just add no edge for it.
                continue
            if related_id not in node_ids:
                warnings.append(
                    f"skipped edge {tok.id} -[{relationship}]-> {related_id}: "
                    f"target is punctuation or not in tokengraph"
                )
                continue
            G.add_edge(tok.id, related_id, relationship=relationship)

    return G, warnings


class GraphMetrics(NamedTuple):
    """Size/complexity/shape metrics for one tokengraph's NetworkX graph
    (see tokengraph_to_networkx() and this module's own docstring for the
    edge orientation these assume -- every "dependent"/"leaf" here is
    about in-degree, not out-degree).

    Size and complexity:

    - `node_count`/`edge_count`: tokens (excluding punctuation) and
      relations between them.
    - `cyclomatic_number`: edges beyond a spanning tree
      (`edge_count - node_count + weakly_connected_components`) -- 0 for
      a pure tree; each coordinating conjunction, apposition, or similar
      construction that gives a token a second governor/dependent beyond
      strict tree shape adds 1. A direct, single-number answer to "how
      much non-tree structure does this sentence have".
    - `is_acyclic`/`longest_chain`: whether the graph is a DAG (it always
      should be for a well-formed analysis; a cycle means something is
      malformed, mirroring compute_subordination_depths()'s own
      cycle-detection warning) and, if so, the length in edges of its
      longest directed path -- the deepest raw token-to-token embedding
      chain in the sentence. `longest_chain` is None when a cycle makes
      it undefined, or the graph is empty.

    Shape:

    - `leaf_count`/`leaf_fraction`: tokens with no dependents of their own
      (in-degree 0) -- terminal tokens in the dependency structure.
    - `mean_dependents`/`max_dependents`: the in-degree distribution's
      mean and max -- how many other tokens point at the typical/busiest
      token. A sentence with a high max relative to its node count reads
      as "one token governs almost everything"; a low, even mean/max
      reads as "shallow and bushy" rather than "deep and chainy".
    - `relationship_counts`: how many edges carry each relationship label
      (e.g. `{"subject": 2, "direct object": 1, ...}`) -- what KIND of
      structure the sentence leans on, not just how much of it there is.

    All fields are 0/0.0/empty (not raised) for an empty graph.
    """

    node_count: int
    edge_count: int
    cyclomatic_number: int
    is_acyclic: bool
    longest_chain: Optional[int]
    leaf_count: int
    leaf_fraction: float
    mean_dependents: float
    max_dependents: int
    relationship_counts: Dict[str, int]


def graph_metrics(G: nx.MultiDiGraph) -> GraphMetrics:
    """Compute GraphMetrics for `G` (as built by tokengraph_to_networkx(),
    though this only depends on `G` being a networkx graph with an
    `relationship` edge attribute -- it doesn't otherwise care how `G` was
    built). See GraphMetrics's own docstring for what each field means and
    the in-degree-as-branching convention every "dependent"/"leaf" metric
    here assumes.
    """
    node_count = G.number_of_nodes()
    edge_count = G.number_of_edges()
    components = nx.number_weakly_connected_components(G)
    cyclomatic_number = edge_count - node_count + components

    is_acyclic = nx.is_directed_acyclic_graph(G)
    longest_chain = nx.dag_longest_path_length(G) if is_acyclic and node_count else None

    in_degrees = [degree for _, degree in G.in_degree()]
    leaf_count = sum(1 for degree in in_degrees if degree == 0)
    leaf_fraction = leaf_count / node_count if node_count else 0.0
    mean_dependents = sum(in_degrees) / node_count if node_count else 0.0
    max_dependents = max(in_degrees) if in_degrees else 0

    relationship_counts: Dict[str, int] = {}
    for _, _, relationship in G.edges(data="relationship"):
        relationship_counts[relationship] = relationship_counts.get(relationship, 0) + 1

    return GraphMetrics(
        node_count=node_count,
        edge_count=edge_count,
        cyclomatic_number=cyclomatic_number,
        is_acyclic=is_acyclic,
        longest_chain=longest_chain,
        leaf_count=leaf_count,
        leaf_fraction=leaf_fraction,
        mean_dependents=mean_dependents,
        max_dependents=max_dependents,
        relationship_counts=relationship_counts,
    )
