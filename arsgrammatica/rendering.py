"""
Reconstructs readable text from a tokengraph (a list of TokenAnalysis, as
produced by latin_syntax_dspy.analyze/pipeline.py), in two forms:
`tokengraph_to_text()` for plain text, and `tokengraph_to_html()` for HTML
with lexical tokens wrapped in verbal-unit-colored spans (see that
function's own docstring). Both are the inverse, in spirit, of
segmentation: turn tokens back into the kind of surface text a person would
actually write, rather than `" ".join(tok.token for tok in tokengraph)`,
which puts a space before every token including punctuation and enclitics
(see pipeline.py's _render_sentence_text() docstring, which flags exactly
this: "virumque" would round-trip as "virum que"). This module needs
`tokentype` to decide spacing, so it operates on TokenAnalysis
(post-SentenceAnalysis), not the plain pre-analysis Token list segmentation
produces -- tokentype isn't known yet at that earlier stage.
 
Every token is classified as one of:
 
- **right-joining**: no space between it and the token that FOLLOWS it.
  Opening parentheses/brackets, and the first quote of a quote pair (see
  below), are right-joining. A right-joining token itself is always
  preceded by a space (as stated -- this isn't conditioned on what came
  before it, unlike the "normal" category below; two right-joining tokens
  in a row, e.g. "((", literally get a space between them under this rule
  -- an edge case the spec doesn't carve out an exception for, so this
  implementation doesn't invent one).
- **left-joining**: attaches directly to whatever precedes it, no space,
  ever. The default for punctuation -- periods, commas, semicolons,
  hyphens, and closing parentheses/brackets -- and also the second quote
  of a quote pair.
- **normal** (lexical, numeral, praenomen, and abbreviation): gets a space
  before it, UNLESS the immediately preceding token was right-joining, in
  which case it attaches directly with no space. Implemented as "anything
  that isn't enclitic or punctuation," so this also covers any future
  tokentype value without needing a code change here.
 
**Enclitic tokens are a fourth case not given a rule in the original
request**, handled here by inference rather than left undefined: an
enclitic (e.g. "que" split off of "virumque") is bound directly to the
token before it in real Latin orthography, with no space, regardless of
what that preceding token was -- exactly the case pipeline.py's own
docstring flags as a known gap. Enclitics are therefore treated as
unconditionally no-space-before, same as left-joining, but tracked as
their own case since (unlike true left-joining tokens) an enclitic does
not make the token *after* it attach directly -- only right-joining does
that.
 
**Quote pairing** assumes non-nested pairs of the same literal character:
the Nth occurrence of `"` (or, independently, of `'`) is right-joining if
N is odd (an opening quote) and left-joining if N is even (a closing
quote). This matches the request's own framing ("the first in a pair is
right-joining, the second is left-joining") and handles the realistic
case -- alternating same-glyph quotes marking separate quoted spans, e.g.
`"Tuum est," inquit, "Servi regnum."` -- but not curly/directional quotes
("“"/"”", "‘"/"’"), which weren't part of the request and don't need this
counting trick anyway, since each directional character is unambiguous on
its own.
"""
 
import html
from typing import Dict, List, Optional, Tuple
 
from .models import IMPLIED_TOKENTYPES, TokenAnalysis
from .verbal_units import (
    assign_verbal_units,
    assign_verbal_unit_colors,
    compute_subordination_depths,
)
 
# "Brackets of various kinds" -- parentheses, square brackets, and curly
# braces. Extend these two sets together if other bracket styles (e.g.
# guillemets) need the same opening/closing treatment.
_OPENING_BRACKETS = {"(", "[", "{"}
_CLOSING_BRACKETS = {")", "]", "}"}
 
_QUOTE_CHARS = {'"', "'"}
 
_LEFT = "left"
_RIGHT = "right"
_ENCLITIC = "enclitic"
_NORMAL = "normal"
 
 
def _classify(tok: TokenAnalysis, quote_counts: Dict[str, int]) -> str:
    """Return this token's join behavior: one of _LEFT, _RIGHT, _ENCLITIC,
    or _NORMAL. `quote_counts` is mutated in place to track how many times
    each quote character has been seen so far, across the whole call to
    tokens_to_text() -- it must be threaded through in token order."""
    text = tok.token
 
    if tok.tokentype == _ENCLITIC:
        return _ENCLITIC
 
    if tok.tokentype == "punctuation":
        if text in _OPENING_BRACKETS:
            return _RIGHT
        if text in _CLOSING_BRACKETS:
            return _LEFT
        if text in _QUOTE_CHARS:
            quote_counts[text] = quote_counts.get(text, 0) + 1
            return _RIGHT if quote_counts[text] % 2 == 1 else _LEFT
        # Periods, commas, semicolons, hyphens, and any other punctuation
        # not called out above all default to left-joining.
        return _LEFT
 
    # lexical, numeral, praenomen, abbreviation, and any future tokentype
    # not covered above all get the same "normal" spacing rule.
    return _NORMAL
 
 
def tokengraph_to_text(tokengraph: List[TokenAnalysis]) -> str:
    """Join `tokengraph`'s tokens into one continuous plain-text string,
    per this module's docstring. Tokens are read in list order (the same
    order tokengraph_to_mermaid() and validate() assume)."""
    quote_counts: Dict[str, int] = {}
    pieces: List[str] = []
    previous_class = None

    for tok in tokengraph:
        if tok.tokentype in IMPLIED_TOKENTYPES:
            # An implied/elided token (models.py's IMPLIED_TOKENTYPES) has
            # no surface realization at all -- skip it entirely, exactly as
            # if it weren't in the list, rather than trying to render
            # `None`. previous_class is deliberately left untouched, so the
            # next real token's spacing is decided as if this one weren't
            # here.
            continue
        cls = _classify(tok, quote_counts)
        text = tok.token

        if not pieces:
            # Nothing precedes the first token -- never prepend a space,
            # regardless of this token's own classification.
            pieces.append(text)
        elif cls in (_LEFT, _ENCLITIC):
            pieces.append(text)
        elif cls == _RIGHT:
            pieces.append(" " + text)
        else:  # _NORMAL
            if previous_class == _RIGHT:
                pieces.append(text)
            else:
                pieces.append(" " + text)
 
        previous_class = cls
 
    return "".join(pieces)
 
 
def tokengraph_to_html(tokengraph: List[TokenAnalysis]) -> str:
    """Render `tokengraph` as an HTML string: the same continuous text
    `tokengraph_to_text()` produces -- identical spacing rules, and the same
    punctuation/enclitic/quote-pair handling -- except every **lexical**
    token, every **praenomen** token, every **numeral** token, and every
    **coordinating conjunction** (any token with relationship1 or
    relationship2 == "coordinating conjunction", lexical or not), has its
    text wrapped in a `<span style="...">` colored by the verbal unit it
    belongs to. Colors
    come from `verbal_units.assign_verbal_units()` /
    `assign_verbal_unit_colors()` -- the same assignment and the same
    first-appearance palette ordering `tokengraph_to_mermaid()` uses for its
    node coloring -- so a passage rendered here and the same passage's
    Mermaid diagram color each verbal unit identically.

    The coordinating-conjunction carve-out exists because a conjunction
    like "-que" or "-ve" is typically tokentype "enclitic", not "lexical",
    but `assign_verbal_units()` still resolves it to one of the units it
    coordinates (see that module's docstring) -- e.g. in "arma virumque
    cano.", "que" resolves to the same unit as "cano", same as "arma" and
    "virum" do. Leaving it unwrapped would visually hide that assignment
    even though it's a real one, unlike the other non-lexical tokentypes
    below. A subordinating conjunction (e.g. "cum", "ut") doesn't need this
    carve-out: it's always tokentype "lexical" (a full word, never
    enclitic), so it's already wrapped.

    The praenomen carve-out is the same idea for a different reason:
    syntax_model.md's "Praenomina" section gives every `tokentype`=
    "praenomen" token (e.g. "Sex.") its own real relation -- relatedtoken1
    -> the lexical name it precedes, relationship1 = "praenomen" -- so
    `assign_verbal_units()` resolves it to that name's own verbal unit
    exactly like any other token in the clause (e.g. "Sex." lands in the
    same unit as "Tarquinius", which is "venit"'s). Unlike the
    coordinating-conjunction case, this is keyed on `tokentype` directly
    rather than on the relationship label, matching how the "lexical" half
    of this check works -- every praenomen, by convention, is eligible for
    this treatment, not just ones that happen to already carry the
    relation (a praenomen with nothing to relate to, e.g. "L." in the
    genitive filiation formula "L. f.", simply has no verbal-unit
    assignment and so renders unwrapped anyway, same as an unrelated
    lexical token would).

    The numeral carve-out is for the same reason again: syntax_model.md's
    tokenization section restricts `tokentype`="numeral" to a number
    written NUMERICALLY (Roman or Arabic) -- a number spelled out as an
    ordinary word (e.g. "decem") is "lexical" instead -- but a numeral is
    otherwise an ordinary participant in the clause, able to carry a real
    relation like any noun or adjective (e.g. "XII" modifying "filii" via
    "adjectival", the same relation "decem" would use if spelled out).
    `assign_verbal_units()` resolves that relation exactly like any other,
    so a numeral belonging to a verbal unit is wrapped the same way a
    lexical token would be -- unlike punctuation, a non-conjunction
    enclitic, or an abbreviation, none of which carry that kind of
    ordinary syntactic relation under the current scheme.

    Every other non-lexical, non-praenomen, non-numeral token --
    punctuation, a non-conjunction enclitic (e.g. the interrogative "-ne"),
    and abbreviations -- is still emitted as plain (escaped) text even
    though `assign_verbal_units()` assigns every token, including
    punctuation, to whichever unit its relations resolve to; this function
    just doesn't turn that assignment into a span for anything else. A
    lexical, praenomen, numeral, or coordinating-conjunction token
    belonging to no verbal unit (assignment is `None`, e.g. a bare
    accusative of place) is left unwrapped too, as is one whose unit
    happens to have no non-punctuation member at all and so never got a
    color slot from `assign_verbal_unit_colors()` (should not occur in
    practice for a lexical, praenomen, or numeral token, since it's always
    a non-punctuation member of its own unit, but handled defensively
    rather than assumed).

    An **implied/elided token** (models.py's IMPLIED_TOKENTYPES: "implied
    sum", "continued discourse", "implied subject") is omitted entirely -- same as
    tokengraph_to_text() -- rather than rendered with any span: it has no
    surface text (`tok.token` is always `None`), and unlike
    `tokengraph_to_mermaid()`'s diagram (which DOES show these, as their
    own specially-colored, specially-labeled node -- see that module's own
    docstring), inserting placeholder text into the middle of reconstructed
    prose here would misrepresent what the passage actually says. The
    Mermaid diagram is the one place an implied token's presence is worth
    seeing at all.

    Every token's text is HTML-escaped (`&`, `<`, `>`, and quote characters)
    before being emitted, spans or not -- real Latin text can contain a
    literal `"` or `'` (see the quote-pair handling below), which would
    otherwise be indistinguishable from markup to anything that re-parses
    this output.

    The span's inline style sets both `background-color` (the verbal unit's
    palette `fill`, the same value used as a Mermaid node's `fill`) and
    `color` (the palette's `text` value, currently black for every slot) --
    the latter so the token reads correctly regardless of whatever text
    color the surrounding page has set, matching the explicit black
    `color:` every Mermaid node in that unit also gets.
    """
    assignment = assign_verbal_units(tokengraph)
    colors, _warnings = assign_verbal_unit_colors(tokengraph, assignment=assignment)
    return _tokens_to_html(tokengraph, assignment, colors)


def _tokens_to_html(
    tokens: List[TokenAnalysis],
    assignment: Dict[str, Optional[str]],
    colors: Dict[str, Tuple[str, str, str]],
) -> str:
    """Shared rendering core behind tokengraph_to_html() and
    tokengraph_to_depth_html(): join `tokens` into one HTML string with the
    same spacing/escaping/quote-pairing rules as tokengraph_to_text()
    (including that function's identical omission of implied/elided
    tokens -- see tokengraph_to_html()'s own docstring for why), plus color
    spans for lexical tokens, praenomen tokens, numeral tokens, and
    coordinating conjunctions (see that same docstring for why
    conjunctions, praenomens, and numerals get this too), given an
    already-computed verbal-unit `assignment` and `colors` mapping. Taking
    these as parameters (rather
    than deriving them from `tokens` itself) is what lets
    tokengraph_to_depth_html() render one depth-block's tokens at a time
    while every block still uses the exact same unit-to-color mapping as
    the whole passage, instead of each block re-deriving its own (which
    could disagree if a block happens to contain only some of a unit's
    tokens).

    Quote-pairing state (which occurrence of a `"`/`'` is opening vs.
    closing) resets at the start of `tokens` -- correct for a whole
    tokengraph, but means a quoted span literally split across two depth
    blocks would have its quote parity reset at the block boundary. Not a
    case any current gold fixture exercises.
    """
    quote_counts: Dict[str, int] = {}
    pieces: List[str] = []
    previous_class = None

    for tok in tokens:
        if tok.tokentype in IMPLIED_TOKENTYPES:
            # See tokengraph_to_text()'s identical skip -- no surface text
            # to escape or wrap, and previous_class is left untouched.
            # tokengraph_to_mermaid() is the one place these are shown at
            # all (see tokengraph_to_html()'s own docstring).
            continue
        cls = _classify(tok, quote_counts)
        rendered = html.escape(tok.token)

        is_coordinating_conjunction = (
            tok.relationship1 == "coordinating conjunction"
            or tok.relationship2 == "coordinating conjunction"
        )
        if tok.tokentype in ("lexical", "praenomen", "numeral") or is_coordinating_conjunction:
            unit_id = assignment.get(tok.id)
            color = colors.get(unit_id) if unit_id is not None else None
            if color is not None:
                fill, _stroke, text_color = color
                rendered = (
                    f'<span style="background-color: {fill}; color: {text_color};">'
                    f"{rendered}</span>"
                )

        if not pieces:
            pieces.append(rendered)
        elif cls in (_LEFT, _ENCLITIC):
            pieces.append(rendered)
        elif cls == _RIGHT:
            pieces.append(" " + rendered)
        else:  # _NORMAL
            if previous_class == _RIGHT:
                pieces.append(rendered)
            else:
                pieces.append(" " + rendered)

        previous_class = cls

    return "".join(pieces)


# Left-margin indent per level of subordination depth, in
# tokengraph_to_depth_html()'s default rendering -- purely a CSS layout
# value, tunable per call via that function's `indent_em` parameter.
_DEFAULT_DEPTH_INDENT_EM = 2.0


def tokengraph_to_depth_html(
    tokengraph: List[TokenAnalysis],
    indent_em: float = _DEFAULT_DEPTH_INDENT_EM,
    depth: Optional[int] = None,
) -> Tuple[str, List[str]]:
    """Render `tokengraph` as HTML illustrating each verbal expression's
    *depth of subordination* (see verbal_units.compute_subordination_
    depths()): tokens are assembled sequentially exactly as
    tokengraph_to_html() does -- same spacing, escaping, and verbal-unit
    color highlighting -- but grouped into consecutive-run "blocks" by
    which verbal unit each token belongs to (per assign_verbal_units()),
    each rendered as its own <div> indented by a CSS margin-left of
    `depth * indent_em` em -- 0 for an independent clause, 1 for a clause
    it introduces (a dependent clause, a direct quote, an aside, a
    circumstantial participle/ablative absolute, or -- now that indirect-
    statement infinitives carry their own governing-verb relation -- an
    indirect statement too), 2 for a verbal expression THAT one in turn
    introduces, and so on. All layout is CSS (margin-left/margin-bottom on
    each block's <div>) -- no table or nested-list structure is used to
    produce the indentation.

    `depth`, if given, caps how deep the rendering goes: ONLY blocks whose
    own depth of subordination is <= `depth` are included in the output --
    a block deeper than that is dropped entirely, not rendered empty or
    grayed out. `depth=0` shows root/independent clauses only (and direct
    quotes, asides, and any other depth-0 construction); omit `depth` (or
    pass `None`, the default) to show every block, same as before this
    parameter existed. Valid values run from 0 up to
    verbal_units.max_subordination_depth()'s own return value for this
    `tokengraph` (that function exists specifically to help a caller pick
    a sensible value here); a negative `depth` raises ValueError, since
    there's no clause shallower than root. A `depth` larger than the
    passage's actual maximum is accepted, not an error -- it just means
    "show everything," identical to leaving `depth` unset.

    Block boundaries follow assign_verbal_units()'s token-to-unit
    assignment, with one adjustment: an **enclitic** token never starts a
    new block, even when its own assignment differs from the block
    currently open (see tests/test_rendering.py's coordinating-conjunction
    word-order-mismatch case for exactly this -- an enclitic coordinating
    conjunction like "-que" can resolve to a DIFFERENT verbal unit than the
    word it's orthographically glued to, e.g. in "Hermionenque", and
    starting a new block there would split one Latin word across two
    <div>s). A token with no verbal-unit assignment at all (None --
    typically punctuation, or a token syntax_model.md doesn't document a
    relation for) likewise never starts a new block; it folds into
    whichever block is currently open, so a stray comma or postpositive
    particle doesn't fragment the layout. Leading tokens before the first
    resolvable verbal-unit token (rare) default to depth 0.

    Note that a circumstantial-participle/ablative-absolute noun (e.g.
    "Anco" in "Anco regnante...", or "eum" in "Eum advenientem...")
    resolves, per assign_verbal_units()'s own established convention, to
    whatever unit ITS OWN relation reaches -- typically the outer clause --
    while the participle itself is its own singleton unit; this means a
    circumstantial-participle phrase renders as the noun staying in the
    outer clause's block and the bare participle as its own one-word
    indented block, rather than the whole phrase indenting together. That
    follows directly from the noun's own documented relation (it fits into
    the surrounding clause, or points at the main verb as an ablative
    absolute) and isn't specific to this function.

    A verbal expression whose depth couldn't be resolved (see
    compute_subordination_depths()) renders at depth 0 rather than
    raising, with a warning explaining why -- the same "degrade visibly,
    don't crash" convention tokengraph_to_mermaid() uses.

    Returns (html, warnings), combining assign_verbal_unit_colors()'s
    warnings (colors repeating past 8 verbal units) and
    compute_subordination_depths()'s (an unresolved governing verbal
    expression) -- computed the same way, and returned in full, regardless
    of whether `depth` filters some blocks out of the rendered `html`
    itself.
    """
    if depth is not None and depth < 0:
        raise ValueError(f"depth must be >= 0 (root clauses only), got {depth!r}")

    assignment = assign_verbal_units(tokengraph)
    colors, color_warnings = assign_verbal_unit_colors(tokengraph, assignment=assignment)
    depths, depth_warnings = compute_subordination_depths(tokengraph)
    warnings = color_warnings + depth_warnings

    blocks = []
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
            # Leading token(s) with no verbal-unit assignment yet (or a
            # leading enclitic, in principle) -- open a placeholder block
            # rather than crashing on an empty blocks list below.
            blocks.append((None, []))
        blocks[-1][1].append(tok)

    lines = []
    for unit_id, block_tokens in blocks:
        block_depth = depths.get(unit_id) if unit_id is not None else 0
        if block_depth is None:
            block_depth = 0
        if depth is not None and block_depth > depth:
            # This whole block is deeper than the requested cutoff --
            # drop it entirely rather than rendering an empty/grayed-out
            # placeholder for it.
            continue
        block_html = _tokens_to_html(block_tokens, assignment, colors)
        margin_left = block_depth * indent_em
        lines.append(
            f'<div style="margin-left: {margin_left}em; margin-bottom: 0.35em;">'
            f"{block_html}</div>"
        )

    return "\n".join(lines), warnings
