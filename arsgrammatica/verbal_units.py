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

A second, analogous wrinkle: a noun or pronoun in a true "ablative
absolute" relation to a verb (syntax_model.md's "verbal units with
participles") is syntactically absolute -- it does not function inside
that verb's own clause, even though its own relatedtoken1 points straight
at that verb. Grammatically it belongs instead to the circumstantial
participle it agrees with, which always relates back to that same noun
via "circumstantial participle" (possibly an implied participle of *sum*,
when Latin has no real participle to use -- see IMPLIED_TOKENTYPES).
Example: in "paucis interiectis diebus ... Sex. Tarquinius inscio
Collatino ... venit" (Livy), both *diebus* and *Collatino* relate to
*venit* as "ablative absolute", but *interiectis* (a real participle)
relates to *diebus*, and an implied participle of *sum* relates to
*Collatino*, both via "circumstantial participle" -- so *diebus* and
*Collatino* (and anything that in turn chains through them, e.g. an
adjective or apposition) belong to *interiectis*'s and the implied
participle's own verbal units respectively, NOT to *venit*'s. This is
checked the same way as the "unit verb" wrinkle above -- via a reverse
index -- but only overrides the default forward chase when the noun's
own outgoing relation actually is "ablative absolute"; a noun a
circumstantial participle agrees with that otherwise fits normally into
the surrounding clause (e.g. "eum" as direct object in "eum advenientem
... accepere") keeps that normal relation and is NOT redirected --
syntax_model.md's own distinction between the two cases is exactly this
outgoing-relation label.

A third case needs NO wrinkle at all, despite looking similar at first
glance: a participle's own antecedent can be an "implied subject" token
(models.py's IMPLIED_TOKENTYPES) rather than a real noun, when the
participle agrees with a governing verb's own unexpressed subject (e.g.
"Recordatus" and the implied subject of "ait" in "Recordatusque somniorum
ait..."). That implied token is not itself a verbal-unit anchor
(`verbalunitid` is unset), and its own outgoing relation is an ordinary
"subject" -> the verb, not "ablative absolute" -- so it resolves through
the plain forward chase below exactly like "eum" above, landing in the
verb's own unit, and the participle that points to it resolves the same
way in turn. No tokentype check anywhere in this module is needed for
this to work correctly.
"""
 
from typing import Dict, List, Optional, Tuple
 
from .models import TokenAnalysis
 
_UNIT_VERB = "unit verb"
_CIRCUMSTANTIAL_PARTICIPLE = "circumstantial participle"
_ABLATIVE_ABSOLUTE = "ablative absolute"

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

# A dedicated "caution" color for implied/elided tokens (models.py's
# IMPLIED_TOKENTYPES: "implied sum", "continued discourse", "implied
# subject") -- a strong,
# saturated amber, deliberately NOT drawn from _VERBAL_UNIT_PALETTE above
# (whose pastel tints it would otherwise be confusable with, especially the
# "yellow" slot) and deliberately not pastel itself, so it reads as "this
# marks something MISSING from the surface text" rather than as just
# another clause's color. Every consumer that renders an implied token
# (currently rendering.py's tokengraph_to_html()/tokengraph_to_depth_html()
# and mermaid.py's tokengraph_to_mermaid()) uses this SAME color for it,
# regardless of which verbal unit the token itself anchors -- the warning
# is about the token's own kind, not about which clause it's in. Black
# text keeps strong contrast against the fill, same convention as every
# palette slot above.
_IMPLIED_TOKEN_COLOR = ("#ffc107", "#7a5200", "#000000")  # amber warning



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

    A true ablative-absolute noun (its own outgoing relation is "ablative
    absolute", not some normal clause role) is redirected to the verbal
    unit of the circumstantial participle it agrees with, rather than to
    the verb its own relatedtoken1 points at -- see this module's
    docstring for the full "paucis interiectis diebus ... inscio
    Collatino ... venit" example. Anything that in turn chains through
    that noun (an adjective, an appositive) follows it into the
    participle's unit too, since this redirect happens once, at the noun
    itself, and every other resolution is unchanged.
    """
    by_id = {tok.id: tok for tok in tokengraph}

    # Reverse index: for every token that some OTHER token points at via a
    # "unit verb" relation, record who points at it. Per syntax_model.md,
    # a "unit verb" target is always either the literal sentinel 'root'
    # (from an independent verb -- never a real token) or a subordinating
    # conjunction/relative pronoun's id (from a dependent verb) -- so a hit
    # here always means "this token introduces the pointing verb's clause."
    introduces_clause_for: Dict[str, str] = {}
    # Reverse index: for every token that some OTHER token points at via a
    # "circumstantial participle" relation, record who points at it (the
    # participle -- real or implied -- that agrees with it). Used below to
    # redirect a TRUE ablative-absolute noun to that participle's own
    # verbal unit instead of the verb it otherwise points at; a noun a
    # participle agrees with that fits normally into the clause (its own
    # outgoing relation isn't "ablative absolute") is left alone and keeps
    # resolving normally, so this index is consulted but not always used.
    circumstantial_participle_for: Dict[str, str] = {}
    for tok in tokengraph:
        for related_field, label_field in (
            ("relatedtoken1", "relationship1"),
            ("relatedtoken2", "relationship2"),
        ):
            related = getattr(tok, related_field)
            label = getattr(tok, label_field)
            if related is None or related == "root":
                continue
            if label == _UNIT_VERB:
                introduces_clause_for[related] = tok.id
            elif label == _CIRCUMSTANTIAL_PARTICIPLE:
                circumstantial_participle_for[related] = tok.id

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
            participle_id = circumstantial_participle_for.get(tid)
            is_ablative_absolute = (
                tok.relationship1 == _ABLATIVE_ABSOLUTE
                or tok.relationship2 == _ABLATIVE_ABSOLUTE
            )
            if participle_id is not None and is_ablative_absolute:
                result = resolve(participle_id)

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


def find_governing_verbal_expression(
    tokengraph: List[TokenAnalysis],
) -> Dict[str, Optional[str]]:
    """For every verbal expression anchor in `tokengraph` (any token with
    `verbalunitid` set to its own id -- the same convention
    `assign_verbal_units()` relies on), find the *governing* verbal
    expression it is subordinate to: the anchor id its own relatedtoken1
    (falling back to relatedtoken2) chain eventually leads to, following
    through as many intermediate non-anchor tokens as necessary.

    Returns `{anchor id: governing anchor id, or None}`. `None` covers
    BOTH of two different situations, deliberately not distinguished here:
    an independent verb (relatedtoken1 == 'root', nothing to chase) and a
    chase that dead-ends or cycles through non-anchor tokens before ever
    reaching another anchor (a malformed or genuinely disconnected verbal
    expression) -- either way, "no governing verbal expression" is the
    right answer for a caller that just wants "is this subordinate to
    something, and if so what" (e.g. aat_bridge.py's `attgraph()`,
    building an AAT action node's `related_node`, where both cases alike
    mean `related_node = None`). A caller that needs to tell those two
    apart, or wants a warning when the chase genuinely fails, should use
    `compute_subordination_depths()` instead -- it consumes this same
    chase (via this function) but adds exactly that distinction, plus
    warnings, on top.

    One malformed-input case this function does NOT resolve to None:
    two anchors whose own relatedtoken1/2 point directly at EACH OTHER
    (rather than through intermediate tokens). The chase from either one
    hits the OTHER anchor immediately -- an anchor is a hit the moment
    it's reached, before its own further relations are ever followed --
    so each resolves to "the other" as its governing expression, a
    locally self-consistent but globally nonsensical mutual cycle. This
    is unchanged from the original private helper this function was
    extracted from; catching it requires the joint, cross-anchor
    resolution `compute_subordination_depths()`'s own `in_progress`
    bookkeeping does (see its "cycle detected" warning), which a single
    anchor's local chase has no way to see on its own. A caller building
    an AATGraph from a relation graph with this specific defect (an
    actual LM error, not a normal input) would get a graph with two
    actions each listing the other as its own governing action --
    referentially valid (aat.core.validate.validate() has no cycle
    check either) but logically circular.

    The chase itself handles every documented case uniformly, without
    needing to special-case by relationship label, because they all
    eventually resolve to another anchor via forward pointers already in
    the graph -- see `compute_subordination_depths()`'s own docstring for
    the full worked-out case list (unit verb, direct quote/aside/indirect
    statement, circumstantial participle).
    """
    by_id = {tok.id: tok for tok in tokengraph}
    anchor_ids = {tok.id for tok in tokengraph if tok.verbalunitid == tok.id}

    def chase(token_id: str, visited: set) -> Optional[str]:
        """Follow relatedtoken1 (then relatedtoken2) forward from
        `token_id`, returning the first anchor id reached, or None if the
        chain dead-ends or cycles before reaching one. `token_id` itself
        counts as a hit if it's already an anchor (the direct-link cases:
        direct quote, aside, indirect statement)."""
        if token_id in visited:
            return None
        visited.add(token_id)
        if token_id in anchor_ids:
            return token_id
        tok = by_id.get(token_id)
        if tok is None:
            return None
        for field in ("relatedtoken1", "relatedtoken2"):
            target = getattr(tok, field)
            if target is None or target == "root":
                continue
            result = chase(target, visited)
            if result is not None:
                return result
        return None

    def parent_of(anchor_id: str) -> Optional[str]:
        tok = by_id[anchor_id]
        for field in ("relatedtoken1", "relatedtoken2"):
            target = getattr(tok, field)
            if target is None or target == "root":
                continue
            result = chase(target, visited=set())
            if result is not None and result != anchor_id:
                return result
        return None

    return {anchor_id: parent_of(anchor_id) for anchor_id in anchor_ids}


def compute_subordination_depths(
    tokengraph: List[TokenAnalysis],
) -> Tuple[Dict[str, Optional[int]], List[str]]:
    """Compute each verbal expression's *depth of subordination*: the
    number of verbal expressions it is removed from an independent ("root")
    clause. An independent verb is depth 0; a verb it introduces (a
    dependent clause, a direct quote, an aside) is depth 1; a verbal
    expression THAT verb in turn introduces (e.g. an indirect statement
    inside a dependent clause) is depth 2; and so on.

    A "verbal expression" here is any token that anchors one -- i.e. any
    token with `verbalunitid` set to its own id (the same convention
    `assign_verbal_units()` relies on). For each anchor, this function
    finds its *parent* anchor -- the verbal expression it's subordinate to
    -- by following the anchor's own relatedtoken1 (falling back to
    relatedtoken2), through as many intermediate non-anchor tokens as
    necessary, until it lands on another anchor. This one chase handles
    every documented case uniformly, without needing to special-case by
    relationship label, because they all eventually resolve to another
    anchor via forward pointers already in the graph:

    - unit verb (independent): relatedtoken1 == 'root' -> no parent, depth 0.
    - unit verb (dependent): relatedtoken1 -> a subordinating conjunction or
      relative pronoun (not itself an anchor) -> ITS relatedtoken1 -> the
      superior verb (a conjunction) or an antecedent noun (a relative
      pronoun), the latter requiring one more hop through the noun's own
      relation to reach the verb it depends on.
    - direct quote / aside / indirect statement: relatedtoken1 -> the verb
      of the clause it interrupts, is framed by, or (for an indirect-
      statement infinitive) governs it, directly (no intermediate token).
    - circumstantial participle: relatedtoken1 -> the noun/pronoun it
      agrees with (not itself an anchor) -> that noun's own relation,
      either its normal role in the surrounding clause (one more hop to a
      verb) or, for a true ablative absolute, 'ablative absolute' pointing
      directly at the main verb.

    Returns `({anchor id: depth or None}, warnings)`. A depth of `None`
    means the chase from that anchor never reached another anchor (a
    malformed or genuinely disconnected verbal expression -- e.g. an
    indirect-statement infinitive predating this convention, with no
    relatedtoken1 of its own at all) or a cycle was detected; `warnings`
    names which anchor(s) and why, mirroring `tokengraph_to_mermaid()`'s
    warnings-list convention rather than raising.
    """
    by_id = {tok.id: tok for tok in tokengraph}
    anchor_ids = {tok.id for tok in tokengraph if tok.verbalunitid == tok.id}

    warnings: List[str] = []

    # The chase itself -- following relatedtoken1/relatedtoken2 forward
    # until another anchor is reached -- now lives in
    # find_governing_verbal_expression(), shared with aat_bridge.py's
    # attgraph(). Computed once, up front, for every anchor; this is a
    # pure function of `tokengraph` with no dependency on `depths`'
    # memoization state, so precomputing it here for all anchors (instead
    # of the original code's lazy per-call `parent_of()`) changes nothing
    # about the result.
    governing = find_governing_verbal_expression(tokengraph)

    depths: Dict[str, Optional[int]] = {}
    in_progress: set = set()

    def depth_of(anchor_id: str) -> Optional[int]:
        if anchor_id in depths:
            return depths[anchor_id]
        tok = by_id[anchor_id]
        if tok.relatedtoken1 == "root":
            depths[anchor_id] = 0
            return 0

        if anchor_id in in_progress:
            warnings.append(
                f"cycle detected resolving the governing verbal expression "
                f"for {anchor_id!r} -- leaving its depth (and its parent's) "
                f"unresolved"
            )
            return None
        in_progress.add(anchor_id)

        parent = governing.get(anchor_id)
        if parent is None:
            warnings.append(
                f"could not find a governing verbal expression for "
                f"{anchor_id!r} -- leaving its depth unresolved"
            )
            result = None
        else:
            parent_depth = depth_of(parent)
            result = None if parent_depth is None else parent_depth + 1

        in_progress.discard(anchor_id)
        depths[anchor_id] = result
        return result

    for anchor_id in anchor_ids:
        depth_of(anchor_id)

    return depths, warnings


def compute_aat_depths(tokengraph: List[TokenAnalysis]) -> Dict[str, int]:
    """Compute each verbal expression's depth the way it would come out if
    you built an `aat` package AATGraph from this same `tokengraph` (via
    `aat_bridge.attgraph()`) and walked each action node's own
    `related_node` chain to the top -- an independent action (no governing
    action) is depth 0, one it governs is depth 1, and so on -- WITHOUT
    actually building that graph or depending on `aat` being installed at
    all: `attgraph()` populates every action's `related_node` from this
    same module's `find_governing_verbal_expression()`, so walking that
    map directly here reproduces the identical numbers `graph.
    governing_action()` chains would.

    Returns `{anchor id: depth}` -- one entry per verbal-expression anchor
    (same set `compute_subordination_depths()` covers), and, unlike that
    function, EVERY anchor gets a plain `int`, never `None`, and this never
    returns any warnings. That's not an oversight: an AATNode's
    `related_node` is either "points at a real governing action" or
    `None` -- there's no third state for "a governing expression should
    exist here but the chase couldn't find one" (compute_subordination_
    depths()'s "unresolved, needs a warning" case). So this function folds
    that case into the same bucket as a genuinely independent verb (depth
    0) instead of excluding it, exactly as an AATGraph itself would have
    no way to tell the two apart. For every WELL-FORMED sentence (which is
    to say: every one of this codebase's own gold fixtures) the two
    functions agree exactly, hop for hop -- they're driven by the same
    underlying chase. They can only diverge on malformed input: an anchor
    whose own chase never reaches another anchor at all (relatedtoken1 not
    'root', but nothing resolvable) is `None`/excluded/warned-about from
    `compute_subordination_depths()`, but depth 0 here.

    A mutual cycle -- two anchors relating directly to each other, so each
    resolves to "the other" as its own governing expression (see
    `find_governing_verbal_expression()`'s own docstring for why its local
    chase can't detect this as a cycle at all) -- is the one case where
    this function's numbers are not just "collapsed" but genuinely
    arbitrary: walking the chain here still has to terminate somewhere, so
    whichever anchor's own resolution happens to be demanded FIRST ends up
    one level shallower than the other, an artifact of iteration order
    rather than anything meaningful in the relation graph. This is the
    same malformed-LM-output scenario `compute_subordination_depths()`
    detects and warns about explicitly (leaving both anchors' depth
    `None`) -- a caller that needs to tell "confidently ranked" apart from
    "arbitrarily broke a tie in a cycle" should use that function instead,
    or run `find_unanchored_coordinated_verbs()`/`validate()` upstream,
    since a real cycle like this only comes from malformed relations to
    begin with.

    Used by `mermaid.tokengraph_to_mermaid()`'s `rank_by_depth` option, so
    the invisible same-depth layout links in the full syntax diagram line
    up with the depth an AAT graph of the same sentence would show, rather
    than arsgrammatica's own (richer, but AAT-incompatible on unresolved
    anchors) subordination-depth notion -- see that function's own
    docstring. `compute_subordination_depths()`/`max_subordination_depth()`
    /`tokengraph_to_depth_html()`'s depth-indented HTML view are unaffected
    by this function and keep using the original notion, unchanged.
    """
    governing = find_governing_verbal_expression(tokengraph)

    depths: Dict[str, int] = {}
    in_progress: set = set()

    def depth_of(anchor_id: str) -> int:
        if anchor_id in depths:
            return depths[anchor_id]
        if anchor_id in in_progress:
            # A cycle this function's own local walk can't resolve
            # meaningfully (see this function's own docstring) -- treat as
            # "no governing expression found", same as a genuinely
            # independent action, rather than recursing forever.
            return 0
        in_progress.add(anchor_id)

        parent = governing.get(anchor_id)
        result = 0 if parent is None else depth_of(parent) + 1

        in_progress.discard(anchor_id)
        depths[anchor_id] = result
        return result

    for anchor_id in governing:
        depth_of(anchor_id)

    return depths


def max_subordination_depth(
    tokengraph: List[TokenAnalysis],
    depths: Optional[Dict[str, Optional[int]]] = None,
) -> Optional[int]:
    """Return the deepest level of subordination reached anywhere in
    `tokengraph` -- the highest value `compute_subordination_depths()`
    assigns to any verbal expression. Root/independent clauses are depth
    0, so this is also the upper end of the valid `depth` range for
    `rendering.tokengraph_to_depth_html()`'s own `depth` parameter (whose
    valid range is 0, root clauses only, through this function's return
    value, everything).

    Pass `depths` (the first element of `compute_subordination_depths()`'s
    return value) if the caller already computed it, to avoid re-deriving
    it here; otherwise it's computed internally (any resolution warnings
    are silently dropped in that case -- call
    `compute_subordination_depths()` directly first if the caller also
    needs those).

    Returns `None` if `tokengraph` has no verbal expressions at all (an
    empty passage, or one with none of the three constructions
    syntax_model.md counts as one), or if every anchor's own depth came
    back unresolved (see `compute_subordination_depths()`'s own
    warnings for why an anchor might be unresolved -- a relation cycle, or
    a governing verbal expression that couldn't be found). Otherwise
    returns the maximum of every RESOLVED anchor's depth, ignoring
    unresolved ones rather than letting a single bad anchor blank out the
    whole result.
    """
    if depths is None:
        depths, _warnings = compute_subordination_depths(tokengraph)

    resolved = [d for d in depths.values() if d is not None]
    if not resolved:
        return None
    return max(resolved)


def find_unanchored_coordinated_verbs(tokengraph: List[TokenAnalysis]) -> List[str]:
    """Heuristic sanity check for a specific, observed live-LM mistake: a
    coordinating conjunction that pairs two verbal expressions (see
    latin_syntax_dspy.py's docstring) is supposed to leave BOTH conjuncts
    anchoring their own verbal unit -- each with its own `verbalunitid`
    (and its own `verbalunits` entry). In practice, the LM sometimes drops
    this for the second conjunct, especially when that verb also governs
    further subordinate structure of its own (a dependent clause, an
    indirect statement) -- see gold_examples.py's
    coordinating_conjunction_dedit_et_dixit_esse fixture for a real example
    (dixit, coordinated with dedit via "et" AND governing its own indirect
    statement, came back from a live model with no verbalunitid at all).

    This is NOT the same kind of check as validate() (referential id
    integrity) or compute_subordination_depths()'s warnings (a resolvable-
    but-broken relation graph) -- both of those only catch a problem if
    the tokengraph is already self-inconsistent. This function catches a
    tokengraph that's perfectly well-formed and internally consistent, but
    still probably WRONG, by looking for an asymmetry a correct analysis
    should never produce.

    The heuristic: find every "coordinating conjunction" token that uses
    BOTH relatedtoken1 and relatedtoken2 (the two-conjunct pairing case --
    see that relation's own note about the one-sided, sentence-initial
    exception, which this deliberately ignores since there's only one
    conjunct to check there). For each such pair, if EXACTLY ONE of the
    two joined tokens is a recognized verbal-unit anchor (`verbalunitid`
    set to its own id) and the other is not, that asymmetry is flagged: if
    the conjunction is genuinely pairing two nouns/adjectives/
    prepositional phrases, NEITHER side would be an anchor; if it's
    correctly pairing two verbal expressions, BOTH sides would be. Only
    the lopsided case -- one anchored, one not -- is unusual enough to be
    worth a human look.

    This pairwise shape doesn't apply to a repeated connector coordinating
    a series of three or more items (polysyndeton, e.g. 'et...et...et' --
    see latin_syntax_dspy.py's docstring): there, every connector's own
    relatedtoken2 points at a NEIGHBORING CONNECTOR, not at a second
    conjunct, so this heuristic's asymmetry check would misfire on a
    series that happens to coordinate verbal expressions (the neighboring
    connector is never itself a verbal-unit anchor, so one side would
    always look "unanchored" even when the analysis is entirely correct).
    A pair is therefore skipped whenever relatedtoken2 resolves to a token
    that is itself a coordinating-conjunction connector.

    Returns a list of warning strings (empty if nothing looks suspicious),
    the same "degrade visibly, don't raise" convention every other
    warnings-returning function in this codebase uses. This is a
    heuristic, not a guarantee: it can only flag the asymmetry itself, not
    confirm the unanchored side really was meant to be a verb, so a clean
    result here isn't a substitute for validate() or a human read of the
    analysis -- and a flagged result deserves a look rather than an
    automatic "fix," since guessing the right verbalunitid/relation back
    in could just as easily paper over a different, unrelated mistake.
    """
    by_id = {tok.id: tok for tok in tokengraph}
    anchor_ids = {tok.id for tok in tokengraph if tok.verbalunitid == tok.id}

    warnings: List[str] = []
    seen_pairs = set()

    for tok in tokengraph:
        if not (
            tok.relatedtoken1 is not None
            and tok.relatedtoken1 != "root"
            and tok.relationship1 == "coordinating conjunction"
            and tok.relatedtoken2 is not None
            and tok.relatedtoken2 != "root"
            and tok.relationship2 == "coordinating conjunction"
        ):
            continue

        pair = (tok.relatedtoken1, tok.relatedtoken2)
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)

        first_id, second_id = pair
        second_tok = by_id.get(second_id)
        if second_tok is not None and (
            second_tok.relationship1 == "coordinating conjunction"
            or second_tok.relationship2 == "coordinating conjunction"
        ):
            # relatedtoken2 points at a FELLOW connector, not at a second
            # conjunct -- the signature of the series/polysyndeton pattern
            # (see this function's own docstring), where this heuristic's
            # pairwise-specific asymmetry check doesn't apply.
            continue

        first_anchored = first_id in anchor_ids
        second_anchored = second_id in anchor_ids
        if first_anchored == second_anchored:
            # Both anchored (a correctly paired pair of verbs) or neither
            # (almost certainly a noun/adjective/prepositional-phrase
            # pair) -- either way, not the asymmetry this check looks for.
            continue

        anchored_id, unanchored_id = (
            (first_id, second_id) if first_anchored else (second_id, first_id)
        )
        anchored_text = by_id[anchored_id].token if anchored_id in by_id else anchored_id
        unanchored_text = by_id[unanchored_id].token if unanchored_id in by_id else unanchored_id
        warnings.append(
            f"{tok.id} ({tok.token!r}) coordinates {anchored_id} "
            f"({anchored_text!r}), which anchors its own verbal unit, with "
            f"{unanchored_id} ({unanchored_text!r}), which does not -- if "
            "this conjunction is meant to join two verbal expressions "
            "(rather than a noun/adjective/prepositional-phrase pair), "
            f"{unanchored_id} is likely missing its own verbalunitid and "
            "'unit verb'/'root' (or dependent-clause) relation."
        )

    return warnings
