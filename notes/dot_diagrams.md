# Graphviz DOT diagrams (`dot.py`)

`arsgrammatica.tokengraph_to_dot()` draws the same tokengraph diagram as `tokengraph_to_mermaid()` -- same nodes, same edges, same verbal-unit coloring, same implied-token treatment -- as Graphviz DOT source instead of Mermaid source. See `dot.py`'s own module docstring for the full rationale; the short version below.

## Why a second renderer

`tokengraph_to_mermaid()`'s `rank_by_depth` chains same-depth verbal-unit anchors with Mermaid's invisible-link syntax (`~~~`) -- a layout *nudge* Mermaid's own engine can override once a diagram gets complicated. Graphviz's `dot` engine has an actual primitive for this: a `{rank=same; id1; id2; ...}` subgraph statement, which *forces* those nodes onto the same rank. `tokengraph_to_dot()`'s `rank_by_depth` builds exactly that, from the same `verbal_units.compute_aat_depths()` groups the Mermaid version already uses -- same ranking, a hard constraint instead of a heuristic.

## Usage

```python
from arsgrammatica import tokengraph_to_dot

dot_source, warnings = tokengraph_to_dot(tokengraph)
```

Same signature shape as `tokengraph_to_mermaid()`:

- `orientation` (default `"BT"`) -- maps straight onto DOT's `rankdir` attribute (`BT`/`TB`/`LR`/`RL`).
- `color_by_verbal_unit` (default `True`) -- colors each node by its verbal unit, via `fillcolor`/`color`/`fontcolor` node attributes (DOT has no reusable named class the way Mermaid's `classDef` does, so it's inline per node instead).
- `rank_by_depth` (default `True`) -- the `{rank=same; ...}` alignment described above.
- `depth` (default `None`) -- caps the diagram to verbal-unit blocks at or below a given *subordination* depth, dropping deeper blocks entirely. See "Depth filtering" below -- this is a different depth notion from `rank_by_depth`'s, and easy to conflate with it.
- Returns `(dot_source, warnings)` -- same warnings as the Mermaid version (a skipped edge pointing at punctuation, a token excluded by the `depth` cutoff, or a missing id; more than 8 verbal units repeating colors), plus `compute_subordination_depths()`'s own warnings when `depth` is given.

`save_dot(tokengraph, path, ...)` (in `arsgrammatica.dot`, not re-exported from the top-level package -- same treatment as `mermaid.save_mermaid()`) writes the diagram straight to a `.dot` file, and takes the same `depth` parameter.

## Depth filtering

`depth` caps the diagram to verbal-unit blocks at or below a given *subordination* depth (`verbal_units.compute_subordination_depths()`: an independent clause is depth 0, a clause it introduces is depth 1, and so on) -- the SAME depth notion and cutoff rule as `rendering.tokengraph_to_depth_html()`'s own `depth` parameter behind its indented-HTML view, **not** the `verbal_units.compute_aat_depths()` notion `rank_by_depth` above uses for rank alignment. The two are unrelated and can disagree on a given tokengraph, so don't assume a `rank=same` grouping and a `depth` cutoff line up.

```python
# Only root/independent-clause blocks (and anything else at depth 0):
dot_source, warnings = tokengraph_to_dot(tokengraph, depth=0)
```

A block deeper than `depth` is dropped whole -- every one of its tokens omitted as a node, exactly as if it had never been in `tokengraph` -- never rendered empty or grayed out. `depth=0` shows depth-0 blocks only; omit `depth` (or pass `None`) to show everything, same as before this parameter existed; a `depth` at or beyond `verbal_units.max_subordination_depth()`'s own return value for the tokengraph shows everything too; a negative `depth` raises `ValueError`.

Unlike the indented-HTML view -- which only ever drops whole blocks, never a cross-block edge -- dropping a block here can leave a KEPT node's edge pointing at a now-excluded token. `tokengraph_to_dot()` skips that edge (with a warning) rather than emitting a dangling `->` line Graphviz would reject.

## Rendering

Generating the DOT text needs no dependency at all -- pure string building, same as `tokengraph_to_mermaid()`. Turning it into a picture needs Graphviz installed separately (the `dot` command-line tool is not a pip package):

```sh
dot -Tsvg analysis.dot > analysis.svg
dot -Tpng analysis.dot > analysis.png
```

Other options: paste the `.dot` text into an online Graphviz viewer (e.g. edotor.net), or Quarto's own fenced ```` ```{dot} ```` code-block support (needs Graphviz on the machine building the site).

**marimo notebooks**: unlike `mo.mermaid()`, marimo has no built-in Graphviz display helper as of this writing. Showing a DOT diagram in a notebook cell needs one extra step -- render to SVG yourself (`subprocess` to the `dot` binary, or the `graphviz` PyPI package, which does the same subprocess call for you) and wrap the result in `mo.Html(svg_text)`:

```python
import graphviz
import marimo as mo

src = graphviz.Source(dot_source)
mo.Html(src.pipe(format="svg").decode("utf-8"))
```

## `marimo/latin_syntaxer_dot.py`

A dedicated notebook doing exactly that, end to end: browse for a previously-saved analysis file (`read_analyses()`'s own format), pick a sentence from a menu (`split_analysis_by_sentence()`), then generate and display its Graphviz diagram inline, with `orientation`/`color_by_verbal_unit`/`rank_by_depth` exposed as live toggles, a depth-of-subordination slider (same idea and same `verbal_units.max_subordination_depth()`-bounded range as `latin_syntaxer_review.py`'s own indented-HTML depth slider -- see "Depth filtering" above), and a "Download Graphviz DOT source (.dot)" button. No LM access needed -- it only reads an already-saved analysis, the same way `latin_syntaxer_review.py` (its Mermaid-diagram counterpart) does.

It degrades visibly through both Graphviz failure modes rather than crashing the cell: the `graphviz` package missing entirely (`pip install -e ".[dev]"` covers it -- see `notes/install.md`) versus the package present but the `dot` executable not on PATH (`graphviz.ExecutableNotFound`, only raised once you actually try to render) -- either way you still get the "Download .dot source" button to render elsewhere.

## `analysis_to_dot.py`

A command-line counterpart to the notebook above, for scripting/piping instead of interactive use: reads a saved analysis file (`read_analyses()`'s own format) and writes its tokengraph's Graphviz DOT source to standard output, with `--orientation`/`--no-color`/`--no-rank` flags covering `tokengraph_to_dot()`'s own parameters. Only the DOT source goes to stdout -- warnings go to stderr instead -- so redirection and piping both work cleanly:

```sh
python analysis_to_dot.py analysis.cex > analysis.dot
python analysis_to_dot.py analysis.cex --orientation LR > analysis.dot
python analysis_to_dot.py analysis.cex --no-color --no-rank > analysis.dot

# Piped straight into Graphviz, if it's installed:
python analysis_to_dot.py analysis.cex | dot -Tsvg > analysis.svg
```

Unlike the notebook, it operates on the file's whole tokengraph as `read_analyses()` returns it -- one flat list spanning every sentence in the file, not split by sentence -- so use `marimo/latin_syntaxer_dot.py` instead if you want to pick a single sentence out of a multi-sentence file. No LM access needed, same as the notebook. No dedicated test file, matching `syntaxer_main.py`'s own precedent of no pytest coverage for CLI entry points -- it's a thin wrapper around `read_analyses()` and `tokengraph_to_dot()`, which are both already covered. It doesn't yet expose `tokengraph_to_dot()`'s `depth` parameter as a flag -- only the notebook's slider does, for now.

## Tests

`tests/test_dot.py` covers generation only (node/edge selection, coloring, ranking, depth filtering) via plain string assertions on the DOT text -- no Graphviz binary needed to run `pytest`, matching this codebase's offline/DummyLM test philosophy. The depth-filtering tests include a property check across every gold example (capping `depth` one below each passage's own maximum subordination depth) confirming no edge is ever left dangling -- a KEPT node's edge pointing at a token `depth` excluded -- plus a hand-built case exercising that exact warning. Every gold example was also spot-checked against a real `dot` binary during development (all 48 examples × 4 option combinations, plus a depth-filtered diagram, rendered cleanly) -- not part of the automated suite, since that would add a system dependency to `pytest` itself.
