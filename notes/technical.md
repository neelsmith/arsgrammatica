# Some technical docs



## Harvesting gold examples from real analyses

`gold_example_from_analysis()`/`format_gold_example_source()` (in `tests/fixtures/harvest.py`) turn a real analysis's own `sentences`/`verbalunits`/`tokengraph` -- the same triple `write_analyses()`/`serialize_analyses()` take -- into a `GoldExample` (`tests/fixtures/gold_examples.py`), instead of hand-writing a `canned_answer` dict from scratch:

```python
from fixtures.harvest import gold_example_from_analysis, format_gold_example_source

sentences, results = analyze_passage("Some new passage you've reviewed by hand.")
result = results[0]  # one result per sentence; pick whichever one you're harvesting

example = gold_example_from_analysis(
    slug="some_new_construction_example",
    tags=["the construction this example is meant to cover"],
    sentences=sentences,
    verbalunits=result.verbalunits,
    tokengraph=result.tokengraph,
    reasoning=result.reasoning,  # dspy.ChainOfThought's own reasoning field
)
print(format_gold_example_source(example, "_SOME_NEW_CONSTRUCTION_ANSWER"))
```

`format_gold_example_source()`'s output is ready-to-paste Python: a `_SOME_NEW_CONSTRUCTION_ANSWER = {...}` dict literal followed by the `GoldExample(...)` entry that references it, in the same two-part shape every existing block in `gold_examples.py` already uses. `gold_example_from_analysis()` runs `validate()` against the given `sentences`/`verbalunits`/`tokengraph` before returning (pass `skip_validation=True` to bypass) -- catching a referentially-malformed analysis, but *not* judging whether the analysis is actually correct; that's still on you, per "an analysis you've reviewed by hand" above.

**Should a harvested example go into the trainset GEPA optimizes against, or into a held-out evaluation set?** Usually the latter. A *correct* analysis is, by definition, something the current model/prompt already gets right -- adding it to `optimize_gepa.py`'s trainset (all of `GOLD_EXAMPLES` today; see that script's own docstring for why there's no split at all there) mostly dilutes the trainset with an easy case GEPA gets to self-grade against, without teaching it anything new. The better default is to add the harvested example to `GOLD_EXAMPLES` *and* to `model_bakeoff.py`'s `HELD_OUT_SLUGS` (see `BAKEOFF.md`'s "The held-out evaluation set") -- growing a real regression corpus that catches a future prompt/model change breaking something that currently works, without inflating GEPA's own self-graded trainset. The exception is a rare construction the model only sometimes gets right, where locking in a correct demonstration genuinely is useful training signal -- that's what `model_bakeoff.py`'s bootstrap stage already does on purpose with a few-shot demo pool. `gold_example_from_analysis()` itself has no opinion baked in -- the choice of which list you paste the result into (and whether you also add its slug to `HELD_OUT_SLUGS`) is entirely on you.



## Files

- `syntaxer_main.py` — command-line entry point: loads `.env`, configures the LM, and runs an analysis for a passage given on the command line.
- `calibrate_max_tokens.py` — loads `.env`, configures the LM, and fits `arsgrammatica/token_budget.py`'s `max_tokens` estimate against real completion-token usage over `GOLD_EXAMPLES` (see "Estimating and enforcing a `max_tokens` budget" above).
- `arsgrammatica/` — the package with the actual analysis logic:
  - `models.py` — pydantic models for `CitedText`, `Token`, `Sentence`, `VerbalExpression`, and `TokenAnalysis`, matching the fields and relation labels from `syntax_model.md`.
  - `segmentation_dspy.py` — the DSPy signature (`SegmentPassage`) that segments citation-labeled source text into sentences and tokens, assigning stable ids (`t0`, `t1`, ...) and tracking which citation each token came from.
  - `latin_syntax_dspy.py` is the DSPy signature (`SyntaxAnalysis`) that takes a sentence's tokens and produces `verbalunits` + `tokengraph`, plus `validate()` and `print_analysis()`.
  - `pipeline.py` — ties the two stages together: `analyze_sources()` runs the full pipeline over citation-labeled input and analyzes every sentence it finds (via `token_budget.analyze_with_retry()`, not `analyze()` directly -- see below); `analyze_passage()` is the convenience wrapper for a single bare passage string; `combined_tokengraph()` concatenates results for diagramming.
  - `token_budget.py` — `estimate_max_tokens()` picks a `max_tokens` budget for a SyntaxAnalysis call from a passage's token count, using a fit `calibrate_max_tokens.py` writes to `token_budget_calibration.json` (or an untuned fallback before that's ever been run); `analyze_with_retry()` wraps `analyze()` with that estimate and retries with a larger budget if the result still comes back truncated (see "Estimating and enforcing a `max_tokens` budget" above).
  - `serialization.py` — `serialize_analyses()`/`write_analyses()`/`read_analyses()` save and reload `sentences`/`verbalunits`/`tokengraph` as one deterministic, pipe-delimited plain-text file, or as an equivalent in-memory string; `split_analysis_by_sentence()` splits `read_analyses()`'s flat, whole-file lists back into one `(tokengraph, verbalunits)` slice per sentence (see "Saving and loading analyses" above).
  - `mermaid.py` — turns a `tokengraph` into a Mermaid flowchart: one node  per non-punctuation token, one labelled edge per
    `relatedtoken1`/`relationship1` and `relatedtoken2`/`relationship2` pair, colored by verbal unit, with same-depth verbal-unit anchors chained together via Mermaid's invisible-link syntax so the layout also respects depth of subordination (see `VISUALIZATION.md`).
  - `verbal_units.py` — `assign_verbal_units()` partitions a `tokengraph` into the verbal units its own relations imply, purely from the existing graph structure (no extra LM call); `assign_verbal_unit_colors()` builds on that to assign each verbal unit a stable palette color, in the same first-appearance order `mermaid.py` uses for its node coloring — the single shared source both `mermaid.py` and `rendering.py` draw on so their colorings always agree. `compute_subordination_depths()` computes each verbal expression's *depth of subordination* (0 for an independent clause, 1 for a clause it introduces, 2 for one that clause in turn introduces, and so on) the same way, by chasing each anchor's own relation to its governing verbal expression (see `VISUALIZATION.md`); `max_subordination_depth()` reduces that to the single deepest depth reached anywhere in the passage (`None` if there are no verbal expressions, or none resolve), the natural upper bound for `tokengraph_to_depth_html()`'s own `depth` parameter below. `find_unanchored_coordinated_verbs()` is a heuristic sanity check, separate from `validate()`: it flags a "coordinating conjunction" pair where one side anchors its own verbal unit and the other doesn't -- an asymmetry a correct analysis should never produce, and a real mistake a live LM has made (see that function's own docstring for the worked example). Returns a list of warning strings (empty if nothing looks wrong); it can't confirm the unanchored side really was meant to be a verb, only that the asymmetry is worth a human look.
  - `rendering.py` — `tokengraph_to_text()` reconstructs a continuous, readable plain-text string from a `tokengraph`, with correct spacing around punctuation, brackets, quote pairs, and enclitics (unlike a plain `" ".join(...)`, which would put a space before every token, including punctuation and enclitics -- e.g. rendering "virumque" as "virum que"). `tokengraph_to_html()` does the same join, but as an HTML string with lexical, praenomen, and numeral tokens (and any coordinating conjunction) wrapped in verbal-unit-colored `<span>`s. `tokengraph_to_depth_html()` renders the same colored tokens grouped into per-verbal-unit blocks, each CSS-indented by its depth of subordination (see `VISUALIZATION.md`); its optional `depth` parameter caps rendering to blocks at or below that depth (`depth=0` through the passage's own `max_subordination_depth()`) -- a block deeper than the cap is omitted entirely, not rendered empty.
  - `__init__.py` — re-exports the public names above, so callers do `from arsgrammatica import ...` rather than reaching into submodules.
- `tests/` — a pytest suite covering models, segmentation, analysis, validation, and coverage of the scheme's relation/type vocabulary.
- `docs/build_api_docs.py` — regenerates `docs/arsgrammatica-api-docs.html`, a single self-contained HTML page documenting every name in `arsgrammatica.__all__`, built with `pdoc` straight from the package's own docstrings and type hints. Run `python docs/build_api_docs.py` after changing a public docstring or signature to refresh it; requires `pdoc` (`pip install pdoc --break-system-packages`).

