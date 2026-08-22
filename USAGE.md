# Latin Syntax Analyzer — Usage Guide

A DSPy program that analyzes a Latin passage into two structures: a table of verbal expressions, and a token-by-token dependency graph. The analytic scheme itself is documented in `syntax_model.md`.



## Running an analysis from the command line

You can run an analysis from the command with the wrapper script `syntaxer_main.py`. It needs an `.env` file in this folder with your LM credentials, like this:

```
API_BASE=https://localmodel/api
MODEL=litellm/modelname
API_KEY=your-key-here
```

Then:

```bash
python3 syntaxer_main.py --passage "Gallia est omnis divisa in partes tres."
```

`--citation` is an optional second argument giving a citation label for the passage (e.g. a CTS URN), recorded on every resulting token via `Token.citation`; it defaults to no citation if omitted:

```bash
python3 syntaxer_main.py --passage "Arma virumque canō." --citation "urn:cts:latinLit:phi0690:1.1"
```

`syntaxer_main.py` reads `API_BASE` / `MODEL` / `API_KEY` from `.env`, configures the LM, and prints the analysis.

For a local, unauthenticated model (e.g. Ollama), leave `API_KEY` present but empty:

```
API_BASE=http://localhost:11434
MODEL=ollama_chat/llama3
API_KEY=
```

`syntaxer_main.py` only raises "Missing API key" when `API_KEY` isn't in `.env` at all; an empty value is treated as "this model doesn't need one" and is left out of the LM call entirely, rather than sent through as an empty credential.


## Using `arsgrammatica` in a script

To call the pipeline from your own script or a REPL instead of the CLI, configure a `dspy.LM` yourself and use `arsgrammatica` directly:

```python
import dspy
from arsgrammatica import analyze_passage, print_analysis

dspy.configure(lm=dspy.LM(model="litellm_proxy/anthropic/Claude Opus 5",
                           api_base="https://api_url/litellm",
                           api_key="your-key-here"))

sentences, results = analyze_passage("Gallia est omnis divisa in partes tres.")
for sentence, result in zip(sentences, results):
    print_analysis(sentence.tokens, result)
```

Explanation:

- `analyze_passage()` returns `(sentences, results)`: that is, one `Sentence` and one `SyntaxAnalysis` result per sentence it finds in `passage`. 
- `result.verbalunits` is a list of `VerbalExpression` objects
- `result.tokengraph` is a list of `TokenAnalysis` objects, one per token in that sentence, in order.

`analyze_passage()` also prints a warning if the LM refers to a token id that doesn't exist in its sentence's input tokens. (That's a sign that the output needs a re-run or a prompt tweak, and does not necessarily mean that your code is broken.)

`validate()` only catches referential problems like that one -- ids that don't exist. It can't tell you an otherwise well-formed analysis is probably still wrong. For one specific, observed failure mode -- a coordinating conjunction correctly pairing two verbal expressions, but the second one silently missing its own `verbalunitid` -- call `find_unanchored_coordinated_verbs()` on the result:

```python
from arsgrammatica import find_unanchored_coordinated_verbs

for sentence, result in zip(sentences, results):
    for warning in find_unanchored_coordinated_verbs(result.tokengraph):
        print(f"Possible mistake: {warning}")
```

It's a heuristic, not a guarantee -- see its own docstring -- but a clean result costs nothing to check, and a flagged one is worth a manual read before you trust the analysis.


## Analyzing citable sources

`arsgrammatica` supports tracking analyzing texts identified by some canonical citation. Under the hood, `analyze_passage()` wraps `passage` as a `CitedText` and hands this to `analyze_sources()`, which is what actually does the work. You can call `analyze_sources()` directly like this:

```python
from arsgrammatica import analyze_sources, combined_tokengraph
from arsgrammatica.models import CitedText

aeneid = "urn:cts:latinLit:phi0690:"
sources = [
    CitedText(citation=f"{aeneid}1.1", text="Arma virumque canō, Trōiae quī prīmus ab ōrīs"),
    CitedText(citation=f"{aeneid}1.2", text="Ītaliam, fātō profugus, Lāvīniaque vēnit"),
]
sentences, results = analyze_sources(sources)
tokengraph = combined_tokengraph(results)  # one flat list, spanning every sentence
```


`analyze_sources()` handles any number of sentences and citation units; sentence boundaries don't need to respect citation-unit boundaries (one sentence may span two source lines, as above), and every token still records which source unit it came from via `Token.citation`.


## Saving and loading analyses

`write_analyses()`/`read_analyses()` (in `arsgrammatica/serialization.py`) save and reload a full analysis -- `sentences`, `verbalunits` (concatenated across every sentence's result), and `tokengraph` (via `combined_tokengraph()`) -- as one deterministic, pipe-delimited plain-text file, so you can persist an analysis, diff it, hand-edit it, or reload it later without re-running the LM:

```python
from arsgrammatica import write_analyses, read_analyses, combined_tokengraph

verbalunits = [vu for result in results for vu in result.verbalunits]
tokengraph = combined_tokengraph(results)

warnings = write_analyses(sentences, verbalunits, tokengraph, "analysis.txt")
for w in warnings:
    print(f"Warning: {w}")

tokengraph, verbalunits, sentences = read_analyses("analysis.txt")
```

`serialize_analyses(sentences, verbalunits, tokengraph)` builds the exact same text and returns it as a string (plus the same warnings) instead of writing it to a file -- `write_analyses()` is just a thin wrapper around it. Use this whenever you want the serialized format for something other than a standalone file: embedding it in a prompt, logging it, or handing it to some other file-writing code of your own.

The file has three labelled, pipe-delimited blocks (`#!sentences`, `#!verbal_units`, `#!tokens`), each with its own fixed header row -- see `serialization.py`'s module docstring for the exact format, why `sentences` is needed at all (it's the only place a citation is actually attached to a token id), and what `write_analyses()`'s warnings vs. `read_analyses()`'s errors each catch. Each of the three labels may appear more than once in the file; `read_analyses()` merges every instance of a label into that label's combined row list, in file order, so simply concatenating several `write_analyses()`/`serialize_analyses()` outputs together and reading the result back gives you one combined analysis. `read_analyses()` is otherwise deliberately strict: a malformed or internally inconsistent file raises `ValueError` naming the exact line and problem, rather than silently reconstructing something partial.

`read_analyses()` hands back flat, whole-file lists -- every sentence's `tokengraph`/`verbalunits` concatenated together, the same shape `combined_tokengraph()` produces. `split_analysis_by_sentence(tokengraph, verbalunits, sentences)` splits that back into one `(sentence_tokengraph, sentence_verbalunits)` slice per sentence, aligned with `sentences` itself:

```python
from arsgrammatica import read_analyses, split_analysis_by_sentence

tokengraph, verbalunits, sentences = read_analyses("analysis.txt")
slices = split_analysis_by_sentence(tokengraph, verbalunits, sentences)

for sentence, (sentence_tokengraph, sentence_verbalunits) in zip(sentences, slices):
    ...  # render or inspect this one sentence's own analysis
```

This is what `marimo/syntaxer_review.py` (see "`marimo` notebooks" below) uses to let you pick one sentence at a time out of a saved analysis file, without needing an LM at all. An implied/elided token (see models.py's `TokenAnalysis`) is included in whichever sentence's slice it's nested inside, but one sitting *after* a sentence's own last real token (rather than between two real tokens) falls just outside that sentence's slice -- see `split_analysis_by_sentence()`'s own docstring for why, and `read_analyses()`'s note on the same underlying [first, last] real-token-position convention.


## Reading passages from a delimited-text source file

`read_ctsdata()` (in `arsgrammatica/ctsdata.py`) reads a list of citable passages -- each one a CTS URN paired with its own text -- out of a pipe-delimited file, the input-side counterpart to `write_analyses()`/`read_analyses()` above (which handle an analysis's *results*, not the passages you're about to analyze):

```python
from arsgrammatica import read_ctsdata

rows = read_ctsdata("passages.txt")
for row in rows:
    citation = row.urnbase + row.citation  # reconstructs the full URN
    print(citation, "--", row.text)
```

The file has one or more `#!ctsdata` blocks, each with its own `urn|text` header row:

```
#!ctsdata
urn|text
urn:cts:compnov:bible.genesis.vulgate:45.1|Non se poterat ultra tenere.
```

Each row's `urn` column must be a 5-part, colon-separated CTS URN (e.g. `urn:cts:compnov:bible.genesis.vulgate:45.1`); `read_ctsdata()` splits it into `urnbase` (the first 4 parts, rejoined with `:`, plus a trailing `:` -- `urn:cts:compnov:bible.genesis.vulgate:` for that example) and `citation` (the 5th part, `45.1`) -- the same `urnbase + citation` shape `syntaxer_workflow.py`'s own manual-entry form uses for its base-URN/passage fields. Pass `delimiter=...` if the file itself uses something other than `|`. Like `read_analyses()`, this is deliberately strict (a malformed row or a urn that doesn't split into exactly 5 parts raises `ValueError`, naming the line) and merges multiple `#!ctsdata` blocks in file order.


## Estimating and enforcing a `max_tokens` budget

`SyntaxAnalysis`'s output (a `reasoning` field plus JSON-serialized `verbalunits`/`tokengraph`) grows with how long and how syntactically complex a sentence is, not by a fixed amount, so a single hard-coded `max_tokens` value is eventually wrong: too small for a long or deeply subordinated sentence (truncation), too large for a short one (wasted budget). `arsgrammatica/token_budget.py` addresses this with a calibrate-then-retry approach, and `pipeline.py`'s `analyze_sources()` already uses it -- both `analyze_sources()` and `analyze_passage()` get this for free, with nothing to change in your own calling code.

First, calibrate against your own configured model:

```bash
python3 calibrate_max_tokens.py
```

This is a live-LM script (real API cost, one call per `GOLD_EXAMPLES` entry) that measures how many completion tokens the real model actually uses for each gold example, fits `completion_tokens ~= intercept + slope * num_input_tokens` by least squares, and writes the result to `arsgrammatica/token_budget_calibration.json`. Re-run it whenever the configured model, the `SyntaxAnalysis` prompt, or the `TokenAnalysis`/`VerbalExpression` schema changes substantially. Until you've run it at least once, `estimate_max_tokens()` falls back to an untuned, deliberately generous placeholder fit -- safe, but not a real measurement of your model.

```python
from arsgrammatica import estimate_max_tokens

budget = estimate_max_tokens(num_tokens=25)  # -> an int max_tokens value
```

`estimate_max_tokens()` takes the calibrated (or fallback) fit, multiplies it by a `safety_margin` (default `1.4`, covering reasoning-length variance the fit alone doesn't), and clamps the result to `[floor, ceiling]`. Set `ceiling` to your actual model's real max-output-tokens limit -- the module's own `DEFAULT_CEILING` is only a placeholder stand-in, since that limit varies by provider/model and there's no single correct default.

For the retry half, `analyze_with_retry()` wraps `analyze()`:

```python
from arsgrammatica import analyze_with_retry

result = analyze_with_retry(passage, tokens)
```

It starts from `estimate_max_tokens(len(tokens))` (or `initial_max_tokens`, if you pass one), and checks the result two ways: whether the returned `tokengraph` is missing any of `tokens`' own ids (the primary, provider-independent signal -- a real truncation, LM-JSON getting cut off mid-list, always shows up here), and, as a corroborating check, whether the LM's own `finish_reason` was `"length"`. If either signals truncation and a retry is still available (`max_retries`, default `1`) with budget left before `ceiling`, it multiplies the budget by `growth_factor` (default `2.0`) and calls again -- `max_tokens` is part of DSPy's own LM cache key, so the retry always reaches the LM again rather than replaying the same truncated cached response. If retries run out: a call that raised re-raises (nothing to fall back to); a call that returned an incomplete result is returned anyway, with a `UserWarning` naming the missing ids, rather than treated as fatal -- consistent with `validate()`'s own warn-don't-raise convention for imperfect LM output.

`get_calibration()` reports which fit is currently active (the real one from `calibrate_max_tokens.py`, or the untuned fallback) if you want to check before relying on an estimate.


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


## `marimo` notebooks

- `syntaxer.py`: an interactive notebook wrapping `analyze_passage()` -- the base URN / passage / text-to-analyze inputs each re-analyze immediately as you edit them.
- `syntaxer_workflow.py`: the same notebook, built for the real-world-testing loop DEVELOPMENT.md describes -- the three inputs are one form (nothing re-analyzes, and no LM call happens, until you click *Analyze*, rather than on every keystroke), and there's a `cex`/`txt` extension choice (default `cex`) plus a *Download analysis* button that hands the current analysis (built with `serialize_analyses()`, see "Saving and loading analyses" above) to the browser's own download mechanism -- no folder path to type, at the cost of the browser (not the notebook) deciding where the file actually lands. The filename defaults to the submitted citation (base URN + passage) with the chosen extension. Ready to hand-review and, if it's a case worth keeping, turn into a fixture with `tests/fixtures/harvest.py`.
- `syntaxer_ctsdata.py`: the same notebook again, but the passage(s) to analyze come from a `#!ctsdata` source file (see "Reading passages from a delimited-text source file" above) instead of being typed in by hand -- browse for the file, then pick one or more passages from the multiselect menu that appears (labelled `<citation>: <first few words>…`, e.g. `45.1: Non se poterat ultra…`), and click *Analyze*. Every selected passage becomes its own `CitedText` source and is analyzed together via `analyze_sources()` -- always in the file's own order regardless of the order they were clicked in, since consecutive sources can share a sentence across their boundary -- with the file's own urn supplying each source's base URN and citation. Everything downstream (Mermaid diagram, highlighted/indented HTML, save-to-file) covers the combined result across every selected passage, same as `syntaxer_workflow.py`'s own multi-sentence output. Both this notebook and `syntaxer_workflow.py` also have *See list of tokens*/*See cost*/*See prompts* checkboxes, each toggling a hidden display of the raw token list, the last LM call's own reported cost, or `dspy.inspect_history()`'s prompt/response transcript.
- `syntaxer_review.py`: no LM access at all -- browse for a file previously written by `write_analyses()` (see "Saving and loading analyses" above), pick a sentence from the menu that appears (labelled `<n>. <citation>: <first six words>…`, via `split_analysis_by_sentence()`), and it displays that one sentence's own Mermaid diagram, plain (uncolored) text, verbal-unit-colored HTML, and colored-and-indented-by-subordination-depth HTML -- the same four views `syntaxer_workflow.py`/`syntaxer_ctsdata.py` show after an LM call, but reconstructed entirely from the saved file. A slider above the indented view caps it to that sentence's own `max_subordination_depth()` or shallower, the same depth-cap control the other two notebooks offer, except here it only appears once a sentence with at least one token has actually been picked. A *Download Mermaid diagram (.mmd)* button next to the diagram hands that sentence's raw Mermaid source (the same text `mo.mermaid()` renders) to the browser's own download mechanism, ready to paste into mermaid.live, a README code block, or any other Mermaid-aware tool -- disabled until a sentence is selected, and named from that sentence's own menu number and citation (e.g. `1_Aeneid_1_1_mermaid.mmd`). Useful for reviewing or presenting an already-completed analysis (e.g. one harvested into `GOLD_EXAMPLES`) without spending an LM call, or working at all when the LM is unreachable.

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
    `relatedtoken1`/`relationship1` and `relatedtoken2`/`relationship2` pair, colored by verbal unit (see `VISUALIZATION.md`).
  - `verbal_units.py` — `assign_verbal_units()` partitions a `tokengraph` into the verbal units its own relations imply, purely from the existing graph structure (no extra LM call); `assign_verbal_unit_colors()` builds on that to assign each verbal unit a stable palette color, in the same first-appearance order `mermaid.py` uses for its node coloring — the single shared source both `mermaid.py` and `rendering.py` draw on so their colorings always agree. `compute_subordination_depths()` computes each verbal expression's *depth of subordination* (0 for an independent clause, 1 for a clause it introduces, 2 for one that clause in turn introduces, and so on) the same way, by chasing each anchor's own relation to its governing verbal expression (see `VISUALIZATION.md`); `max_subordination_depth()` reduces that to the single deepest depth reached anywhere in the passage (`None` if there are no verbal expressions, or none resolve), the natural upper bound for `tokengraph_to_depth_html()`'s own `depth` parameter below. `find_unanchored_coordinated_verbs()` is a heuristic sanity check, separate from `validate()`: it flags a "coordinating conjunction" pair where one side anchors its own verbal unit and the other doesn't -- an asymmetry a correct analysis should never produce, and a real mistake a live LM has made (see that function's own docstring for the worked example). Returns a list of warning strings (empty if nothing looks wrong); it can't confirm the unanchored side really was meant to be a verb, only that the asymmetry is worth a human look.
  - `rendering.py` — `tokengraph_to_text()` reconstructs a continuous, readable plain-text string from a `tokengraph`, with correct spacing around punctuation, brackets, quote pairs, and enclitics (unlike a plain `" ".join(...)`, which would put a space before every token, including punctuation and enclitics -- e.g. rendering "virumque" as "virum que"). `tokengraph_to_html()` does the same join, but as an HTML string with lexical, praenomen, and numeral tokens (and any coordinating conjunction) wrapped in verbal-unit-colored `<span>`s. `tokengraph_to_depth_html()` renders the same colored tokens grouped into per-verbal-unit blocks, each CSS-indented by its depth of subordination (see `VISUALIZATION.md`); its optional `depth` parameter caps rendering to blocks at or below that depth (`depth=0` through the passage's own `max_subordination_depth()`) -- a block deeper than the cap is omitted entirely, not rendered empty.
  - `__init__.py` — re-exports the public names above, so callers do `from arsgrammatica import ...` rather than reaching into submodules.
- `tests/` — a pytest suite covering models, segmentation, analysis, validation, and coverage of the scheme's relation/type vocabulary.
- `docs/build_api_docs.py` — regenerates `docs/arsgrammatica-api-docs.html`, a single self-contained HTML page documenting every name in `arsgrammatica.__all__`, built with `pdoc` straight from the package's own docstrings and type hints. Run `python docs/build_api_docs.py` after changing a public docstring or signature to refresh it; requires `pdoc` (`pip install pdoc --break-system-packages`).

## Extending the scheme

`syntax_model.md` says the current relation set is partial. To add a new relation:

1. Add the new label to `RelationLabel` in `arsgrammatica/models.py`.
2. Describe when to use it in `SyntaxAnalysis`'s docstring in
   `arsgrammatica/latin_syntax_dspy.py`, following the pattern of the existing relations
   (which token gets `relatedtoken1`/`relationship1`, which gets the
   corresponding value on the other end).
3. Add a gold example exercising it to `tests/fixtures/gold_examples.py` and
   re-run `pytest` to confirm the models still validate before trying it
   against the real LM.
