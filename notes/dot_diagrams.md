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
- `depth` (default `None`) -- caps the diagram to nodes within a given *graph* distance of a root verb, dropping farther ones entirely. See "Depth filtering" below -- this is a THIRD depth notion, distinct from `rank_by_depth`'s, and easy to conflate with either that one or `tokengraph_to_depth_html()`'s own `depth`.
- `aat_depth` (default `None`) -- a SEPARATE, independent filter from `depth` above, dropping nodes by `rank_by_depth`'s own AAT-depth notion instead. See "Filtering by AAT depth" below.
- `show_root` (default `True`) -- draws every independent verb's own `root` relation as a real edge into a single dedicated `root` node (a plain, uncolored oval), instead of dropping it silently. See "Drawing the root node" below.
- Returns `(dot_source, warnings)` -- same warnings as the Mermaid version (a skipped edge pointing at punctuation, a token excluded by the `depth` or `aat_depth` cutoff, or a missing id; more than 8 verbal units repeating colors). Neither `depth` nor `aat_depth` filtering, nor `show_root`, ever adds a warning.

`save_dot(tokengraph, path, ...)` writes the diagram straight to a `.dot` file, and takes the same `depth`/`aat_depth` parameters. Both it and its Mermaid-side equivalent, `mermaid.save_mermaid()`, went unexported from the top-level package at first -- an oversight, not a deliberate design choice -- and are now both re-exported (`arsgrammatica.save_dot`, `arsgrammatica.save_mermaid`; see `arsgrammatica/__init__.py`).

```python
from arsgrammatica import save_dot

warnings = save_dot(tokengraph, "analysis.dot")
```

## Depth filtering

`depth` caps the diagram to nodes at or within a given *graph* distance -- number of edges -- from the nearest root/independent verbal-unit anchor, following the exact same `relatedtoken1`/`relatedtoken2` edges drawn as `->` lines (`dot.compute_graph_depths()`). This is deliberately **not** the same notion as `rendering.tokengraph_to_depth_html()`'s own `depth` (`verbal_units.compute_subordination_depths()`, a CLAUSE-level notion where a whole clause's subject, object, and other ordinary dependents all share ONE depth with their governing verb), and **not** `verbal_units.compute_aat_depths()` either (`rank_by_depth` above). All three can disagree on the same tokengraph -- don't assume a `rank=same` grouping, an indented-HTML block, and a `depth` cutoff here line up.

An earlier version of this parameter used the clause-level notion, on the reasoning that it should work "like the indented-HTML slider." That was wrong for a dependency GRAPH: at `depth=0` it showed a root verb's entire clause (subject, object, every ordinary dependent), not just the verb, because they all share the clause's own subordination depth. Graph distance is what a graph view actually wants -- `depth=0` shows ONLY root verbal-unit anchors:

```python
# Only root verb(s) -- no dependents at all:
dot_source, warnings = tokengraph_to_dot(tokengraph, depth=0)
```

`depth=1` adds every token exactly one edge from a root anchor (its subject, object, adverbials, ...); `depth=2` adds tokens two edges away; and so on. A token farther than `depth` is dropped entirely -- omitted as a node, exactly as if it had never been in `tokengraph`. Omit `depth` (or pass `None`) to show everything, same as before this parameter existed; a `depth` at or beyond `dot.max_graph_depth()`'s own return value for the tokengraph shows everything too; a negative `depth` raises `ValueError`.

A token's depth follows its `relatedtoken1` relation, falling back to `relatedtoken2` only when `relatedtoken1` itself doesn't resolve -- the same preference `compute_subordination_depths()` already uses to chase a verbal expression's own governor. This matters for a token playing two roles at once, most notably a relative pronoun that's both an anaphoric pointer (`relatedtoken1` -> its antecedent) and its own dependent clause's subject (`relatedtoken2` -> that clause's verb, which points back at the pronoun via its own "unit verb" relation) -- a genuine two-way link the data model allows. Preferring `relatedtoken1` and never averaging or taking a minimum over both avoids letting that second, forward-pointing edge collapse the pronoun's depth down to whatever the (only computable FROM the pronoun) dependent verb happens to resolve to. A token with no resolvable relation at all defaults to depth 0, the same "can't determine, default to root level" fallback `compute_subordination_depths()` and `tokengraph_to_depth_html()` both use.

Dropping a node can leave a KEPT node's edge pointing at a now-excluded one -- e.g. a relative pronoun kept at its own depth while the dependent verb it's also the subject of is still excluded one depth further out. `tokengraph_to_dot()` skips that edge (with a warning) rather than emitting a dangling `->` line Graphviz would reject.

## Filtering by AAT depth

`aat_depth` is a SECOND, independent node-dropping filter, alongside `depth` above -- using `verbal_units.compute_aat_depths()` instead of `compute_graph_depths()`: the SAME notion `rank_by_depth` uses to align nodes, now used to drop them. Mirrors `mermaid.tokengraph_to_mermaid()`'s own `aat_depth` parameter exactly (see `VISUALIZATION.md`'s "Filtering by AAT-graph depth" section).

```python
# Root/independent clauses only, in full:
dot_source, warnings = tokengraph_to_dot(tokengraph, aat_depth=0)
```

Since `compute_aat_depths()` (like `compute_subordination_depths()`) gives a whole clause's verb and all of its ordinary dependents ONE shared depth, `aat_depth=0` shows a root clause IN FULL -- its verb plus every one of that clause's own dependents -- unlike `depth=0` above, which shows only the bare root verb with no dependents at all. Every token takes the AAT depth of the verbal unit it belongs to (`assign_verbal_units()`); a token belonging to no verbal unit at all defaults to depth 0 (kept), same "can't determine, default to root level" fallback used throughout this codebase.

`depth` and `aat_depth` compose freely -- a node survives only if it clears BOTH cutoffs (whichever are actually given). A dangling edge left by either filter is skipped with the same combined warning. `verbal_units.max_aat_depth(tokengraph)` is the natural upper bound for an `aat_depth` slider, the same role `max_graph_depth()` plays for `depth` above. Omit `aat_depth` (or pass `None`, the default) to show every node with respect to this filter; a negative `aat_depth` raises `ValueError`.

## Drawing the root node (`show_root`)

Every independent verb's own `relation1` is the special sentinel value `root` (`relationship1` is always `unit verb` -- see `syntax_model.md`), which isn't a real token id and was previously always dropped silently rather than drawn. `show_root` (default `True`) draws it instead: a single dedicated `root` node -- `shape=oval`, no `fillcolor`/`style=filled` regardless of `color_by_verbal_unit` -- that every independent verb's own anchor points to, labelled with its own `unit verb` relationship exactly like any other edge:

```python
# Default: every independent verb points to a plain "root" oval.
dot_source, warnings = tokengraph_to_dot(tokengraph)

# Old behavior: the 'root' relation is dropped silently, no node at all.
dot_source, warnings = tokengraph_to_dot(tokengraph, show_root=False)
```

A sentence with more than one independent (coordinated) verb still gets only ONE `root` node -- every root-anchored verb's edge points into the same node, rather than one `root` node each. The node is added only when at least one surviving token actually has a `root` edge to draw, so an empty tokengraph, or one where every root-anchored token happens to be filtered out, never gets an orphan `root` node with nothing pointing to it. That last case is actually never possible through `depth`/`aat_depth` filtering on its own, though: an independent verb's anchor is always depth 0 in BOTH `compute_graph_depths()` and `compute_aat_depths()`, so `show_root`'s node/edges compose freely with either cutoff and are never excluded by them.

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

## `marimo/latin_syntaxer_review.py`'s own diagram display

`latin_syntaxer_review.py` is the notebook that displays this diagram interactively: browse for a previously-saved analysis file (`read_analyses()`'s own format), pick a sentence from a menu (`split_analysis_by_sentence()`), and generate/display either a Mermaid or a Graphviz diagram for it, via a `diagram_tool` radio (`"mermaid"`/`"graphviz"`, the latter offered only when the `graphviz` package actually imports, same as `latin_syntaxer_textinput.py`'s own). No LM access needed -- it only reads an already-saved analysis. Whichever tool is selected, the notebook degrades visibly through both Graphviz failure modes rather than crashing the cell: the `graphviz` package missing entirely (`pip install -e ".[dev]"` covers it -- see `notes/install.md`) versus the package present but the `dot` executable not on PATH (`graphviz.ExecutableNotFound`, only raised once you actually try to render) -- either way you still get a "Download diagram source" button to render elsewhere.

Its depth slider (labelled "Maximum depth of subordination to display", `verbal_units.max_subordination_depth()`-bounded) feeds every viz on the page from one shared value: `tokengraph_to_html()`'s/`tokengraph_to_depth_html()`'s own `depth`, and `tokengraph_to_mermaid()`'s/`tokengraph_to_dot()`'s `aat_depth` -- the two notions agreeing hop-for-hop on well-formed input (see `verbal_units.compute_aat_depths()`'s own docstring), so one slider reads as one consistent cutoff everywhere despite the different parameter names. This is a DIFFERENT depth notion from `tokengraph_to_dot()`'s own graph-distance `depth` parameter (see "Depth filtering" above) -- the notebook's slider is never wired to that one.

The same slider value also now limits the notebook's AAT (Agent-Action-Target) graph, via `verbal_units.filter_tokengraph_by_aat_depth()` -- a new function that, unlike `tokengraph_to_mermaid()`'s/`tokengraph_to_dot()`'s own `aat_depth` (which only decides which NODES a diagram draws), returns an actual depth-limited `tokengraph`, so it can be handed to `aat_bridge.aatgraph()` before the AAT graph is even built, rather than after. See its own docstring (`arsgrammatica/verbal_units.py`) and `tests/test_aat_bridge.py`'s composition tests for why this never leaves `aatgraph()` with a dangling `related_node` reference into a token the filter dropped.

## `utilities/analysis_to_dot.py`

A command-line counterpart to the notebook above, for scripting/piping instead of interactive use: reads a saved analysis file (`read_analyses()`'s own format) and writes its tokengraph's Graphviz DOT source to standard output, with `--orientation`/`--no-color`/`--no-rank`/`--no-root` flags covering `tokengraph_to_dot()`'s own parameters. Only the DOT source goes to stdout -- warnings go to stderr instead -- so redirection and piping both work cleanly:

```sh
python utilities/analysis_to_dot.py analysis.cex > analysis.dot
python utilities/analysis_to_dot.py analysis.cex --orientation LR > analysis.dot
python utilities/analysis_to_dot.py analysis.cex --no-color --no-rank > analysis.dot
python utilities/analysis_to_dot.py analysis.cex --no-root > analysis.dot

# Piped straight into Graphviz, if it's installed:
python utilities/analysis_to_dot.py analysis.cex | dot -Tsvg > analysis.svg
```

Unlike the notebook, it operates on the file's whole tokengraph as `read_analyses()` returns it -- one flat list spanning every sentence in the file, not split by sentence -- so use `marimo/latin_syntaxer_review.py` instead if you want to pick a single sentence out of a multi-sentence file. No LM access needed, same as the notebook. No dedicated test file, matching `syntaxer_main.py`'s own precedent of no pytest coverage for CLI entry points -- it's a thin wrapper around `read_analyses()` and `tokengraph_to_dot()`, which are both already covered. It doesn't yet expose `tokengraph_to_dot()`'s `depth` or `aat_depth` parameters as flags -- only the notebook's `depth`/`aat_depth`-driven slider is wired in anywhere, for now.

## `utilities/analyses_to_dot_pngs.py`

A batch counterpart to the two above: reads one or more saved analysis files, and writes one PNG per sentence -- across every file -- to an output directory. Unlike `analysis_to_dot.py`, this one DOES split each file by sentence (`split_analysis_by_sentence()`), since a PNG is naturally one-diagram-per-image rather than one combined text stream:

```sh
python utilities/analyses_to_dot_pngs.py analysis.cex --output-dir diagrams/
python utilities/analyses_to_dot_pngs.py a.cex b.cex c.cex --output-dir diagrams/
python utilities/analyses_to_dot_pngs.py analysis.cex --output-dir diagrams/ --orientation LR
python utilities/analyses_to_dot_pngs.py analysis.cex --output-dir diagrams/ --no-color --no-rank
python utilities/analyses_to_dot_pngs.py analysis.cex --output-dir diagrams/ --no-root
```

Each PNG is named `<file_stem>_<sentence_number>_<citation>.png`, alphanumeric-sanitized the same way `marimo/latin_syntaxer_review.py`'s own `diagram_filename_stem` cell names its own download button's file -- prefixed with the source file's own stem so sentences from different input files never collide in one output directory. The output directory is created if it doesn't already exist.

Actually rendering a PNG needs both the `graphviz` package AND Graphviz's own `dot` executable (see "Rendering" above and `notes/graphviz_install.md`) -- unlike `analysis_to_dot.py`, which only ever produces DOT text. The script checks for the `graphviz` package up front and fails fast with install instructions if it's missing; a missing `dot` executable is only discovered on the first actual render (`graphviz.ExecutableNotFound`), which also exits immediately with install instructions, since every subsequent sentence would fail the same way. Same two failure modes the notebook degrades through, just fail-fast here instead of a per-diagram callout.

A file that can't be read, or can't be split by sentence, is skipped with a message on stderr rather than aborting the whole run -- everything else still gets rendered. The script exits non-zero if any file was skipped, or if nothing was written at all. Warnings from `tokengraph_to_dot()` itself (a skipped edge, colors repeating) go to stderr per sentence, same convention as `analysis_to_dot.py`. No `--depth`/`--aat-depth` flags either, same reason as `analysis_to_dot.py`.

## Tests

`tests/test_dot.py` covers generation only (node/edge selection, coloring, ranking, depth filtering, and its own "Drawing the 'root' node" section for `show_root`) via plain string assertions on the DOT text -- no Graphviz binary needed to run `pytest`, matching this codebase's offline/DummyLM test philosophy. The `depth` (graph-distance) tests include a property check across every gold example, at every depth level from 0 up to that passage's own `max_graph_depth()`, confirming no edge is ever left dangling -- a KEPT node's edge pointing at a token `depth` excluded -- plus a hand-built relative-pronoun fixture (the shape of a real bug report: a pronoun that's both an anaphoric pointer and its own clause's subject) exercising both the depth-computation preference rule and that exact dangling-edge warning. The `aat_depth` tests mirror that structure with their own property check (every gold example, every AAT-depth level up to `max_aat_depth()`) and a hand-built coordinating-conjunction fixture for the dangling-edge case (a conjunction resolved into one clause, coordinating with a token whose OWN verbal unit sits at a deeper AAT depth), plus checks that `aat_depth=0` keeps a whole root clause together and that `depth`/`aat_depth` compose (a node must clear both cutoffs). The `show_root` tests cover: the node/edge appearing by default and disappearing with `show_root=False`; no new warnings across every gold example; the node staying uncolored even with `color_by_verbal_unit=True`; two coordinated independent verbs sharing one `root` node rather than getting one each; a hand-built tokengraph with no independent verb at all getting no orphan `root` node; and `root` surviving both `depth=0` and `aat_depth=0`. `tests/test_mermaid_ranking.py` has the equivalent `aat_depth` coverage for `tokengraph_to_mermaid()`, and `tests/test_mermaid_root.py` mirrors every `show_root` test above for the Mermaid side. Every gold example was also spot-checked against a real `dot` binary during development (all 48 examples × option combinations, plus depth-filtered diagrams at every level, rendered cleanly) -- not part of the automated suite, since that would add a system dependency to `pytest` itself.
