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

## Visualizing results

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


## Files

- `syntaxer_main.py` — command-line entry point: loads `.env`, configures the LM, and runs an analysis for a passage given on the command line.
- `arsgrammatica/` — the package with the actual analysis logic:
  - `models.py` — pydantic models for `CitedText`, `Token`, `Sentence`, `VerbalExpression`, and `TokenAnalysis`, matching the fields and relation labels from `syntax_model.md`.
  - `segmentation_dspy.py` — the DSPy signature (`SegmentPassage`) that segments citation-labeled source text into sentences and tokens, assigning stable ids (`t0`, `t1`, ...) and tracking which citation each token came from.
  - `latin_syntax_dspy.py` is the DSPy signature (`SyntaxAnalysis`) that takes a sentence's tokens and produces `verbalunits` + `tokengraph`, plus `validate()` and `print_analysis()`.
  - `pipeline.py` — ties the two stages together: `analyze_sources()` runs the full pipeline over citation-labeled input and analyzes every sentence it finds; `analyze_passage()` is the convenience wrapper for a single bare passage string; `combined_tokengraph()` concatenates results for diagramming.
  - `mermaid.py` — turns a `tokengraph` into a Mermaid flowchart: one node  per non-punctuation token, one labelled edge per
    `relatedtoken1`/`relationship1` and `relatedtoken2`/`relationship2` pair.
  - `__init__.py` — re-exports the public names above, so callers do `from arsgrammatica import ...` rather than reaching into submodules.
- `tests/` — a pytest suite covering models, segmentation, analysis, validation, and coverage of the scheme's relation/type vocabulary. See "Testing without network access" below.

## Testing without network access

```bash
pytest
```

Runs the whole suite against `tests/`, using DSPy's `DummyLM` in place of a real LM call — useful for confirming the models/signatures/pipeline still fit together after you change something, without spending API calls. Tests that call the actual configured LM are marked `live` and skipped by default (they're the only way to check the LM itself gets a scenario right, not just that the code can represent a correct answer); run them explicitly
with:

```bash
pytest -m live
```

(`live` tests need a working `.env`, same as `syntaxer_main.py`; they skip gracefully if `API_KEY` isn't set.)

Some standard `pytest` shorthands:

- `pytest` to run all.
- `pytest -v` for per-test names instead of dots. 
- `pytest tests/test_gold_examples.py` to run just one file. 
- `pytest -k agent` to run only tests matching a substring. 
- `pytest --collect-only` if you just want to see what it discovered without running anything.

## Optimizing with GEPA

`optimize_gepa.py` uses [dspy.GEPA](https://dspy.ai) -- a reflective prompt optimizer -- to improve `SyntaxAnalysis`'s instructions against the gold examples in `tests/fixtures/gold_examples.py`. Unlike `pytest` (entirely `DummyLM`-backed), this is a **live-LM script**: every trial makes a real
call to the configured task model, plus a reflection model GEPA uses to read scoring feedback and propose better instructions. Expect it to use real API usage against the configured proxy.

```bash
python optimize_gepa.py                    # --auto light (cheapest; default)
python optimize_gepa.py --auto medium       # more thorough, more expensive
python optimize_gepa.py --auto heavy        # most thorough, most expensive
python optimize_gepa.py --max-metric-calls 40   # exact call budget instead of a preset
python optimize_gepa.py --skip-baseline     # skip the pre-GEPA scoring pass (saves N calls)
```

Needs the same `.env` as `syntaxer_main.py` (`API_BASE`/`MODEL`/`API_KEY`). Optionally set `REFLECTION_MODEL` (and `REFLECTION_API_BASE`/`REFLECTION_API_KEY`, if they differ) to use a different model specifically for GEPA's reflective step -- GEPA's own docs recommend a strong reasoning model for this. Without `REFLECTION_MODEL` set, the task model doubles as the reflection model, a reasonable default for a first run.

**Scope and data**: this optimizes only `SyntaxAnalysis` (the `analyze` module in `latin_syntax_dspy.py`), not the segmentation stage. It trains on all gold examples in `GOLD_EXAMPLES` (20 as of this writing) with no separate held-out valset -- per `dspy.GEPA`'s own behavior when no valset is given, it uses the trainset for both reflective updates and Pareto-score tracking. That's a reasonable starting point while the gold set is still small, but expect the optimized prompt to fit these exact sentences well without a guarantee it generalizes to new ones -- worth revisiting (holding out a few examples as a valset) once there are more gold examples to spare.

**Scoring**: `arsgrammatica/gepa_metric.py`'s `syntax_metric` compares a prediction's `verbalunits`/`tokengraph` against the gold answer and returns a score in [0, 1] (a weighted blend: relations 50%, verbal-expression classification 30%, basic per-token fields 20% -- a judgment call, easy to retune in that file) plus specific, human-readable feedback naming every
mismatched token/relation/classification, for GEPA's reflection model to read. Relations are compared as an unordered set, not by `relatedtoken1`/`relatedtoken2` position, since that pairing is documented as an interchangeable overflow slot (see `models.py`'s `RelationLabel` comment) -- see `tests/test_gepa_metric.py` for fully offline tests of the metric itself (including that a relation-slot swap scores as a perfect match, not an error).

**Using the result**: `optimize_gepa.py` saves the optimized program's instructions to `optimized_syntax_analysis.json` (configurable via `--out`).

To use it:

```python
from arsgrammatica.latin_syntax_dspy import analyze
analyze.load("optimized_syntax_analysis.json")
```

right after import and before calling `analyze_passage()`/ `analyze_sources()` -- `analyze` is the same module-level `ChainOfThought` instance the whole pipeline uses, so loading into it in place is enough; nothing else needs to change. `gepa_logs/` (GEPA's own run logs) is gitignored; `optimized_syntax_analysis.json` is not -- commit it once you're satisfied with a run, or gitignore it yourself if you'd rather treat it as a local, disposable artifact.

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
