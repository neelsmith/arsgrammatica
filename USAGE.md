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


## Files

- `syntaxer_main.py` — command-line entry point: loads `.env`, configures the LM, and runs an analysis for a passage given on the command line.
- `arsgrammatica/` — the package with the actual analysis logic:
  - `models.py` — pydantic models for `CitedText`, `Token`, `Sentence`, `VerbalExpression`, and `TokenAnalysis`, matching the fields and relation labels from `syntax_model.md`.
  - `segmentation_dspy.py` — the DSPy signature (`SegmentPassage`) that segments citation-labeled source text into sentences and tokens, assigning stable ids (`t0`, `t1`, ...) and tracking which citation each token came from.
  - `latin_syntax_dspy.py` is the DSPy signature (`SyntaxAnalysis`) that takes a sentence's tokens and produces `verbalunits` + `tokengraph`, plus `validate()` and `print_analysis()`.
  - `pipeline.py` — ties the two stages together: `analyze_sources()` runs the full pipeline over citation-labeled input and analyzes every sentence it finds; `analyze_passage()` is the convenience wrapper for a single bare passage string; `combined_tokengraph()` concatenates results for diagramming.
  - `mermaid.py` — turns a `tokengraph` into a Mermaid flowchart: one node  per non-punctuation token, one labelled edge per
    `relatedtoken1`/`relationship1` and `relatedtoken2`/`relationship2` pair, colored by verbal unit (see `VISUALIZATION.md`).
  - `verbal_units.py` — `assign_verbal_units()` partitions a `tokengraph` into the verbal units its own relations imply, purely from the existing graph structure (no extra LM call); used by `mermaid.py`'s coloring, and available standalone for anything else that wants the same clause grouping.
  - `rendering.py` — `tokengraph_to_text()` reconstructs a continuous, readable plain-text string from a `tokengraph`, with correct spacing around punctuation, brackets, quote pairs, and enclitics (unlike a plain `" ".join(...)`, which would put a space before every token, including punctuation and enclitics -- e.g. rendering "virumque" as "virum que").
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
