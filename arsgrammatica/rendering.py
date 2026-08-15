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
(post-SyntaxAnalysis), not the plain pre-analysis Token list segmentation
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
- **normal** (lexical, numeral, praenomen, and -- if `models.py`'s
  `TokenAnalysis.tokentype` ever grows this value -- abbreviation): gets a
  space before it, UNLESS the immediately preceding token was
  right-joining, in which case it attaches directly with no space. Because
  this case is implemented as "anything that isn't enclitic or
  punctuation," no code change is needed here if `tokentype` gains an
  `"abbreviation"` value later (see models.py's TokenAnalysis -- that
  value isn't in the current Literal, only "praenomen" is, even though
  syntax_model.md's own tokenization scheme documents abbreviations as
  their own thing; this function is already forward-compatible with that
  gap closing).
 
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
from typing import Dict, List
 
from .models import TokenAnalysis
from .verbal_units import assign_verbal_units, assign_verbal_unit_colors
 
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
 
    # lexical, numeral, praenomen, and any future tokentype not covered
    # above (e.g. "abbreviation") all get the same "normal" spacing rule.
    return _NORMAL
 
 
def tokengraph_to_text(tokengraph: List[TokenAnalysis]) -> str:
    """Join `tokengraph`'s tokens into one continuous plain-text string,
    per this module's docstring. Tokens are read in list order (the same
    order tokengraph_to_mermaid() and validate() assume)."""
    quote_counts: Dict[str, int] = {}
    pieces: List[str] = []
    previous_class = None
 
    for tok in tokengraph:
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
    token's text is wrapped in a `<span style="...">` colored by the verbal
    unit it belongs to. Colors come from `verbal_units.assign_verbal_units()`
    / `assign_verbal_unit_colors()` -- the same assignment and the same
    first-appearance palette ordering `tokengraph_to_mermaid()` uses for its
    node coloring -- so a passage rendered here and the same passage's
    Mermaid diagram color each verbal unit identically.
 
    Only tokens with `tokentype == "lexical"` get wrapped: punctuation,
    enclitics, numerals, and praenomens are emitted as plain (escaped) text
    even though `assign_verbal_units()` assigns every token, including
    punctuation, to whichever unit its relations resolve to -- this function
    just doesn't turn that assignment into a span for anything but lexical
    tokens, per the request it was built for. A lexical token belonging to
    no verbal unit (assignment is `None`, e.g. a bare accusative of place)
    is left unwrapped too, as is a lexical token whose unit happens to have
    no non-punctuation member at all and so never got a color slot from
    `assign_verbal_unit_colors()` (should not occur in practice, since a
    lexical token IS a non-punctuation member of its own unit, but handled
    defensively rather than assumed).
 
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
 
    quote_counts: Dict[str, int] = {}
    pieces: List[str] = []
    previous_class = None
 
    for tok in tokengraph:
        cls = _classify(tok, quote_counts)
        rendered = html.escape(tok.token)
 
        if tok.tokentype == "lexical":
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