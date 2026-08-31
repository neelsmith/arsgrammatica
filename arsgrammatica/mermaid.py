"""
Render a `tokengraph` (a list of TokenAnalysis, as produced by
latin_syntax_dspy.analyze_passage) as a Mermaid flowchart.
 
- Every non-punctuation token becomes a node, labelled with the token's
  surface text.
- Every `relatedtoken1`/`relationship1` and `relatedtoken2`/`relationship2`
  pair on a token becomes a labelled edge from that token to the related
  token.
- By default (`color_by_verbal_unit=True`), every token is also colored by
  the verbal unit it belongs to (see verbal_units.py's assign_verbal_units())
  -- so the clauses a sentence breaks into are visually distinguishable at a
  glance, not just inferable from following edges by hand. The one
  exception: an implied/elided token (models.py's IMPLIED_TOKENTYPES --
  "implied sum", "continued discourse", "implied subject") always gets a
  dedicated "caution" amber (verbal_units._IMPLIED_TOKEN_COLOR) instead,
  regardless of which unit it anchors or (for "implied subject", which
  anchors none of its own -- see models.py's TokenAnalysis docstring)
  resolves into -- flagging "a real word is missing here" rather than
  blending in as an ordinary member of that unit's color. Its label is
  "elided sum" or "continued discourse" (see `_IMPLIED_TOKEN_LABELS`
  below), or else its own tokentype string verbatim ("implied subject"
  has no dedicated entry there), rather than its own surface text, since
  it has none (`token` is `None`). It's also drawn as a rounded-corner
  rectangle (Mermaid's `(...)` node shape) rather than the plain `[...]`
  rectangle every other node uses -- a second, shape-based cue alongside
  the color that this node stands in for a word that isn't actually
  there, independent of and unaffected by verbal-unit coloring (this
  shape applies regardless of `color_by_verbal_unit`). This is the ONE place these tokens are shown at all --
  rendering.py's tokengraph_to_html()/tokengraph_to_depth_html() omit them
  entirely, same as tokengraph_to_text() does, since there's no real word
  to display in reconstructed prose; the Mermaid diagram is where an
  implied token's presence (and what it stands in for, via its edges) is
  actually worth seeing.
- By default (`rank_by_depth=True`), every verbal-unit anchor node is also
  chained to every other anchor at the SAME depth its verbal expression
  would have in an `aat` package AATGraph built from this same tokengraph
  (see verbal_units.py's compute_aat_depths()) using Mermaid's
  invisible-link syntax (`~~~`) -- a layout nudge only, no visible edge and
  no new relation -- so independent clauses, the clauses one level below
  them, and so on, tend to land level with each other in the rendered
  diagram instead of wherever Mermaid's layout engine would otherwise put
  them. This is the SAME depth aat_bridge.py's attgraph() would assign
  that verbal expression's own AAT action node, so this diagram's layout
  and an AAT graph of the same sentence (see latin_syntaxer_review.py's
  own AAT display) rank things identically -- not arsgrammatica's own
  richer, but AAT-incompatible-on-malformed-input, notion of subordination
  depth (compute_subordination_depths()), which still powers
  rendering.py's depth-indented HTML view and is unaffected by this.

(These are the fields syntax_model.md calls `relation1`/`relationship1` and
`relation2`/`relationship2` -- in models.py the "relation" side is named
`relatedtoken*` to make clear it holds a token id, not the relation label.)
 
Punctuation tokens are dropped as nodes. Any edge that would point at a
dropped or unrecognized token id is skipped rather than emitted as a broken
reference, and reported back to the caller so silent gaps are visible --
except the special sentinel target 'root' (an independent verb's own
relatedtoken1, per syntax_model.md), which is skipped silently: it isn't a
real node and was never supposed to be one, so it's not a gap worth
reporting.
"""
 
from typing import List, Tuple
 
from .models import IMPLIED_TOKENTYPES, TokenAnalysis
from .verbal_units import (
    _IMPLIED_TOKEN_COLOR,
    assign_verbal_units,
    assign_verbal_unit_colors,
    compute_aat_depths,
)
 
# Characters that need escaping inside a Mermaid quoted label.
_LABEL_ESCAPES = {
    '"': "&quot;",
    "<": "&lt;",
    ">": "&gt;",
}
 
 
def _escape_label(text: str) -> str:
    for char, replacement in _LABEL_ESCAPES.items():
        text = text.replace(char, replacement)
    return text


# The Mermaid node label for an implied/elided token (keyed by its own
# tokentype, since it has no surface text of its own to use instead) --
# "implied sum" reads as "elided sum" here specifically because that's the
# more immediately legible term for a reader scanning the diagram; "continued
# discourse" already reads fine as-is. Any IMPLIED_TOKENTYPES value not
# listed here (e.g. "implied subject") falls back to its own tokentype
# string verbatim (see its use below), so this mapping is a display
# nicety, not something any tokentype strictly depends on.
_IMPLIED_TOKEN_LABELS = {
    "implied sum": "elided sum",
    "continued discourse": "continued discourse",
}
 
 
# The verbal-unit color palette and the first-appearance ordering rule now
# live in verbal_units.py (assign_verbal_unit_colors()), shared with
# rendering.py's tokengraph_to_html() -- so both consumers assign identical
# colors to the same verbal units instead of each maintaining its own copy.


def token_label(tok: TokenAnalysis) -> str:
    """The display label for one token: its own surface text (`tok.token`),
    or -- for an implied/elided token (tokentype in IMPLIED_TOKENTYPES,
    which has no surface text of its own; `tok.token` is None) -- a
    placeholder from `_IMPLIED_TOKEN_LABELS` ("elided sum" for "implied
    sum", "continued discourse" verbatim), falling back to the token's own
    tokentype string verbatim for any IMPLIED_TOKENTYPES value not listed
    there (e.g. "implied subject").

    This is the exact label `tokengraph_to_mermaid()` puts in each node's
    diagram box; it's pulled out as its own function so anything else that
    needs "the same label the Mermaid diagram uses" for a token --
    graphs.py's tokengraph_to_networkx(), for one -- can reuse it directly
    rather than re-deriving (and risking drifting from) the same fallback
    logic."""
    return (
        tok.token
        if tok.token is not None
        else _IMPLIED_TOKEN_LABELS.get(tok.tokentype, tok.tokentype)
    )


def tokengraph_to_mermaid(
    tokengraph: List[TokenAnalysis],
    orientation: str = "BT",
    color_by_verbal_unit: bool = True,
    rank_by_depth: bool = True,
) -> Tuple[str, List[str]]:
    """Build a Mermaid `graph` diagram from a tokengraph.

    `orientation` is Mermaid's own flowchart orientation code -- `BT`
    (bottom-to-top, the default here), `TB`, `LR`, or `RL` -- used verbatim
    in the diagram's opening line (`graph BT`, `graph LR`, etc.). See
    https://mermaid.js.org/syntax/flowchart.html for what each value looks
    like; this function doesn't validate it, so a typo just becomes invalid
    Mermaid syntax in the output rather than an error here.

    `color_by_verbal_unit` (default True) colors every node by the verbal
    unit it belongs to, per verbal_units.assign_verbal_units() -- so each
    clause is visually distinguishable. Verbal units are assigned colors
    from `_VERBAL_UNIT_PALETTE` in the order their tokens first appear in
    `tokengraph`; a token assigned to no verbal unit is left with Mermaid's
    default node styling. The one exception is an implied/elided token
    (models.py's IMPLIED_TOKENTYPES) -- it always gets its own dedicated
    `implied` class, colored with `verbal_units._IMPLIED_TOKEN_COLOR`,
    instead of whatever `_VERBAL_UNIT_PALETTE` color its own verbal unit
    would otherwise get (see this module's own docstring for why). Pass
    False to skip coloring and get a plain diagram, as before this
    parameter existed.

    `rank_by_depth` (default True) makes the diagram's layout respect each
    verbal expression's own depth in the `aat` package's Agent-Action-
    Target model (see verbal_units.compute_aat_depths()) -- the same depth
    aat_bridge.attgraph() would give that verbal expression's own AAT
    action node, walking related_node chains to an independent (depth 0)
    action: every verbal-unit anchor node (any token with `verbalunitid`
    set to its own id, implied tokens included) at the SAME depth gets
    chained together with Mermaid's invisible-link syntax (`~~~`), e.g.
    `t1 ~~~ t6 ~~~ t9` for three anchors all at depth 2. This draws no
    visible edge and adds no relation of its own -- it only nudges
    Mermaid's layout engine to keep same-depth verbal expressions level
    with each other, the same way independent clauses, the dependent
    clauses one level below them, and so on, end up visually aligned by
    rank rather than scattered -- and lines this diagram's layout up with
    an AAT graph of the same sentence (see compute_aat_depths()'s own
    docstring for exactly how its numbers relate to arsgrammatica's own,
    richer subordination-depth notion, which this does NOT use). A depth
    with only one anchor gets no chain at all (nothing to link); unlike
    the old depth-of-subordination ranking, no anchor is ever excluded for
    having an unresolved depth -- compute_aat_depths() never leaves one
    unresolved (see its own docstring for the one malformed-input case,
    a relation cycle, where that means an arbitrary rather than a
    meaningful depth, rather than an excluded one). Pass False to skip
    this and get the diagram's previous, unranked layout.

    Returns (diagram_text, warnings). `warnings` lists any edges that were
    skipped because they referenced a punctuation token or an id not present
    in `tokengraph` -- worth checking, since it usually means the id came
    from a validation problem upstream (see latin_syntax_dspy.validate) --
    plus, if `color_by_verbal_unit` is True and the passage has more than 8
    verbal units, one warning that colors are repeating rather than staying
    distinct (the palette has 8 slots; see _VERBAL_UNIT_PALETTE).
    `rank_by_depth` itself never adds a warning -- see compute_aat_depths().
    """
    node_ids = {tok.id for tok in tokengraph if tok.tokentype != "punctuation"}
 
    lines = [f"graph {orientation}"]
    for tok in tokengraph:
        if tok.id not in node_ids:
            continue
        # An implied/elided token (see models.py's IMPLIED_TOKENTYPES) has
        # no surface text at all -- tok.token is None -- so it needs a
        # placeholder label rather than crashing _escape_label() on None;
        # token_label() supplies that. The node's color (below) is what
        # actually marks it as an implied token, not the label text.
        label = token_label(tok)
        # An implied/elided token (models.py's IMPLIED_TOKENTYPES) gets a
        # rounded-corner rectangle -- Mermaid's `(...)` node shape -- instead
        # of the plain `[...]` rectangle every other node uses, as a second,
        # shape-based signal (on top of the dedicated amber color below)
        # that this node stands in for a word that isn't actually there.
        open_bracket, close_bracket = (
            ("(", ")") if tok.tokentype in IMPLIED_TOKENTYPES else ("[", "]")
        )
        lines.append(f'    {tok.id}{open_bracket}"{_escape_label(label)}"{close_bracket}')
 
    warnings = []
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
                    f"target is punctuation or not in tokengraph"
                )
                continue
            lines.append(f'    {tok.id} -->|{_escape_label(label)}| {related_id}')

    if rank_by_depth:
        depths = compute_aat_depths(tokengraph)

        # Group every verbal-unit anchor node still in the diagram by its
        # own AAT-graph depth, preserving tokengraph's own (first-
        # appearance) order within each group. Unlike the old depth-of-
        # subordination ranking, compute_aat_depths() never leaves an
        # anchor's depth unresolved -- depths.get() is None here only for a
        # non-anchor token (it only ever keys its result by anchor id), so
        # this `is None` check is purely "is this token an anchor at all",
        # not "did its depth fail to resolve".
        depth_groups: dict = {}
        for tok in tokengraph:
            if tok.id not in node_ids:
                continue
            depth = depths.get(tok.id)
            if depth is None:
                continue
            depth_groups.setdefault(depth, []).append(tok.id)

        rank_lines = [
            "    " + " ~~~ ".join(ids)
            for depth in sorted(depth_groups)
            for ids in (depth_groups[depth],)
            if len(ids) > 1
        ]
        if rank_lines:
            lines.append("")
            lines.extend(rank_lines)

    if color_by_verbal_unit:
        assignment = assign_verbal_units(tokengraph)
        colors, color_warnings = assign_verbal_unit_colors(tokengraph, assignment=assignment)
        warnings.extend(color_warnings)

        # Implied tokens (models.py's IMPLIED_TOKENTYPES) always get a
        # dedicated "caution" amber (_IMPLIED_TOKEN_COLOR) instead of
        # whatever color their own verbal unit would otherwise get --
        # regardless of which unit they anchor -- so they're excluded from
        # every per-unit `member_ids` group below and given their own
        # classDef/class pair instead. See rendering.py's
        # tokengraph_to_html() docstring for the matching HTML behavior.
        implied_ids = [
            tok.id
            for tok in tokengraph
            if tok.id in node_ids and tok.tokentype in IMPLIED_TOKENTYPES
        ]

        if colors or implied_ids:
            lines.append("")
            class_names = {}
            for i, (unit_id, (fill, stroke, text)) in enumerate(colors.items()):
                class_name = f"vu{i}"
                class_names[unit_id] = class_name
                lines.append(
                    f"    classDef {class_name} fill:{fill},stroke:{stroke},color:{text};"
                )
            for unit_id in colors:
                member_ids = [
                    tok.id
                    for tok in tokengraph
                    if tok.id in node_ids
                    and assignment.get(tok.id) == unit_id
                    and tok.id not in implied_ids
                ]
                if member_ids:
                    lines.append(f"    class {','.join(member_ids)} {class_names[unit_id]};")
            if implied_ids:
                fill, stroke, text = _IMPLIED_TOKEN_COLOR
                lines.append(
                    f"    classDef implied fill:{fill},stroke:{stroke},color:{text};"
                )
                lines.append(f"    class {','.join(implied_ids)} implied;")
 
    return "\n".join(lines), warnings
 
 
def save_mermaid(
    tokengraph: List[TokenAnalysis],
    path: str,
    orientation: str = "BT",
    color_by_verbal_unit: bool = True,
    rank_by_depth: bool = True,
) -> List[str]:
    """Write the diagram to `path` (e.g. 'analysis.mmd') and return any
    warnings from tokengraph_to_mermaid."""
    diagram, warnings = tokengraph_to_mermaid(
        tokengraph,
        orientation=orientation,
        color_by_verbal_unit=color_by_verbal_unit,
        rank_by_depth=rank_by_depth,
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(diagram + "\n")
    return warnings