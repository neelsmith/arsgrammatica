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
from .verbal_units import assign_verbal_units
 
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
 
 
# Categorical palette for coloring verbal units: 8 (fill, stroke, text)
# triples, in a fixed order chosen so adjacent slots stay distinguishable
# under color-vision deficiency as well as normal vision. Pastel-hued by
# request: each `fill` is a light, low-saturation tint; `stroke` is that
# same hue at full saturation (the vivid color a non-pastel categorical
# palette would use), giving each swatch a colored outline instead of a
# colored fill as its primary identity cue; `text` is black throughout --
# every one of these fills has strong contrast against black (all comfortably
# above the WCAG AA text threshold of 4.5:1, several above 10:1).
#
# Pushing this light necessarily fails the dataviz skill's OKLCH lightness
# ceiling (0.77 for a light surface) -- true pastel and that ceiling are
# mutually exclusive, since the ceiling exists specifically to keep marks
# from reading as washed-out. That gate was designed for un-labeled marks
# (points, bars) where color alone carries identity; every node in this
# diagram already carries its own visible text label, which is the
# mitigation the skill itself prescribes for exactly this trade-off. What
# was NOT relaxed: adjacent-pair separation. This ordering was tuned
# (see scripts/validate_palette.js in Claude's dataviz skill) so it still
# clears both the CVD separation target (worst adjacent ΔE 10.6, target
# ≥8) and the normal-vision floor (worst adjacent ΔE 18.1, floor ≥15) --
# the checks that actually determine whether two colors can be told apart.
# Cycles (mod 8) if a sentence has more than 8 verbal units -- see
# _VERBAL_UNIT_PALETTE's use in tokengraph_to_mermaid(), which reports this
# as a warning rather than silently repeating colors.
_VERBAL_UNIT_PALETTE = [
    ("#82bbff", "#2a78d6", "#000000"),  # blue
    ("#ffa682", "#eb6834", "#000000"),  # orange
    ("#70ffcc", "#1baf7a", "#000000"),  # aqua
    ("#ffd170", "#eda100", "#000000"),  # yellow
    ("#ff94bc", "#e87ba4", "#000000"),  # magenta
    ("#7aff7a", "#008300", "#000000"),  # green
    ("#a494ff", "#4a3aa7", "#000000"),  # violet
    ("#ff9594", "#e34948", "#000000"),  # red
]
 
 
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
 
        # Assign each distinct verbal unit id a stable palette slot, in the
        # order its tokens first appear in `tokengraph` (reading order) --
        # not dict/set iteration order, which isn't guaranteed to match.
        unit_order: List[str] = []
        seen_units = set()
        for tok in tokengraph:
            if tok.id not in node_ids:
                continue
            unit_id = assignment.get(tok.id)
            if unit_id is not None and unit_id not in seen_units:
                seen_units.add(unit_id)
                unit_order.append(unit_id)
 
        if len(unit_order) > len(_VERBAL_UNIT_PALETTE):
            warnings.append(
                f"{len(unit_order)} verbal units but only {len(_VERBAL_UNIT_PALETTE)} "
                "distinct colors -- colors repeat and may be ambiguous between units"
            )
 
        if unit_order:
            lines.append("")
            class_names = {}
            for i, unit_id in enumerate(unit_order):
                class_name = f"vu{i}"
                class_names[unit_id] = class_name
                fill, stroke, text = _VERBAL_UNIT_PALETTE[i % len(_VERBAL_UNIT_PALETTE)]
                lines.append(
                    f"    classDef {class_name} fill:{fill},stroke:{stroke},color:{text};"
                )
            for unit_id in unit_order:
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