"""
Partitions a `tokengraph` into the verbal units its own relations already
imply, so every token can be labelled "this token belongs to verbal unit
X" (or to none) -- e.g. for coloring a Mermaid diagram by clause (see
mermaid.py), or for any future visualization that wants the same grouping.
 
The key idea: a verbal unit's anchor token (the finite verb, infinitive, or
predicate-sense participle that owns an entry in `verbalunits` -- see
models.py's VerbalExpression) already marks itself in the tokengraph via
`verbalunitid` (set to its own id). Every OTHER token can be assigned to
whichever anchor its own relatedtoken1/relatedtoken2 chain eventually
leads to -- with one wrinkle, handled specially below.
 
The wrinkle: "subordinating conjunction" and "relative pronoun" are
themselves cross-clause pointers. A subordinating conjunction's own
relatedtoken1 points at the OUTER clause's verb (the one it modifies,
e.g. "cum" -> "pergit" in "Hercules cum gregem perlustrasset, pergit..."),
and a relative pronoun's own relatedtoken1 points at its antecedent, which
can likewise sit in an outer/different clause (e.g. "quibus" -> "Latini").
Followed naively, both would pull the conjunction/pronoun itself into the
OUTER clause it modifies or refers back to -- backwards from how a reader
would group the sentence: "cum" reads as part of the dependent clause it
introduces ("cum gregem perlustrasset"), not part of the main clause
("pergit ad proximam speluncam") it happens to modify.
 
The fix: syntax_model.md's own "unit verb (dependent)" rule already
records the *reverse* link explicitly -- every dependent verb's own
relatedtoken1 points AT its subordinating conjunction or relative pronoun,
with relationship1 = "unit verb" (see latin_syntax_dspy.py's docstring).
That reverse link is the authoritative "this token introduces clause V"
signal, so it's checked first, for every token: if some verb V has a
"unit verb" relation pointing at this token, this token belongs to V's
verbal unit, full stop -- its own outgoing relations (the antecedent link,
the outer-clause-modifies link) are not used to override that. Only when
no such reverse link exists does a token fall back to following its own
relatedtoken1/relatedtoken2 chain forward.
"""
 
from typing import Dict, List, Optional, Tuple
 
from .models import TokenAnalysis
 
_UNIT_VERB = "unit verb"
 
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
# Lives here (rather than in mermaid.py, where it originated) so every
# consumer that wants "the same verbal-unit colors as the mermaid graph" --
# currently mermaid.py's own node coloring and rendering.py's
# tokengraph_to_html() -- shares one definition and one ordering rule
# (assign_verbal_unit_colors(), below) instead of each re-deriving it and
# risking drift.
#
# Pushing this light necessarily fails the dataviz skill's OKLCH lightness
# ceiling (0.77 for a light surface) -- true pastel and that ceiling are
# mutually exclusive, since the ceiling exists specifically to keep marks
# from reading as washed-out. That gate was designed for un-labeled marks
# (points, bars) where color alone carries identity; every node/span this
# palette colors already carries its own visible text label, which is the
# mitigation the skill itself prescribes for exactly this trade-off. What
# was NOT relaxed: adjacent-pair separation. This ordering was tuned (see
# scripts/validate_palette.js in Claude's dataviz skill) so it still clears
# both the CVD separation target (worst adjacent ΔE 10.6, target ≥8) and
# the normal-vision floor (worst adjacent ΔE 18.1, floor ≥15) -- the checks
# that actually determine whether two colors can be told apart.
# Cycles (mod 8) if a sentence has more than 8 verbal units -- see
# assign_verbal_unit_colors(), which reports this as a warning rather than
# silently repeating colors.
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
 
 
def assign_verbal_units(tokengraph: List[TokenAnalysis]) -> Dict[str, Optional[str]]:
    """Return {token id: verbal unit id or None}, one entry per token in
    `tokengraph` (including punctuation and unrelated tokens, so every id
    is accounted for -- callers that only care about assigned tokens can
    filter out the None values themselves).
 
    A verbal unit's own anchor token is assigned to itself (its
    `verbalunitid`). Every other token is assigned to the verbal unit its
    relations resolve to, per this module's docstring; a token with no
    resolvable relation (e.g. a bare accusative of place, an enclitic, an
    emphatic pronoun left unrelated per syntax_model.md's "Incomplete
    status") gets None.
    """
    by_id = {tok.id: tok for tok in tokengraph}
 
    # Reverse index: for every token that some OTHER token points at via a
    # "unit verb" relation, record who points at it. Per syntax_model.md,
    # a "unit verb" target is always either the literal sentinel 'root'
    # (from an independent verb -- never a real token) or a subordinating
    # conjunction/relative pronoun's id (from a dependent verb) -- so a hit
    # here always means "this token introduces the pointing verb's clause."
    introduces_clause_for: Dict[str, str] = {}
    for tok in tokengraph:
        for related_field, label_field in (
            ("relatedtoken1", "relationship1"),
            ("relatedtoken2", "relationship2"),
        ):
            related = getattr(tok, related_field)
            label = getattr(tok, label_field)
            if related is not None and related != "root" and label == _UNIT_VERB:
                introduces_clause_for[related] = tok.id
 
    resolved: Dict[str, Optional[str]] = {}
    in_progress: set = set()
 
    def resolve(tid: str) -> Optional[str]:
        if tid in resolved:
            return resolved[tid]
        tok = by_id.get(tid)
        if tok is None:
            return None
 
        if tok.verbalunitid is not None:
            resolved[tid] = tok.verbalunitid
            return tok.verbalunitid
 
        if tid in in_progress:
            # A cycle in the relation graph (malformed LM output) -- bail
            # out on this token rather than recursing forever.
            return None
        in_progress.add(tid)
 
        result = None
 
        clause_verb_id = introduces_clause_for.get(tid)
        if clause_verb_id is not None:
            result = resolve(clause_verb_id)
 
        if result is None:
            for related_field in ("relatedtoken1", "relatedtoken2"):
                related = getattr(tok, related_field)
                if related is None or related == "root":
                    continue
                result = resolve(related)
                if result is not None:
                    break
 
        in_progress.discard(tid)
        resolved[tid] = result
        return result
 
    for tid in by_id:
        resolve(tid)
 
    return resolved
 
 
def assign_verbal_unit_colors(
    tokengraph: List[TokenAnalysis],
    assignment: Optional[Dict[str, Optional[str]]] = None,
) -> Tuple[Dict[str, Tuple[str, str, str]], List[str]]:
    """Assign each verbal unit found in `tokengraph` a stable (fill, stroke,
    text) triple from `_VERBAL_UNIT_PALETTE`, using the exact ordering rule
    `tokengraph_to_mermaid()` uses for its node coloring -- so any other
    caller wanting "the same colors as the mermaid graph" (currently
    rendering.py's `tokengraph_to_html()`) gets an identical mapping without
    re-deriving the rule itself.
 
    Order is by first appearance of each verbal unit among tokengraph's
    *non-punctuation* tokens, since those are the only tokens that become
    mermaid nodes at all -- a verbal unit whose earliest token happens to be
    punctuation (it can't be: punctuation tokens aren't assigned to a
    verbal unit's anchor, but could in principle inherit one from a
    relation) still gets ordered by its first non-punctuation member.
 
    Pass `assignment` (the result of `assign_verbal_units(tokengraph)`) if
    the caller already computed it, to avoid re-deriving it here; otherwise
    it's computed internally.
 
    Returns `({verbal unit id: (fill, stroke, text)}, warnings)` --
    `warnings` holds one entry, with the same wording
    `tokengraph_to_mermaid()` uses, if there are more distinct verbal units
    than palette slots (colors repeat past the 8th unit). A verbal unit id
    absent from the returned dict was never assigned to any non-punctuation
    token -- callers should treat that the same as "no verbal unit" (no
    coloring), same as `tokengraph_to_mermaid()` does.
    """
    if assignment is None:
        assignment = assign_verbal_units(tokengraph)
 
    non_punctuation_ids = {tok.id for tok in tokengraph if tok.tokentype != "punctuation"}
 
    unit_order: List[str] = []
    seen_units = set()
    for tok in tokengraph:
        if tok.id not in non_punctuation_ids:
            continue
        unit_id = assignment.get(tok.id)
        if unit_id is not None and unit_id not in seen_units:
            seen_units.add(unit_id)
            unit_order.append(unit_id)
 
    warnings: List[str] = []
    if len(unit_order) > len(_VERBAL_UNIT_PALETTE):
        warnings.append(
            f"{len(unit_order)} verbal units but only {len(_VERBAL_UNIT_PALETTE)} "
            "distinct colors -- colors repeat and may be ambiguous between units"
        )
 
    colors = {
        unit_id: _VERBAL_UNIT_PALETTE[i % len(_VERBAL_UNIT_PALETTE)]
        for i, unit_id in enumerate(unit_order)
    }
    return colors, warnings