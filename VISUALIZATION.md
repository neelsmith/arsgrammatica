
# Visualizing results


## HTML formatting

`tokengraph_to_html()` in `arsgrammatica/rendering.py` renders a tokengraph as one continuous HTML string, using the exact same spacing rules as `tokengraph_to_text()` (correct handling of punctuation, brackets, quote pairs, and enclitics -- see that function's own docstring), except every **lexical** token's text is wrapped in a `<span style="background-color: ...; color: ...;">` colored by the verbal unit it belongs to:

```python
from arsgrammatica import tokengraph_to_html

html = tokengraph_to_html(result.tokengraph)
```

The colors are the *same* colors `tokengraph_to_mermaid()` assigns to that verbal unit's nodes -- same palette, same first-appearance ordering -- so a passage rendered this way and that passage's Mermaid diagram always agree on which clause is which color. (Both draw on `arsgrammatica.assign_verbal_unit_colors()`, so there's one shared definition to keep them in sync rather than two that could drift apart.) Only `tokentype == "lexical"` tokens get a span; punctuation, enclitics, numerals, and praenomens are emitted as plain (escaped) text even when they resolve to a verbal unit. A lexical token with no verbal unit at all (an unrelated bare accusative, an interjection) is left unwrapped too.

All token text is HTML-escaped (`&`, `<`, `>`, and quote characters) before being emitted, so real Latin text using literal `"`/`'` marks round-trips safely through the output. Since this reuses the same 8-color pastel palette described below, the same caveat applies: past 8 simultaneous verbal units in one passage, colors repeat.

## Mermaid graphs

In the current version of `arsgrammatica`, you can generate mermaid diagrams from the token graph.

`arsgrammatica` includes utilities
```python
from arsgrammatica import tokengraph_to_mermaid

diagram, warnings = tokengraph_to_mermaid(result.tokengraph)
print(diagram)
```

`diagram` is Mermaid `graph` syntax you can use anywhere that renders Mermaid (many Markdown viewers, mermaid.live, etc.). 

`warnings` lists any edge that got skipped because it pointed at a punctuation token or an id missing from `tokengraph` — worth checking, since it usually traces back to a problem `validate()` already flagged. 

`save_mermaid()` in `arsgrammatica/mermaid.py` (import it as
`from arsgrammatica.mermaid import save_mermaid`) writes the diagram straight to a `.mmd` file if you'd rather not copy/paste from the terminal. 

### Orientation

Both `tokengraph_to_mermaid()` and `save_mermaid()` take an optional `orientation` argument -- one of Mermaid's own flowchart orientation codes (`BT`, `TB`, `LR`, `RL`; see the [Mermaid flowchart docs](https://mermaid.js.org/syntax/flowchart.html)), used verbatim in the diagram's opening line. It defaults to `BT` (bottom-to-top):

```python
diagram, warnings = tokengraph_to_mermaid(result.tokengraph, orientation="LR")
```

### Coloring by verbal unit

By default, every token is also colored by which verbal unit's clause it belongs to -- so a sentence's clauses are visually distinguishable at a glance, not just inferable by following edges by hand. This is on by default; pass `color_by_verbal_unit=False` for a plain, uncolored diagram (the old behavior):

```python
diagram, warnings = tokengraph_to_mermaid(result.tokengraph, color_by_verbal_unit=False)
```

Under the hood, `arsgrammatica.assign_verbal_units(tokengraph)` computes a `{token id: verbal unit id or None}` mapping directly from the tokengraph's own relations (no extra LM call) -- every token that's part of a verbal unit's clause resolves to that unit's anchor token id; a token with no relation at all (an unrelated bare accusative, an enclitic, punctuation) maps to `None` and is left with Mermaid's default node styling. This mapping is exposed separately from the diagram itself, and a second function, `arsgrammatica.assign_verbal_unit_colors(tokengraph)`, exposes the palette-slot assignment too -- both are what `tokengraph_to_html()` (see "HTML formatting" above) uses to color its spans identically to this diagram's nodes.

Verbal units are assigned colors from a fixed 8-color palette, in the order their tokens first appear in the sentence; `warnings` gets one extra entry if a passage has more than 8 verbal units, since colors then repeat and stop being unambiguous.

The palette is pastel: each swatch is a light, low-saturation fill with a vivid outline in that same hue, and black text throughout. Pastel and the `dataviz` skill's usual accessibility ceiling are in real tension -- pushing this light necessarily exceeds the lightness cap that skill's validator enforces for un-labeled marks (dots, bars) where color alone has to carry identity. That ceiling doesn't fully apply here, since every node already carries its own visible text label -- but rather than dropping accessibility checking altogether, the ordering was still tuned against the same validator for the checks that don't assume an unlabeled mark: adjacent-pair color-vision-deficiency separation and normal-vision separation both still clear their targets, so any two simultaneous colors in one diagram should still read as clearly different, even if a colorblind viewer or a printed black-and-white copy will need the node labels (already always present) to disambiguate further.
