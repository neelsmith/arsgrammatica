"""
Render a `tokengraph` (a list of TokenAnalysis, as produced by
latin_syntax_dspy.analyze_string) as a displaCy-style dependency diagram --
https://spacy.io/usage/visualizers, the "manual" mode for the `dep` style,
where you supply your own `{"words": [...], "arcs": [...]}` data instead of
a spaCy `Doc`. That data shape is exactly what `tokengraph_to_displacy_data()`
below builds, so its output is directly usable with real spaCy
(`displacy.render(data, style="dep", manual=True)`) or with the browser-side
displaCy.js renderer, if you ever want either of those instead of this
module's own SVG.

This module draws its OWN SVG rather than depending on the `spacy` package:
spaCy isn't a dependency of this project, and pulls in its own pinned
`pydantic` version -- a real risk of colliding with the `pydantic` models
DSPy already depends on throughout this codebase, just to reuse a rendering
template over data this module is building anyway. So, same as mermaid.py
(Mermaid flowchart source) and dot.py (Graphviz DOT source), this module
hand-writes its own diagram -- here, SVG markup with hand-computed word
positions and stacked dependency arcs, rather than delegating to a
third-party layout engine.

Three public functions, in increasing order of what they do:

- `tokengraph_to_displacy_data()` -- pure data, no drawing: the standard
  `{"words": [...], "arcs": [...]}` shape, plus a parallel list of which
  token id (or `None`, for the synthetic "ROOT" pseudo-word -- see below)
  each word came from, for a caller (e.g. this module's own SVG renderer)
  that wants to re-derive something -- like verbal-unit coloring -- from
  the original tokengraph without re-deriving word order.
- `tokengraph_to_displacy_svg()` -- builds on the above: lays out words left
  to right, stacks overlapping arcs into non-overlapping vertical levels,
  and renders the whole thing as one self-contained SVG string, optionally
  colored by verbal unit (see verbal_units.py) the same way mermaid.py and
  rendering.py already color their own diagrams, so all three visualizations
  of the same sentence agree on which color means which clause.
- `save_displacy_html()` -- wraps that SVG in a minimal, self-contained HTML
  page (with the sentence's own reconstructed text as a caption, by default)
  and writes it to a file -- unlike mermaid.py's `.mmd`/dot.py's `.dot`
  output, this needs no external renderer to view: open the file in any
  browser.

**Word order, punctuation excluded, and implied/elided tokens included only
when something links to them.** displaCy's dependency view is fundamentally
about a linear reading-order sequence of words with arcs between them.
Punctuation (unlike mermaid.py's node graph, which draws it as an ordinary
node) is dropped from the word list entirely: a diagram of a sentence's
dependency structure reads more clearly as just its words, with the commas
and periods left to the caption/plain text instead.

A token with no surface realization at all (models.py's IMPLIED_TOKENTYPES
-- "implied sum", "continued discourse", "implied subject") has no
inherent position in the sentence's own reading order the way a real word
does, unlike mermaid.py's node-and-edge graph, which can place one
anywhere. But when some OTHER, surviving token's own relation actually
names it as a target (relatedtoken1/2 pointing at it -- a real participle
agreeing with an implied subject, an infinitive's "indirect statement"
pointing at an implied governing verb, and so on), that's the missing half
of a real relation, not just noise to drop -- so this module includes it
after all, positioned immediately after that OTHER token in the word
sequence, the nearest thing to "a position" an unpositioned token can be
given. (When more than one surviving token names the SAME implied token as
a target -- e.g. three indirect-statement infinitives all sharing one
understood governing verb -- it can still only occupy one slot; this
module places it after the LAST such token, in reading order, deterministic
but not a claim about which position reads most naturally in every case.)
Once included this way, the implied token behaves exactly like any other
word: its own relatedtoken1/2 relations (e.g. an elided "sunt" pointing at
the participle it supports, or an implied verb's own "root" edge) are drawn
too, provided their targets resolve normally.

An implied/elided token that nothing else's relation ever names as a
target -- one that only relates OUTWARD to something else, with nothing
pointing back at it -- has no anchor position to be placed at and is
dropped from the word list entirely, exactly as before this existed; its
own outgoing relations are then simply never drawn (nothing survives to
draw them from). Any relation pointing at a token dropped for some OTHER
reason (punctuation, or excluded by `aat_depth` -- see below) is skipped
and reported as a warning, same "degrade visibly, don't silently drop it"
convention mermaid.py's own `warnings` return value already uses for a
relation to a missing id.

**Word tags.** Each surviving word's own "tag" (displayed the way a
part-of-speech tag would be) is its tokentype string -- but ONLY when
that tokentype is something other than "lexical": an ordinary word is the
overwhelming majority of most sentences, so labelling every single one
"lexical" would just be noise; "enclitic", "numeral", "praenomen", and
"abbreviation" are the genuinely informative minority worth calling out.
A "lexical" word's own tag is the empty string (rendered as no tag line at
all in `tokengraph_to_displacy_svg()`). A linked implied/elided token's own
tag is its tokentype too ("implied sum", "continued discourse", "implied
subject"), same rule, since none of those is "lexical" either -- its word
TEXT, though, can't be `tok.token` (implied tokens have none -- `tok.token
is None`), so it uses mermaid.py's own `token_label()` instead, the exact
same placeholder ("elided sum" for "implied sum", the tokentype string
verbatim otherwise) mermaid.py's own diagram already shows for the same
token, so a reader sees the same label whichever diagram they're looking
at.

**The 'root' sentinel.** An independent verb's own `relatedtoken1 ==
'root'` (syntax_model.md's 'unit verb' relation) has no real word to point
at either -- same fix as mermaid.py's own `show_root`, but adapted to a
linear word sequence rather than a free-floating node: `show_root=True`
(the default) appends one synthetic pseudo-word, displayed as "ROOT", to
the END of the word sequence, and draws every independent verb's own edge
into it. `show_root=False` skips these relations silently, matching this
module's behavior before the option existed -- the same two-value contract
mermaid.py's and dot.py's own `show_root` already use.
"""

from typing import Dict, List, Optional, Tuple
from xml.sax.saxutils import escape as _xml_escape

from .mermaid import token_label
from .models import IMPLIED_TOKENTYPES, TokenAnalysis
from .rendering import tokengraph_to_text
from .verbal_units import (
    _IMPLIED_TOKEN_COLOR,
    assign_verbal_unit_colors,
    assign_verbal_units,
    compute_aat_depths,
)

# The synthetic pseudo-word appended to the word sequence to stand in for
# the 'root' sentinel (see this module's own docstring) -- never a real
# token id, so it can't collide with one.
_ROOT_WORD_TEXT = "ROOT"


def tokengraph_to_displacy_data(
    tokengraph: List[TokenAnalysis],
    show_root: bool = True,
    aat_depth: Optional[int] = None,
) -> Tuple[Dict[str, list], List[Optional[str]], List[str]]:
    """Build displaCy's own "manual" `dep`-style data --
    `{"words": [{"text": ..., "tag": ...}, ...], "arcs": [{"start": int,
    "end": int, "label": ..., "dir": "left" | "right"}, ...]}` -- from
    `tokengraph`, in the same shape https://spacy.io/usage/visualizers
    documents for `displacy.render(data, style="dep", manual=True)`.

    **Words.** One word per tokengraph entry, IN TOKENGRAPH ORDER (already
    reading order -- see Sentence's own docstring), EXCEPT: punctuation,
    which (unlike mermaid.py's node graph, which draws it) this module
    omits entirely, for a cleaner "just the words" diagram; and an
    implied/elided token (tokentype in IMPLIED_TOKENTYPES) that nothing
    else's relation ever names as a target, which has no surface
    realization to give it a position at all (see this module's own
    docstring) and is skipped here too. An implied/elided token that SOME
    surviving token's relation DOES name as a target is instead included,
    positioned immediately after that other token (the last one, in reading
    order, if more than one names the same target) -- see this module's own
    docstring for the full rule. Each word's own "tag" is its tokentype
    string verbatim ("enclitic", "numeral", "praenomen", "abbreviation",
    "implied sum", "continued discourse", or "implied subject" --
    "punctuation" can't appear here at all, since punctuation never gets a
    word; see above), EXCEPT "lexical" -- the ordinary case, and by far the
    most common tokentype in most sentences -- which gets an empty tag
    instead, so the diagram calls out only the genuinely informative
    minority. This still isn't a part-of-speech tag in spaCy's own sense
    (this codebase's tokentype vocabulary doesn't have one), but the
    closest equivalent this data has, displayed the same way a POS tag
    would be. A word's own TEXT is `tok.token`, except for an included
    implied/elided token (`tok.token` is always `None`), which uses
    mermaid.py's own `token_label()` placeholder instead -- the same label
    mermaid.py's diagram already shows for that same token.

    If `show_root` (default True), one further, synthetic word --
    displayed text "ROOT", tag "" -- is appended at the END of the word
    list (see this module's own docstring), but ONLY if at least one
    surviving token actually has a 'root' relation to draw into it (so a
    tokengraph with no independent verb at all -- e.g. one sentence sliced
    out of a larger passage -- never gets an orphan ROOT word), mirroring
    mermaid.py's own show_root convention of only adding its dedicated node
    when there's an edge to draw into it.

    **Arcs.** One arc per resolved relatedtoken1/relationship1 or
    relatedtoken2/relationship2 pair (both checked, same as mermaid.py):
    `start`/`end` are the LOWER/HIGHER of the two words' own indices into
    the returned "words" list (displaCy's own `start < end` requirement),
    and `dir` says which end the arrow points at -- "left" if the token
    this relation points AT (`relatedtoken1`/`2`, i.e. the more
    syntactically prominent side of the pair -- the governing verb, the
    antecedent, the noun a genitive depends on, and so on) ends up at the
    lower (`start`) index, "right" if it ends up at the higher (`end`)
    index. This is a convention of THIS module's own choosing (there's no
    real spaCy dependency parse underneath it for the "arrow points at the
    head" idiom to matter for automatically) -- but a self-consistent one:
    an arc's arrowhead always marks the token that its OWN source token
    "relates to", regardless of which one comes first in the sentence.

    A relation is skipped, and reported as a warning, rather than turned
    into a malformed arc, when: its target is a punctuation token (dropped
    from the word list, per above -- there's no word index for one); its
    target was excluded by `aat_depth` (see below); its target id isn't in
    `tokengraph` at all (the same "referentially malformed" case mermaid.py
    already guards against); or its target IS its own source token (a
    self-relation -- never valid, but defensively guarded against rather
    than assumed impossible). A relation whose target is an implied/elided
    token, by contrast, is exactly the case that gets the target INCLUDED
    (per above) rather than skipped -- so this specific reason should never
    actually surface in practice for a relation whose own source survives;
    it's kept as a defensive fallback (same "guard it anyway" spirit as the
    self-relation check) rather than assumed impossible.

    `aat_depth`, if given, drops every token belonging to a verbal
    expression DEEPER than that AAT-graph depth (`verbal_units.
    compute_aat_depths()`) from the word list entirely -- the exact same
    filter, and the exact same depth notion, `tokengraph_to_mermaid()`'s and
    `tokengraph_to_dot()`'s own `aat_depth` parameters already use, so one
    depth cutoff (e.g. a single slider in a UI) can drive all three
    diagrams identically. A token belonging to no verbal unit at all
    defaults to depth 0 (kept), same "can't determine, default to root
    level" fallback used throughout this codebase. A dropped token's own
    relations are simply never drawn (no warning -- there's no arc AT ALL to
    skip, since the token isn't iterated for its own outgoing relations
    once it has no word slot); a SURVIVING token's relation that points AT
    a dropped one is what gets skipped-with-a-warning. An implied/elided
    token is never itself excluded by `aat_depth` (same exemption
    `tokengraph_to_mermaid()`'s/`tokengraph_to_dot()`'s own `aat_depth`
    already give it) -- whether it appears in the diagram at all is
    decided solely by whether something links to it, per above, regardless
    of depth. Omit `aat_depth` (or pass `None`, the default) to show every
    word; a negative `aat_depth` raises `ValueError`.

    Returns `(data, word_token_ids, warnings)`. `word_token_ids` is a list
    parallel to `data["words"]`, giving the ORIGINAL tokengraph id each word
    came from (`None` for the synthetic ROOT word, if present -- an
    included implied/elided token gets its own real id here, same as any
    other word) -- for a caller (this module's own
    `tokengraph_to_displacy_svg()`) that wants to recover "which token is
    word index 3" without re-deriving this function's own
    word-selection/ordering rules. `warnings` is the list of
    skipped-relation messages described above.
    """
    if aat_depth is not None and aat_depth < 0:
        raise ValueError(f"aat_depth must be >= 0 (root clauses only), got {aat_depth!r}")

    by_id: Dict[str, TokenAnalysis] = {tok.id: tok for tok in tokengraph}

    aat_depth_excluded_ids: set = set()
    if aat_depth is not None:
        assignment_for_depth = assign_verbal_units(tokengraph)
        aat_depths_by_anchor = compute_aat_depths(tokengraph)
        aat_depth_excluded_ids = {
            tok.id
            for tok in tokengraph
            if tok.tokentype not in IMPLIED_TOKENTYPES
            and (
                aat_depths_by_anchor.get(assignment_for_depth.get(tok.id), 0)
                if assignment_for_depth.get(tok.id) is not None
                else 0
            )
            > aat_depth
        }

    # Every ordinary (non-implied) token that survives punctuation- and
    # aat_depth-exclusion, in tokengraph's own reading order -- exactly
    # this function's word list before implied/elided tokens could ever be
    # included at all.
    base_ids: List[str] = [
        tok.id
        for tok in tokengraph
        if tok.tokentype not in IMPLIED_TOKENTYPES
        and tok.tokentype != "punctuation"
        and tok.id not in aat_depth_excluded_ids
    ]
    base_id_set = set(base_ids)

    # Which implied/elided tokens get included, and where. `anchor_id[i]`
    # is the id of the token an included implied token `i` goes right
    # after -- the LAST token, in tokengraph order, whose own
    # relatedtoken1/2 names `i` as a target (see this module's own
    # docstring: only one slot exists per implied token, so ties favor the
    # most recent linker). This is a fixed-point computation, not a single
    # pass, so a linked implied token can itself anchor a FURTHER implied
    # token through its own outgoing relations (a chain) -- no current gold
    # example needs more than one link, but nothing here assumes that.
    implied_by_id = {
        tok.id: tok for tok in tokengraph if tok.tokentype in IMPLIED_TOKENTYPES
    }
    anchor_id: Dict[str, str] = {}
    newly_linked = True
    while newly_linked:
        newly_linked = False
        for tok in tokengraph:
            if tok.id not in base_id_set and tok.id not in anchor_id:
                continue  # tok itself isn't (yet) known to survive
            for related_field in ("relatedtoken1", "relatedtoken2"):
                related_id = getattr(tok, related_field)
                if related_id is None or related_id == "root":
                    continue
                if related_id in implied_by_id:
                    if related_id not in anchor_id:
                        newly_linked = True
                    anchor_id[related_id] = tok.id

    # Every implied token anchored to a given real (or already-included
    # implied) token id, in tokengraph order among themselves.
    implied_after: Dict[str, List[str]] = {}
    for tok in tokengraph:
        anchor = anchor_id.get(tok.id)
        if anchor is not None:
            implied_after.setdefault(anchor, []).append(tok.id)

    ordered_ids: List[str] = []

    def _place(token_id: str) -> None:
        ordered_ids.append(token_id)
        for implied_id in implied_after.get(token_id, ()):
            _place(implied_id)

    for token_id in base_ids:
        _place(token_id)

    word_texts: List[str] = []
    word_tags: List[str] = []
    word_token_ids: List[Optional[str]] = []
    index_by_id: Dict[str, int] = {}

    for token_id in ordered_ids:
        tok = by_id[token_id]
        index_by_id[tok.id] = len(word_texts)
        word_texts.append(token_label(tok))
        word_tags.append(tok.tokentype if tok.tokentype != "lexical" else "")
        word_token_ids.append(tok.id)

    warnings: List[str] = []
    raw_arcs: List[Tuple[int, int, str, str]] = []  # (start, end, label, dir)

    has_root_edge = show_root and any(
        tok.relatedtoken1 == "root" and tok.id in index_by_id for tok in tokengraph
    )
    root_index: Optional[int] = None
    if has_root_edge:
        root_index = len(word_texts)
        word_texts.append(_ROOT_WORD_TEXT)
        word_tags.append("")
        word_token_ids.append(None)

    for tok in tokengraph:
        source_index = index_by_id.get(tok.id)
        if source_index is None:
            # tok itself was dropped (an unlinked implied/elided token,
            # punctuation, or excluded by aat_depth) -- it can still be the
            # TARGET of someone else's relation (handled via
            # index_by_id.get() below), but has none of its own to draw. A
            # LINKED implied/elided token, by contrast, already has an
            # index_by_id entry by this point (see above), so it reaches
            # this loop as an ordinary source and gets its own outgoing
            # relations drawn exactly like any other token's.
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
                if root_index is not None:
                    raw_arcs.append((source_index, root_index, label, "right"))
                # else: show_root=False (or no surviving root edge at all,
                # impossible here since this IS one) -- skip silently, same
                # as mermaid.py's own show_root=False behavior.
                continue

            target_index = index_by_id.get(related_id)
            if target_index is None:
                target_tok = by_id.get(related_id)
                if target_tok is None:
                    reason = "target id is not present in tokengraph"
                elif target_tok.tokentype in IMPLIED_TOKENTYPES:
                    # A relation naming an implied/elided token as its
                    # target is exactly the case this module now INCLUDES
                    # the target for (see this module's own docstring), so
                    # this branch should never actually run for a relation
                    # whose own source survives -- kept as a defensive
                    # fallback, same "guard it anyway" spirit as the
                    # self-relation check below, rather than assumed
                    # impossible.
                    reason = (
                        "target is an implied/elided token that no "
                        "surviving token's own relation named as a target, "
                        "so it never gained a position to draw an arc to"
                    )
                elif target_tok.tokentype == "punctuation":
                    reason = "target is a punctuation token, omitted from the diagram"
                else:
                    reason = "target is excluded by the aat_depth cutoff"
                warnings.append(
                    f"skipped arc {tok.id} -[{label}]-> {related_id}: {reason}"
                )
                continue

            if target_index == source_index:
                warnings.append(
                    f"skipped arc {tok.id} -[{label}]-> {related_id}: "
                    "a token cannot relate to itself"
                )
                continue

            start, end = sorted((source_index, target_index))
            direction = "left" if target_index == start else "right"
            raw_arcs.append((start, end, label, direction))

    data = {
        "words": [
            {"text": text, "tag": tag} for text, tag in zip(word_texts, word_tags)
        ],
        "arcs": [
            {"start": start, "end": end, "label": label, "dir": direction}
            for start, end, label, direction in raw_arcs
        ],
    }
    return data, word_token_ids, warnings


def _assign_arc_levels(spans: List[Tuple[int, int]]) -> List[int]:
    """Stack `spans` (each a `(start, end)` word-index pair) into the
    fewest non-overlapping vertical levels, so overlapping arcs never draw
    on top of each other -- the same "shorter arcs sit closer to the
    baseline, longer ones stack above them" convention real displaCy's own
    layout uses. Two spans that only touch at a shared endpoint (e.g. (0, 2)
    and (2, 4)) are NOT considered overlapping and may share a level.

    Returns a list of levels (0-indexed, 0 = closest to the words), one per
    entry in `spans`, in the SAME order `spans` was given -- not the
    shortest-first order used internally to decide the assignment.
    """
    order = sorted(range(len(spans)), key=lambda i: spans[i][1] - spans[i][0])
    levels = [0] * len(spans)
    level_occupancy: List[List[Tuple[int, int]]] = []
    for i in order:
        start, end = spans[i]
        for level, occupied in enumerate(level_occupancy):
            if all(end <= o_start or o_end <= start for o_start, o_end in occupied):
                occupied.append((start, end))
                levels[i] = level
                break
        else:
            level_occupancy.append([(start, end)])
            levels[i] = len(level_occupancy) - 1
    return levels


def tokengraph_to_displacy_svg(
    tokengraph: List[TokenAnalysis],
    show_root: bool = True,
    color_by_verbal_unit: bool = True,
    aat_depth: Optional[int] = None,
    char_width: float = 8.0,
    min_word_width: float = 30.0,
    word_gap: float = 24.0,
    level_height: float = 42.0,
    arc_base_height: float = 24.0,
    margin: float = 30.0,
    font_family: str = "Helvetica, Arial, sans-serif",
    word_font_size: float = 16.0,
    tag_font_size: float = 10.0,
    label_font_size: float = 11.0,
    stroke_color: str = "#4a4a4a",
    bg_color: str = "#ffffff",
    text_color: str = "#1a1a1a",
) -> Tuple[str, List[str]]:
    """Render `tokengraph` as one self-contained displaCy-style SVG string
    (word row at the bottom, tag row just above each word, dependency arcs
    stacked above that -- see this module's own docstring for the overall
    layout and the `show_root`/implied-token conventions).

    Word boxes are sized from a plain character count (`char_width` px per
    character, floored at `min_word_width`) -- a text-measurement heuristic,
    not real font-glyph metrics (this module has no font-metrics library to
    call), same "good enough, not exact" tolerance this codebase already
    accepts from `_approximate_corpus_counts()`'s own word count and from
    mermaid.py's/dot.py's own layout engines. A passage with unusually wide
    or narrow words may look slightly uneven as a result, but every arc and
    label stays unambiguous regardless.

    `color_by_verbal_unit` (default True) fills each word's own box with
    its verbal unit's color, via `verbal_units.assign_verbal_units()` /
    `assign_verbal_unit_colors()` -- the SAME shared palette and
    first-appearance ordering mermaid.py and rendering.py already use, so
    all three visualizations of the same sentence agree on which color
    means which clause. An INCLUDED implied/elided token (see this module's
    own docstring for when that happens) is the one exception: it always
    gets `verbal_units._IMPLIED_TOKEN_COLOR` -- the same dedicated
    "caution" amber mermaid.py's own diagram already uses for the very same
    token -- regardless of which verbal unit it belongs to, exactly
    mermaid.py's own convention. An unlinked implied/elided token, dropped
    from the word list entirely, still never gets a word box at all, same
    as before this existed. The synthetic ROOT word (if present) is never
    colored, same as mermaid.py's own dedicated 'root' node.

    `aat_depth`, if given, is passed straight through to
    `tokengraph_to_displacy_data()` -- the same AAT-graph depth cutoff
    `tokengraph_to_mermaid()`'s/`tokengraph_to_dot()`'s own `aat_depth`
    parameters use, so one depth value can drive all three diagrams
    identically (e.g. one slider in `marimo/latin_syntaxer_review.py`).

    Returns `(svg, warnings)` -- `warnings` is exactly
    `tokengraph_to_displacy_data()`'s own return value, plus (if
    `color_by_verbal_unit`) `assign_verbal_unit_colors()`'s own warning when
    a passage has more than 8 distinct verbal units and colors repeat.
    """
    data, word_token_ids, warnings = tokengraph_to_displacy_data(
        tokengraph, show_root=show_root, aat_depth=aat_depth
    )
    words = data["words"]
    arcs = data["arcs"]

    word_colors: Dict[int, Tuple[str, str, str]] = {}
    if color_by_verbal_unit:
        assignment = assign_verbal_units(tokengraph)
        colors, color_warnings = assign_verbal_unit_colors(tokengraph, assignment=assignment)
        warnings = warnings + color_warnings
        by_id = {tok.id: tok for tok in tokengraph}
        for i, token_id in enumerate(word_token_ids):
            if token_id is None:
                continue  # the synthetic ROOT word -- never colored
            tok = by_id.get(token_id)
            if tok is not None and tok.tokentype in IMPLIED_TOKENTYPES:
                # An included implied/elided token always gets the same
                # dedicated "caution" amber mermaid.py's own diagram
                # already uses for it, regardless of which verbal unit it
                # belongs to -- see this function's own docstring.
                word_colors[i] = _IMPLIED_TOKEN_COLOR
                continue
            unit_id = assignment.get(token_id)
            if unit_id in colors:
                word_colors[i] = colors[unit_id]

    # --- horizontal layout: one box per word, left to right ---
    left_edges: List[float] = []
    widths: List[float] = []
    x = margin
    for word in words:
        w = max(min_word_width, char_width * len(word["text"]) + 12.0)
        left_edges.append(x)
        widths.append(w)
        x += w + word_gap
    total_width = (x - word_gap if words else x) + margin
    centers = [left_edges[i] + widths[i] / 2 for i in range(len(words))]

    # --- vertical layout: stack overlapping arcs into levels ---
    spans = [(arc["start"], arc["end"]) for arc in arcs]
    arc_levels = _assign_arc_levels(spans)
    max_level = max(arc_levels, default=-1)

    y_arc_foot = margin + (max_level + 1) * level_height + arc_base_height
    y_tag = y_arc_foot + tag_font_size + 4
    y_word = y_tag + word_font_size + 2
    total_height = y_word + margin

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{total_width:.0f}" '
        f'height="{total_height:.0f}" viewBox="0 0 {total_width:.0f} {total_height:.0f}" '
        f'font-family="{_xml_escape(font_family)}">',
        f'<rect x="0" y="0" width="{total_width:.0f}" height="{total_height:.0f}" fill="{bg_color}"/>',
    ]

    # Word boxes (colored background, if any) and text.
    for i, word in enumerate(words):
        is_root_word = word_token_ids[i] is None
        if i in word_colors:
            fill, stroke, fill_text_color = word_colors[i]
            box_top = y_word - word_font_size
            box_height = (y_word - box_top) + 4
            svg_parts.append(
                f'<rect x="{left_edges[i]:.1f}" y="{box_top:.1f}" '
                f'width="{widths[i]:.1f}" height="{box_height:.1f}" rx="4" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="1"/>'
            )
            word_text_color = fill_text_color
        else:
            word_text_color = "#7a7a7a" if is_root_word else text_color
        font_style = ' font-style="italic"' if is_root_word else ""
        svg_parts.append(
            f'<text x="{centers[i]:.1f}" y="{y_word:.1f}" text-anchor="middle" '
            f'font-size="{word_font_size:.1f}" fill="{word_text_color}"{font_style}>'
            f'{_xml_escape(word["text"])}</text>'
        )
        if word["tag"]:
            svg_parts.append(
                f'<text x="{centers[i]:.1f}" y="{y_tag:.1f}" text-anchor="middle" '
                f'font-size="{tag_font_size:.1f}" fill="#9a9a9a">'
                f'{_xml_escape(word["tag"])}</text>'
            )

    # Arcs: a cubic-bezier curve from one word's foot to another's, an
    # arrowhead at whichever end `dir` names, and a label at the peak with
    # a background patch behind it so the label reads clearly against the
    # arc line passing beneath it.
    for arc, level in zip(arcs, arc_levels):
        start_x = centers[arc["start"]]
        end_x = centers[arc["end"]]
        y_peak = y_arc_foot - (arc_base_height + level * level_height)
        svg_parts.append(
            f'<path d="M{start_x:.1f},{y_arc_foot:.1f} '
            f'C{start_x:.1f},{y_peak:.1f} {end_x:.1f},{y_peak:.1f} {end_x:.1f},{y_arc_foot:.1f}" '
            f'fill="none" stroke="{stroke_color}" stroke-width="1.5"/>'
        )
        target_x = start_x if arc["dir"] == "left" else end_x
        arrow_w, arrow_h = 7.0, 7.0
        svg_parts.append(
            f'<polygon points="{target_x - arrow_w / 2:.1f},{y_arc_foot - arrow_h:.1f} '
            f'{target_x + arrow_w / 2:.1f},{y_arc_foot - arrow_h:.1f} '
            f'{target_x:.1f},{y_arc_foot:.1f}" fill="{stroke_color}"/>'
        )
        label = arc["label"]
        label_w = len(label) * label_font_size * 0.6 + 10
        mid_x = (start_x + end_x) / 2
        svg_parts.append(
            f'<rect x="{mid_x - label_w / 2:.1f}" y="{y_peak - label_font_size:.1f}" '
            f'width="{label_w:.1f}" height="{label_font_size + 4:.1f}" fill="{bg_color}"/>'
        )
        svg_parts.append(
            f'<text x="{mid_x:.1f}" y="{y_peak + 2:.1f}" text-anchor="middle" '
            f'font-size="{label_font_size:.1f}" fill="{stroke_color}">'
            f'{_xml_escape(label)}</text>'
        )

    svg_parts.append("</svg>")
    return "\n".join(svg_parts), warnings


def save_displacy_html(
    tokengraph: List[TokenAnalysis],
    path: str,
    caption: Optional[str] = None,
    show_root: bool = True,
    color_by_verbal_unit: bool = True,
    **svg_kwargs,
) -> List[str]:
    """Render `tokengraph` (`tokengraph_to_displacy_svg()`) and write it to
    `path` as one self-contained HTML page -- unlike mermaid.py's `.mmd` or
    dot.py's `.dot` output, this needs no separate rendering step: open the
    file directly in a browser.

    `caption`, if given, is shown as a heading above the diagram; if
    omitted (the default), it's `rendering.tokengraph_to_text(tokengraph)`
    -- the sentence's own reconstructed plain text -- so the page is
    self-explanatory without also having the original passage on hand.
    Pass `caption=""` for no heading at all.

    `**svg_kwargs` are passed straight through to
    `tokengraph_to_displacy_svg()` (e.g. `aat_depth=`, `word_gap=`,
    `stroke_color=`, and so on) for any filtering/layout/color tweaks
    beyond `show_root`/`color_by_verbal_unit`, which are named here
    explicitly since they're the two options most callers actually reach
    for.

    Returns `tokengraph_to_displacy_svg()`'s own warnings.
    """
    svg, warnings = tokengraph_to_displacy_svg(
        tokengraph,
        show_root=show_root,
        color_by_verbal_unit=color_by_verbal_unit,
        **svg_kwargs,
    )
    if caption is None:
        caption = tokengraph_to_text(tokengraph)

    heading = f"<h1>{_xml_escape(caption)}</h1>\n" if caption else ""
    html = (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        f"<title>{_xml_escape(caption) if caption else 'Dependency diagram'}</title>\n"
        "<style>body { font-family: Helvetica, Arial, sans-serif; margin: 2rem; }</style>\n"
        "</head>\n<body>\n"
        f"{heading}"
        f"{svg}\n"
        "</body>\n</html>\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return warnings
