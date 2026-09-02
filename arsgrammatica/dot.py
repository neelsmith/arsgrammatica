"""
Render a `tokengraph` (a list of TokenAnalysis, as produced by
latin_syntax_dspy.analyze_string) as Graphviz DOT source -- a second
renderer alongside mermaid.py's tokengraph_to_mermaid(), sharing the exact
same node/edge selection, labeling, and coloring rules (token_label(),
verbal_units.assign_verbal_units()/assign_verbal_unit_colors(),
IMPLIED_TOKENTYPES), so the two diagrams of the same tokengraph agree in
every way except the output format and how same-depth alignment is
achieved.

That last difference is the whole reason this module exists.
tokengraph_to_mermaid()'s `rank_by_depth` chains same-depth verbal-unit
anchors together with Mermaid's invisible-link syntax (`~~~`) -- a layout
*nudge* that Mermaid's own layout engine is free to override on a large or
complex diagram. Graphviz's `dot` layout engine has an actual primitive for
this instead: a `{rank=same; id1; id2; ...}` subgraph statement, which
*forces* those nodes onto the same rank (the same horizontal level for
`rankdir=BT`/`TB`, or vertical column for `LR`/`RL`) -- a hard constraint,
not a heuristic. `rank_by_depth` here builds exactly that, from the same
verbal_units.compute_aat_depths() depth groups tokengraph_to_mermaid()
already uses, so both diagrams rank the same way; only the layout engine's
willingness to actually honor it differs.

This module only builds DOT source text -- like tokengraph_to_mermaid(),
it has no rendering dependency at all (no `graphviz` package, no `pydot`,
nothing beyond the standard library). Turning the text into a picture needs
a separate Graphviz installation (the `dot` command-line tool) wherever you
view it -- e.g. `dot -Tsvg analysis.dot > analysis.svg`, an online DOT
viewer, or Quarto's own fenced ```{dot}``` code-block support (which needs
Graphviz on the machine building the site) -- the same division of labor as
a Mermaid diagram needing a Mermaid-capable renderer (mermaid.js, marimo's
`mo.mermaid()`, ...) to actually draw it. Unlike Mermaid, marimo has no
built-in `mo.graphviz()`-equivalent as of this writing -- showing one of
these diagrams in a notebook cell needs one extra manual step: render to
SVG yourself (however you like -- `subprocess` to the `dot` binary, or the
`graphviz` PyPI package, which does the same subprocess call for you) and
wrap the result in `mo.Html(svg_text)`.

tokengraph_to_dot()'s `depth` parameter is a SEPARATE feature from the
rank-alignment one above, and uses a different depth notion entirely: it
caps the diagram to verbal-unit blocks at or below a given *subordination*
depth (verbal_units.compute_subordination_depths()), the same notion and
cutoff rule as rendering.tokengraph_to_depth_html()'s own `depth`
parameter -- not verbal_units.compute_aat_depths(), which `rank_by_depth`
above uses. See tokengraph_to_dot()'s own docstring for the full rationale,
including how a dropped block's dangling edges are handled.
"""

from typing import List, Optional, Tuple

from .models import IMPLIED_TOKENTYPES, TokenAnalysis
from .verbal_units import (
    _IMPLIED_TOKEN_COLOR,
    assign_verbal_units,
    assign_verbal_unit_colors,
    compute_aat_depths,
    compute_subordination_depths,
)
from .mermaid import token_label

# Characters that need escaping inside a DOT quoted string: backslash first
# (so escaping it doesn't double-escape the quotes/newlines added after),
# then the quote character itself. DOT has no HTML-entity-style escaping
# the way Mermaid labels do (see mermaid.py's _LABEL_ESCAPES) -- a quoted
# DOT string is just a C-style string literal.
_LABEL_ESCAPES = [
    ("\\", "\\\\"),
    ('"', '\\"'),
]


def _escape_label(text: str) -> str:
    for char, replacement in _LABEL_ESCAPES:
        text = text.replace(char, replacement)
    return text


def _node_attrs(tok: TokenAnalysis, color: Optional[Tuple[str, str, str]] = None) -> str:
    """The bracketed attribute list for one node line: always `label=`,
    plus `style=rounded` for an implied/elided token (models.py's
    IMPLIED_TOKENTYPES -- the same rounded-corner-box cue
    tokengraph_to_mermaid() draws with Mermaid's `(...)` node shape,
    instead of the plain `[...]`/`shape=box` rectangle every other node
    uses), regardless of whether `color` is given. `color`, when given, is
    an (fill, stroke, text) triple from _VERBAL_UNIT_PALETTE or
    _IMPLIED_TOKEN_COLOR -- adds `style=filled` (combined with `rounded`
    into one comma-separated `style` value when both apply) plus
    `fillcolor`/`color`/`fontcolor`. `color=None` (color_by_verbal_unit=
    False, or a token assigned to no verbal unit) leaves the node with the
    digraph's own default `node [shape=box]` styling, unfilled."""
    label = token_label(tok)
    styles = []
    if tok.tokentype in IMPLIED_TOKENTYPES:
        styles.append("rounded")

    attrs = [f'label="{_escape_label(label)}"']
    if color is not None:
        fill, stroke, text = color
        styles.append("filled")
        attrs.append(f'fillcolor="{fill}"')
        attrs.append(f'color="{stroke}"')
        attrs.append(f'fontcolor="{text}"')
    if styles:
        attrs.append(f'style="{",".join(styles)}"')

    return ", ".join(attrs)


def _tokens_excluded_by_depth(
    tokengraph: List[TokenAnalysis], depth: int
) -> Tuple[set, List[str]]:
    """Token ids belonging to a verbal-unit "block" deeper than `depth` --
    i.e. the same tokens rendering.tokengraph_to_depth_html()'s own `depth`
    parameter would drop entirely. Uses that function's exact grouping and
    cutoff rule (duplicated here rather than imported, since it's an
    internal detail of tokengraph_to_depth_html() and not itself a public
    helper): tokens are grouped into consecutive-run "blocks" by
    verbal_units.assign_verbal_units(), with a token whose own assignment
    is None or which is an enclitic never starting a new block (folding
    into whichever block is currently open instead); a block is dropped
    WHOLE when its own verbal_units.compute_subordination_depths() depth
    exceeds `depth` -- NOT verbal_units.compute_aat_depths(), the different
    depth notion tokengraph_to_dot()'s own `rank_by_depth` uses for rank
    alignment. See tokengraph_to_depth_html()'s docstring for the full
    rationale (leading/trailing unassigned tokens, unresolved-depth
    fallback to 0, etc.) -- this mirrors it exactly, just returning a set
    of excluded ids instead of rendered HTML.

    Returns `(excluded_ids, warnings)` -- `warnings` is
    compute_subordination_depths()'s own (an unresolved governing verbal
    expression); depth filtering itself never adds a warning, same as
    tokengraph_to_depth_html().
    """
    assignment = assign_verbal_units(tokengraph)
    depths, warnings = compute_subordination_depths(tokengraph)

    blocks: List[Tuple[Optional[str], List[TokenAnalysis]]] = []
    for tok in tokengraph:
        unit_id = assignment.get(tok.id)
        starts_new_block = (
            unit_id is not None
            and tok.tokentype != "enclitic"
            and (not blocks or blocks[-1][0] != unit_id)
        )
        if starts_new_block:
            blocks.append((unit_id, []))
        elif not blocks:
            blocks.append((None, []))
        blocks[-1][1].append(tok)

    excluded_ids: set = set()
    for unit_id, block_tokens in blocks:
        block_depth = depths.get(unit_id) if unit_id is not None else 0
        if block_depth is None:
            block_depth = 0
        if block_depth > depth:
            excluded_ids.update(tok.id for tok in block_tokens)

    return excluded_ids, warnings


def tokengraph_to_dot(
    tokengraph: List[TokenAnalysis],
    orientation: str = "BT",
    color_by_verbal_unit: bool = True,
    rank_by_depth: bool = True,
    depth: Optional[int] = None,
) -> Tuple[str, List[str]]:
    """Build a Graphviz DOT `digraph` from a tokengraph -- the same
    diagram tokengraph_to_mermaid() draws (same nodes, same edges, same
    coloring), as DOT source instead of Mermaid source. See this module's
    own docstring for why this exists alongside tokengraph_to_mermaid()
    and what actually rendering the result requires.

    `orientation` maps directly onto DOT's `rankdir` graph attribute --
    `BT` (bottom-to-top, the default here, matching
    tokengraph_to_mermaid()'s own default), `TB`, `LR`, or `RL`. Not
    validated here, same as tokengraph_to_mermaid()'s `orientation` --  a
    typo just becomes an attribute value Graphviz itself will reject.

    `color_by_verbal_unit` (default True) colors every node by the verbal
    unit it belongs to, per verbal_units.assign_verbal_units() -- the
    exact same colors (and the same >8-verbal-units warning) as
    tokengraph_to_mermaid(), just written as `fillcolor`/`color`/
    `fontcolor` attributes directly on each node line instead of Mermaid's
    separate `classDef`/`class` statements (DOT has no equivalent of a
    named, reusable class -- inline per-node attributes are the idiomatic
    way to do this). An implied/elided token (IMPLIED_TOKENTYPES) always
    gets its own dedicated amber (verbal_units._IMPLIED_TOKEN_COLOR)
    instead of whatever color its own verbal unit would otherwise get,
    same as tokengraph_to_mermaid(). Pass False for a plain, uncolored
    diagram.

    `rank_by_depth` (default True) is the reason this module exists
    alongside tokengraph_to_mermaid() -- see the module docstring. Every
    verbal-unit anchor node (any token with `verbalunitid` set to its own
    id, implied tokens included) at the same depth in
    verbal_units.compute_aat_depths() gets listed together in one
    `{rank=same; id1; id2; ...}` subgraph statement, which *forces*
    Graphviz's layout engine to place them on the same rank -- not a nudge,
    a hard constraint. A depth with only one anchor gets no `rank=same`
    statement (nothing to align it WITH; unlike Mermaid's `~~~` chain,
    which genuinely needs 2+ nodes to have anything to link, a
    single-member `rank=same` would be harmless here too, just an inert
    statement -- it's skipped for output cleanliness, not necessity). Pass
    False to skip this and let Graphviz's own layout heuristics place
    every node.

    `depth`, if given, caps the diagram to verbal-unit "blocks" at or
    below that *subordination* depth -- the SAME depth notion and cutoff
    rule as rendering.tokengraph_to_depth_html()'s own `depth` parameter
    (verbal_units.compute_subordination_depths(): an independent clause is
    depth 0, a clause it introduces is depth 1, and so on), NOT the
    verbal_units.compute_aat_depths() notion `rank_by_depth` above uses for
    rank alignment -- the two are unrelated and can disagree on a given
    tokengraph. A block deeper than `depth` is dropped whole: every one of
    its tokens is omitted as a node, exactly as if it had never been in
    `tokengraph`. `depth=0` shows only root/independent-clause blocks
    (direct quotes, asides, and other depth-0 constructions included);
    omit `depth` (or pass `None`, the default) to show every block, same as
    before this parameter existed. A `depth` at or beyond
    verbal_units.max_subordination_depth()'s own return value for this
    `tokengraph` shows everything, identical to leaving `depth` unset; a
    negative `depth` raises ValueError, matching
    tokengraph_to_depth_html()'s own validation.

    Dropping a block can leave a KEPT node's edge pointing at a now-
    excluded token -- something tokengraph_to_depth_html() never has to
    handle, since it only ever drops whole blocks, never an edge between
    two blocks. Such an edge is skipped, with the same combined warning
    already used for an edge targeting punctuation or a genuinely absent
    id (see Returns below) -- `depth` filtering degrades visibly rather
    than emitting a dangling `->` line Graphviz would reject.

    Returns `(dot_source, warnings)` -- same shape and same warnings as
    tokengraph_to_mermaid(): an edge skipped because it targets a
    punctuation token, a token excluded by the `depth` cutoff, or an id not
    present in `tokengraph` (except the 'root' sentinel, skipped silently,
    same as there); if `color_by_verbal_unit` is True and the passage has
    more than 8 verbal units, one warning that colors are repeating; and,
    if `depth` is given, compute_subordination_depths()'s own warnings (an
    unresolved governing verbal expression) -- `depth` filtering itself
    never adds a warning beyond those, same as tokengraph_to_depth_html().
    `rank_by_depth` itself never adds a warning -- see compute_aat_depths().
    """
    if depth is not None and depth < 0:
        raise ValueError(f"depth must be >= 0 (root clauses only), got {depth!r}")

    node_ids = {tok.id for tok in tokengraph if tok.tokentype != "punctuation"}

    warnings: List[str] = []
    if depth is not None:
        depth_excluded_ids, depth_warnings = _tokens_excluded_by_depth(tokengraph, depth)
        warnings.extend(depth_warnings)
        node_ids -= depth_excluded_ids

    colors_by_unit = {}
    implied_ids: set = set()
    if color_by_verbal_unit:
        assignment = assign_verbal_units(tokengraph)
        colors_by_unit, color_warnings = assign_verbal_unit_colors(tokengraph, assignment=assignment)
        warnings.extend(color_warnings)
        implied_ids = {
            tok.id
            for tok in tokengraph
            if tok.id in node_ids and tok.tokentype in IMPLIED_TOKENTYPES
        }
    else:
        assignment = {}

    lines = ["digraph tokengraph {", f"    rankdir={orientation};", "    node [shape=box];", ""]
    for tok in tokengraph:
        if tok.id not in node_ids:
            continue
        color = None
        if color_by_verbal_unit:
            if tok.id in implied_ids:
                color = _IMPLIED_TOKEN_COLOR
            else:
                unit_id = assignment.get(tok.id)
                color = colors_by_unit.get(unit_id) if unit_id is not None else None
        lines.append(f"    {tok.id} [{_node_attrs(tok, color)}];")

    lines.append("")
    for tok in tokengraph:
        if tok.id not in node_ids:
            continue
        for related_field, label_field in (
            ("relatedtoken1", "relationship1"),
            ("relatedtoken2", "relationship2"),
        ):
            related_id = getattr(tok, related_field)
            label = getattr(tok, label_field)
            if related_id is None or label is None:
                continue
            if related_id == "root":
                # An independent verb's own unit-verb relation, per
                # syntax_model.md -- intentionally not a real node, so not
                # a warning-worthy gap. Just draw no edge for it.
                continue
            if related_id not in node_ids:
                warnings.append(
                    f"skipped edge {tok.id} -[{label}]-> {related_id}: "
                    f"target is punctuation, excluded by the depth cutoff, "
                    f"or not in tokengraph"
                )
                continue
            lines.append(f'    {tok.id} -> {related_id} [label="{_escape_label(label)}"];')

    if rank_by_depth:
        depths = compute_aat_depths(tokengraph)

        # Same grouping tokengraph_to_mermaid() builds for its `~~~`
        # chains -- see that function's own comment for why depths.get()
        # being None here means "not an anchor", never "unresolved depth"
        # (compute_aat_depths() has no such state).
        depth_groups: dict = {}
        for tok in tokengraph:
            if tok.id not in node_ids:
                continue
            depth = depths.get(tok.id)
            if depth is None:
                continue
            depth_groups.setdefault(depth, []).append(tok.id)

        rank_lines = [
            "    {rank=same; " + "; ".join(ids) + ";}"
            for depth in sorted(depth_groups)
            for ids in (depth_groups[depth],)
            if len(ids) > 1
        ]
        if rank_lines:
            lines.append("")
            lines.extend(rank_lines)

    lines.append("}")
    return "\n".join(lines), warnings


def save_dot(
    tokengraph: List[TokenAnalysis],
    path: str,
    orientation: str = "BT",
    color_by_verbal_unit: bool = True,
    rank_by_depth: bool = True,
    depth: Optional[int] = None,
) -> List[str]:
    """Write the diagram to `path` (e.g. 'analysis.dot') and return any
    warnings from tokengraph_to_dot()."""
    diagram, warnings = tokengraph_to_dot(
        tokengraph,
        orientation=orientation,
        color_by_verbal_unit=color_by_verbal_unit,
        rank_by_depth=rank_by_depth,
        depth=depth,
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(diagram + "\n")
    return warnings
