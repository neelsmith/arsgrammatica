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
  glance, not just inferable from following edges by hand.
 
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
 
from .models import TokenAnalysis
from .verbal_units import assign_verbal_units, assign_verbal_unit_colors
 
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
 
 
# The verbal-unit color palette and the first-appearance ordering rule now
# live in verbal_units.py (assign_verbal_unit_colors()), shared with
# rendering.py's tokengraph_to_html() -- so both consumers assign identical
# colors to the same verbal units instead of each maintaining its own copy.
 
 
def tokengraph_to_mermaid(
    tokengraph: List[TokenAnalysis],
    orientation: str = "BT",
    color_by_verbal_unit: bool = True,
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
    default node styling. Pass False to skip coloring and get a plain
    diagram, as before this parameter existed.
 
    Returns (diagram_text, warnings). `warnings` lists any edges that were
    skipped because they referenced a punctuation token or an id not present
    in `tokengraph` -- worth checking, since it usually means the id came
    from a validation problem upstream (see latin_syntax_dspy.validate) --
    plus, if `color_by_verbal_unit` is True and the passage has more than 8
    verbal units, one warning that colors are repeating rather than staying
    distinct (the palette has 8 slots; see _VERBAL_UNIT_PALETTE).
    """
    node_ids = {tok.id for tok in tokengraph if tok.tokentype != "punctuation"}
 
    lines = [f"graph {orientation}"]
    for tok in tokengraph:
        if tok.id not in node_ids:
            continue
        lines.append(f'    {tok.id}["{_escape_label(tok.token)}"]')
 
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
 
    if color_by_verbal_unit:
        assignment = assign_verbal_units(tokengraph)
        colors, color_warnings = assign_verbal_unit_colors(tokengraph, assignment=assignment)
        warnings.extend(color_warnings)
 
        if colors:
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
                    if tok.id in node_ids and assignment.get(tok.id) == unit_id
                ]
                lines.append(f"    class {','.join(member_ids)} {class_names[unit_id]};")
 
    return "\n".join(lines), warnings
 
 
def save_mermaid(
    tokengraph: List[TokenAnalysis],
    path: str,
    orientation: str = "BT",
    color_by_verbal_unit: bool = True,
) -> List[str]:
    """Write the diagram to `path` (e.g. 'analysis.mmd') and return any
    warnings from tokengraph_to_mermaid."""
    diagram, warnings = tokengraph_to_mermaid(
        tokengraph, orientation=orientation, color_by_verbal_unit=color_by_verbal_unit
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(diagram + "\n")
    return warnings