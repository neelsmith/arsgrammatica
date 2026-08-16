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

The file has three labelled, pipe-delimited blocks (`#!sentences`, `#!verbal_units`, `#!tokens`), each with its own fixed header row -- see `serialization.py`'s module docstring for the exact format, why `sentences` is needed at all (it's the only place a citation is actually attached to a token id), and what `write_analyses()`'s warnings vs. `read_analyses()`'s errors each catch. `read_analyses()` is deliberately strict: a malformed or internally inconsistent file raises `ValueError` naming the exact line and problem, rather than silently reconstructing something partial.

## `marimo` notebooks

- `syntaxer.py`: 

## Files

- `syntaxer_main.py` — command-line entry point: loads `.env`, configures the LM, and runs an analysis for a passage given on the command line.
- `arsgrammatica/` — the package with the actual analysis logic:
  - `models.py` — pydantic models for `CitedText`, `Token`, `Sentence`, `VerbalExpression`, and `TokenAnalysis`, matching the fields and relation labels from `syntax_model.md`.
  - `segmentation_dspy.py` — the DSPy signature (`SegmentPassage`) that segments citation-labeled source text into sentences and tokens, assigning stable ids (`t0`, `t1`, ...) and tracking which citation each token came from.
  - `latin_syntax_dspy.py` is the DSPy signature (`SyntaxAnalysis`) that takes a sentence's tokens and produces `verbalunits` + `tokengraph`, plus `validate()` and `print_analysis()`.
  - `pipeline.py` — ties the two stages together: `analyze_sources()` runs the full pipeline over citation-labeled input and analyzes every sentence it finds; `analyze_passage()` is the convenience wrapper for a single bare passage string; `combined_tokengraph()` concatenates results for diagramming.
  - `serialization.py` — `write_analyses()`/`read_analyses()` save and reload `sentences`/`verbalunits`/`tokengraph` as one deterministic, pipe-delimited plain-text file (see "Saving and loading analyses" above).
  - `mermaid.py` — turns a `tokengraph` into a Mermaid flowchart: one node  per non-punctuation token, one labelled edge per
    `relatedtoken1`/`relationship1` and `relatedtoken2`/`relationship2` pair, colored by verbal unit (see `VISUALIZATION.md`).
  - `verbal_units.py` — `assign_verbal_units()` partitions a `tokengraph` into the verbal units its own relations imply, purely from the existing graph structure (no extra LM call); `assign_verbal_unit_colors()` builds on that to assign each verbal unit a stable palette color, in the same first-appearance order `mermaid.py` uses for its node coloring — the single shared source both `mermaid.py` and `rendering.py` draw on so their colorings always agree. `compute_subordination_depths()` computes each verbal expression's *depth of subordination* (0 for an independent clause, 1 for a clause it introduces, 2 for one that clause in turn introduces, and so on) the same way, by chasing each anchor's own relation to its governing verbal expression (see `VISUALIZATION.md`). `find_unanchored_coordinated_verbs()` is a heuristic sanity check, separate from `validate()`: it flags a "coordinating conjunction" pair where one side anchors its own verbal unit and the other doesn't -- an asymmetry a correct analysis should never produce, and a real mistake a live LM has made (see that function's own docstring for the worked example). Returns a list of warning strings (empty if nothing looks wrong); it can't confirm the unanchored side really was meant to be a verb, only that the asymmetry is worth a human look.
  - `rendering.py` — `tokengraph_to_text()` reconstructs a continuous, readable plain-text string from a `tokengraph`, with correct spacing around punctuation, brackets, quote pairs, and enclitics (unlike a plain `" ".join(...)`, which would put a space before every token, including punctuation and enclitics -- e.g. rendering "virumque" as "virum que"). `tokengraph_to_html()` does the same join, but as an HTML string with lexical tokens wrapped in verbal-unit-colored `<span>`s. `tokengraph_to_depth_html()` renders the same colored tokens grouped into per-verbal-unit blocks, each CSS-indented by its depth of subordination (see `VISUALIZATION.md`).
  - `__init__.py` — re-exports the public names above, so callers do `from arsgrammatica import ...` rather than reaching into submodules.
- `tests/` — a pytest suite covering models, segmentation, analysis, validation, and coverage of the scheme's relation/type vocabulary.

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
