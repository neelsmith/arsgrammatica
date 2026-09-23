# displaCy-style dependency diagrams (`displacy_viz.py`)

`arsgrammatica.tokengraph_to_displacy_data()` turns a `tokengraph` into the same `{"words": [...], "arcs": [...]}` data shape [spaCy's displaCy visualizer](https://spacy.io/usage/visualizers) documents for its "manual" `dep` mode (`displacy.render(data, style="dep", manual=True)`) -- a linear row of words with labelled dependency arcs curving above them, rather than mermaid.py's/dot.py's free-floating node-and-edge graph. `tokengraph_to_displacy_svg()` draws that data as an actual SVG picture, and `save_displacy_html()` wraps the SVG in a ready-to-open HTML file.

## Why a hand-rolled renderer, not real spaCy

The data shape above is genuinely spaCy's own -- feed it to a real `displacy.render(..., manual=True)` call, or to the browser-side `displaCy.js`, and it should render just the same. But this module draws the SVG itself rather than depending on the `spacy` package: spaCy isn't a dependency of this project, and pins its own `pydantic` version, which risks a real conflict with the `pydantic` models DSPy already depends on throughout this codebase -- a heavy, version-fragile dependency just to reuse a rendering template over data this module builds anyway. So, same as mermaid.py (Mermaid source) and dot.py (Graphviz DOT source), `tokengraph_to_displacy_svg()` hand-computes word positions and stacks overlapping arcs into non-collapsing vertical levels itself, in plain string-building -- no new dependency at all.

## Usage

```python
from arsgrammatica import tokengraph_to_displacy_data, tokengraph_to_displacy_svg, save_displacy_html

data, word_token_ids, warnings = tokengraph_to_displacy_data(tokengraph)
svg, warnings = tokengraph_to_displacy_svg(tokengraph)
warnings = save_displacy_html(tokengraph, "diagram.html")
```

`save_displacy_html()` is the one most callers want: unlike mermaid.py's `.mmd` or dot.py's `.dot` output (which both still need an external renderer), the HTML file it writes is complete and browser-ready on its own -- open it directly, no further step.

## Words: reading order, punctuation omitted, implied tokens included only when linked

displaCy's own model is a strict left-to-right sentence: every word is a slot in reading order. `tokengraph_to_displacy_data()` builds that word list from `tokengraph`'s own order, but handles two special cases:

- Punctuation is EXCLUDED entirely (unlike mermaid.py's node graph, which draws it as an ordinary node): a diagram of a sentence's dependency structure reads more clearly as just its words, with commas and periods left to the caption/plain text instead.
- An implied/elided token (`models.IMPLIED_TOKENTYPES` -- "implied sum", "continued discourse", "implied subject") has no surface realization at all, so no reading-order position of its own to draw it at, unlike mermaid.py's node graph, which can place one anywhere. But when some OTHER, surviving token's own relation actually names it as a target (a participle agreeing with an implied subject, an infinitive's "indirect statement" pointing at an implied governing verb, and so on), that's the missing half of a real relation, not just noise -- so it's INCLUDED after all, positioned immediately after that other token. When more than one surviving token names the SAME implied token as a target (e.g. three indirect-statement infinitives sharing one understood governing verb), it still only gets one slot: this module places it after the LAST such token, in reading order -- a deterministic tie-break, not a claim about the most natural-reading position in every case. An implied/elided token that nothing ever links to (it only relates OUTWARD to something else, with nothing pointing back) stays excluded entirely, exactly as before this existed.

Once included this way, a linked implied token behaves exactly like any other word: its OWN `relatedtoken1`/`relatedtoken2` relations (an elided "sunt" relating to the participle it supports, an implied verb's own "root"/"unit verb" edge, and so on) are drawn too, provided their own targets resolve -- this is often the difference between a diagram that shows a passage's implied main verb's own ROOT arc at all, and one that silently never could, before this existed.

Any relation pointing into a token dropped for some OTHER reason (punctuation, or excluded by `aat_depth` -- see below), into a missing id, or into an UNLINKED implied/elided token, is skipped and reported as a warning, rather than silently producing a malformed word-index reference -- the same "degrade visibly" convention mermaid.py's own warnings already use for a relation to a missing id.

Each word's `"tag"` is its own `tokentype` string ("enclitic", "numeral", "praenomen", "abbreviation", "implied sum", "continued discourse", "implied subject" -- "punctuation" can never appear, since punctuation never gets a word), EXCEPT "lexical" -- the ordinary case, and by far the most common tokentype in most sentences -- which gets an empty tag instead, so the diagram calls out only the genuinely informative minority rather than labelling every single word. Not a part-of-speech tag in spaCy's own sense (this codebase's vocabulary doesn't have one), but the closest equivalent, shown the same way a POS tag would be, directly above each word that has one. A linked implied/elided token's own word TEXT can't be its `token` field (always `None`) -- it reuses mermaid.py's own `token_label()` placeholder instead ("elided sum" for "implied sum", the tokentype string verbatim otherwise), so the SAME token reads with the same label in both diagrams.

## The synthetic ROOT word

An independent verb's own `relatedtoken1 == 'root'` (syntax_model.md's "unit verb" relation) has no real word to point at, same problem mermaid.py's own `show_root` solves with a dedicated node. Here, with a genuinely linear word sequence, `show_root=True` (the default) appends ONE synthetic word -- displayed as "ROOT", styled in muted italic gray, never colored by verbal unit -- to the END of the word list, and draws every independent verb's own edge into it. Two coordinated independent verbs (e.g. "Ille ... noluit, Hermionenque ... adduxit") both point into that SAME single ROOT word, not one each. `show_root=False` skips these relations silently, matching this module's behavior before the option existed. The word is only ever added when at least one surviving token actually has a `root` edge to draw -- a tokengraph with no independent verb at all (e.g. one sentence sliced out of a larger passage) never gets an orphan ROOT word.

## Arc direction

`start`/`end` are the lower/higher of the two words' own indices (displaCy's own `start < end` requirement); `dir` says which end the arrowhead points at. This module's own convention: the arrowhead always marks the token a relation's source token "relates to" (`relatedtoken1`/`relatedtoken2` -- the governing verb, the antecedent, the noun a genitive depends on, and so on), regardless of which one comes first in the sentence -- `"left"` if that target ends up at the lower index, `"right"` if at the higher one. There's no real spaCy dependency parse underneath this for a "point at the head" idiom to fall out of automatically; this is simply this module's own self-consistent choice, documented so it isn't mistaken for spaCy's own arrow convention.

Both `relatedtoken1`/`relationship1` and `relatedtoken2`/`relationship2` become separate arcs, same as mermaid.py checks both. A relation is skipped (with a warning) rather than drawn as a malformed arc when its target is a punctuation token (never gets a word index), when its target was excluded by `aat_depth`, when its target id isn't present in `tokengraph`, when its target is an implied/elided token that nothing links to (see above -- a LINKED one gets included and a real arc drawn instead), or when a token would relate to itself.

## Layout: word widths and arc-level stacking

Word box widths come from a plain character count (`char_width` px per character, floored at `min_word_width`) -- a text-measurement heuristic, not real font-glyph metrics (this module calls no font-metrics library), the same "good enough, not exact" tolerance this codebase already accepts from `estimate_corpus_cost.py`'s own mechanical word count and from mermaid.py's/dot.py's own layout engines. A passage with unusually wide or narrow words may look slightly uneven as a result, but every arc and label stays unambiguous regardless.

Overlapping arcs are stacked into non-colliding vertical levels (`_assign_arc_levels()`) the same way real displaCy's own layout does: shorter arcs (by word-index span) are placed first, each into the lowest level that doesn't overlap anything already there; longer arcs stack progressively higher. Two arcs that only touch at a shared endpoint (e.g. spans `(0, 2)` and `(2, 4)`) may share a level -- only an actual horizontal overlap forces a new one.

## Filtering by AAT depth

`aat_depth` (on both `tokengraph_to_displacy_data()` and `tokengraph_to_displacy_svg()`) drops every word whose own verbal unit sits DEEPER than that AAT-graph depth (`verbal_units.compute_aat_depths()`) -- the exact same depth notion, and the exact same parameter name, `tokengraph_to_mermaid()`'s and `tokengraph_to_dot()`'s own `aat_depth` already use (see `VISUALIZATION.md`'s "Filtering by AAT-graph depth"), so one depth value drives all three diagrams identically -- e.g. `marimo/latin_syntaxer_review.py`'s own shared depth slider. `aat_depth=0` keeps a root clause's verb and every one of its ordinary dependents, in full; a dropped word's own relations are simply never drawn (nothing to warn about); a kept word's relation that points AT a dropped one is skipped with a warning, same "degrade visibly" convention as a relation into an implied/elided token or a missing id. Omit `aat_depth` (or pass `None`) to show every word; a negative value raises `ValueError`.

## Coloring by verbal unit

`color_by_verbal_unit=True` (the default, on both `tokengraph_to_displacy_svg()` and `save_displacy_html()`) fills each word's own box with its verbal unit's color, via `verbal_units.assign_verbal_units()`/`assign_verbal_unit_colors()` -- the exact same shared palette and first-appearance ordering mermaid.py and rendering.py already use, so all three visualizations of the same sentence agree on which color means which clause. A punctuation token never gets a word box here at all (see above), so nothing to color. A LINKED implied/elided token is the one exception to normal verbal-unit coloring: it always gets `verbal_units._IMPLIED_TOKEN_COLOR` -- mermaid.py's own dedicated "caution" amber for the very same token -- regardless of which verbal unit it belongs to, exactly mermaid.py's own convention; an unlinked one, excluded from the word list entirely, still never gets a word box at all. The synthetic ROOT word is never colored, same as mermaid.py's own dedicated `root` node.

## `marimo/latin_syntaxer_review.py`, `marimo/latin_syntaxer_textinput.py`, `marimo/latin_syntaxer_ctsdata.py`

Each of these three notebooks' own `diagram_tool` radio (see `notes/dot_diagrams.md`'s "`marimo/latin_syntaxer_review.py`'s own diagram display") offers `"displacy"` alongside `"mermaid"` and the Graphviz-rendered option (`"graphviz"` in `latin_syntaxer_review.py`/`latin_syntaxer_ctsdata.py`, `"dot"` in `latin_syntaxer_textinput.py` -- a display-label difference only, see `notes/dot_diagrams.md`) -- always, unlike that option, since `tokengraph_to_displacy_svg()` has no external dependency to check for at all. Its `aat_depth` is wired into the SAME shared depth slider every other diagram/HTML view on the page already uses, so one slider drives all three diagram tools identically. Since the SVG is already a fully rendered picture the moment it's computed (unlike Mermaid/DOT source, which still need `mo.mermaid()`/Graphviz to become one), its own "Download diagram" button offers the `.svg` directly, rather than an unrendered source format. `latin_syntaxer_selected_ids.py` and `latin_syntaxer_tokenized.py` don't (yet) offer displaCy.

## `utilities/analysis_to_displacy.py`

The command-line counterpart to `analysis_to_dot.py`: reads a saved analysis file (`read_analyses()`'s own format) and writes its tokengraph straight to a browser-ready HTML file via `save_displacy_html()`, with `--no-color`/`--no-root`/`--caption` flags covering the same-named parameters (`-o`/`--output-file` for where the diagram goes, default `displacy.html`).

```sh
python3 utilities/analysis_to_displacy.py analysis.cex -o diagram.html
python3 utilities/analysis_to_displacy.py analysis.cex -o diagram.html --no-color
python3 utilities/analysis_to_displacy.py analysis.cex -o diagram.html --no-root
python3 utilities/analysis_to_displacy.py analysis.cex -o diagram.html --caption "My own title"
```

No LM access needed -- same as `analysis_to_dot.py`, `read_analyses()` reconstructs everything from the file's own text. Operates on the file's whole tokengraph as `read_analyses()` returns it -- one flat list spanning every sentence in the file, not split by sentence -- same caveat as `analysis_to_dot.py`: a long multi-sentence file draws one very wide diagram, since there's no sentence-boundary concept in the word row. Use `marimo/latin_syntaxer_review.py`, or `split_analysis_by_sentence()` directly, for a single sentence out of a larger file.

## Testing

`tests/test_displacy_viz.py` covers the data conversion directly (word order excluding punctuation, tags shown only for a non-"lexical" tokentype, arc direction, the ROOT word's add/omit/multiple-independent-verbs cases, and the skip-with-warning cases: a relation into punctuation, into a missing id, and into itself) via hand-built fixtures and gold examples, the same offline/DummyLM approach every other visualization's tests use.

Implied/elided tokens get their own dedicated coverage: a parametrized check across all four `implied_*` gold examples confirms each one either appears as a word (right after its own linking token -- or, for `implied_sum_omnia_praeclara_rara`, right after the LAST of its two) or stays excluded, matching which of the two applies to that specific fixture; a dedicated test on `continuation_indirect_discourse_tarquinios_adsuesse` confirms its own implied governing verb -- linked by THREE different infinitives at once -- lands after the LAST of them and, now that it has a word slot at all, finally gets its own ROOT arc drawn (something no earlier version of this diagram could show for that passage); and hand-built fixtures cover a linked implied token's own arc being drawn (rather than skipped), an unlinked one staying excluded with no warning, the "last linker wins" tie-break when more than one token targets the same implied token, and a chain where a linked implied token itself anchors a FURTHER implied token.

The SVG renderer is checked for well-formedness and warning pass-through across every gold example, plus dedicated checks that coloring adds no new warnings, that the ROOT word is never colored, and that an included implied/elided token always gets `verbal_units._IMPLIED_TOKEN_COLOR`; `_assign_arc_levels()` is checked directly against hand-built overlapping and touching spans. `save_displacy_html()` is checked for a valid HTML shell, the default reconstructed-text caption, and a custom/empty caption. No system dependency (no Graphviz, no spaCy, no browser) is needed to run these tests -- pure string/SVG assertions, matching `test_dot.py`'s own "no `dot` binary needed" philosophy; the diagrams shown in this note's own development were additionally spot-checked by rendering the HTML output in a real browser (via a headless Chromium screenshot), not part of the automated suite.
