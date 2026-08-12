"""
Render a `tokengraph` (a list of TokenAnalysis, as produced by
latin_syntax_dspy.analyze_passage) as a Mermaid flowchart.

- Every non-punctuation token becomes a node, labelled with the token's
  surface text.
- Every `relatedtoken1`/`relationship1` and `relatedtoken2`/`relationship2`
  pair on a token becomes a labelled edge from that token to the related
  token.

(These are the fields notes.md calls `relation1`/`relationship1` and
`relation2`/`relationship2` -- in models.py the "relation" side is named
`relatedtoken*` to make clear it holds a token id, not the relation label.)

Punctuation tokens are dropped as nodes. Any edge that would point at a
dropped or unrecognized token id is skipped rather than emitted as a broken
reference, and reported back to the caller so silent gaps are visible.
"""

from typing import List, Tuple

from .models import TokenAnalysis

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


def tokengraph_to_mermaid(
    tokengraph: List[TokenAnalysis],
    direction: str = "LR",
) -> Tuple[str, List[str]]:
    """Build a Mermaid `graph` diagram from a tokengraph.

    Returns (diagram_text, warnings). `warnings` lists any edges that were
    skipped because they referenced a punctuation token or an id not present
    in `tokengraph` -- worth checking, since it usually means the id came
    from a validation problem upstream (see latin_syntax_dspy.validate).
    """
    node_ids = {tok.id for tok in tokengraph if tok.tokentype != "punctuation"}

    lines = [f"graph {direction}"]
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
            if related_id not in node_ids:
                warnings.append(
                    f"skipped edge {tok.id} -[{label}]-> {related_id}: "
                    f"target is punctuation or not in tokengraph"
                )
                continue
            lines.append(f'    {tok.id} -->|{_escape_label(label)}| {related_id}')

    return "\n".join(lines), warnings


def save_mermaid(tokengraph: List[TokenAnalysis], path: str, direction: str = "LR") -> List[str]:
    """Write the diagram to `path` (e.g. 'analysis.mmd') and return any
    warnings from tokengraph_to_mermaid."""
    diagram, warnings = tokengraph_to_mermaid(tokengraph, direction=direction)
    with open(path, "w", encoding="utf-8") as f:
        f.write(diagram + "\n")
    return warnings
