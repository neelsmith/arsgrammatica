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
 
from typing import Dict, List, Optional
 
from .models import TokenAnalysis
 
_UNIT_VERB = "unit verb"
 
 
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