# Latin Syntax Analyzer — Usage Guide

A DSPy program that analyzes a Latin passage into two structures: a table of
verbal expressions, and a token-by-token dependency graph. The analytic
scheme itself is documented in `syntax_model.md`.

## Files

- `syntaxer_main.py` — the entry point: loads `.env`, configures the LM, and
  runs an analysis for a passage given on the command line.
- `arsgrammatica/` — the package with the actual analysis logic:
  - `models.py` — pydantic models for `CitedText`, `Token`, `Sentence`,
    `VerbalExpression`, and `TokenAnalysis`, matching the fields and relation
    labels from `syntax_model.md`.
  - `segmentation_dspy.py` — the DSPy signature (`SegmentPassage`) that
    segments citation-labeled source text into sentences and tokens,
    assigning stable ids (`t0`, `t1`, ...) and tracking which citation each
    token came from. This replaced the old deterministic `tokenizer.py`,
    which could not tell `sine`/`bene` from a real enclitic split, couldn't
    read `-ne` context-dependently, and split abbreviations like `f.`/`cos.`
    into separate letter-and-period tokens; `tokenizer.py` has been removed.
  - `latin_syntax_dspy.py` — the DSPy signature (`SyntaxAnalysis`) that takes
    a sentence's tokens and produces `verbalunits` + `tokengraph`, plus
    `validate()` and `print_analysis()`.
  - `pipeline.py` — ties the two stages together: `analyze_sources()` runs
    the full pipeline over citation-labeled input and analyzes every
    sentence it finds; `analyze_passage()` is the convenience wrapper for a
    single bare passage string (see below); `combined_tokengraph()`
    concatenates results for diagramming.
  - `mermaid.py` — turns a `tokengraph` into a Mermaid flowchart: one node
    per non-punctuation token, one labelled edge per
    `relatedtoken1`/`relationship1` and `relatedtoken2`/`relationship2` pair.
  - `__init__.py` — re-exports the public names above, so callers do
    `from arsgrammatica import ...` rather than reaching into submodules.
- `tests/` — a pytest suite covering models, segmentation, analysis,
  validation, and coverage of the scheme's relation/type vocabulary. See
  "Testing without network access" below.

## Setup

```bash
source .venv/bin/activate    # dependencies are already installed here
```

`syntaxer_main.py` needs an `.env` file in this folder with your LM
credentials:

```
API_BASE=https://suarezai.holycross.edu/litellm
MODEL=litellm_proxy/anthropic/Claude Opus 5
API_KEY=your-key-here
```

`API_BASE` and `MODEL` fall back to the values above if unset; `API_KEY` has
no default and `syntaxer_main.py` will raise an error if it's missing.
`.env` is already in `.gitignore`.

## Running an analysis

```bash
python3 syntaxer_main.py --passage "Gallia est omnis divisa in partes tres."
```

Omit `--passage` to run the built-in default (`"arma virumque cano."`).
`syntaxer_main.py` reads `API_BASE` / `MODEL` / `API_KEY` from `.env`,
configures the LM, and prints the analysis.

To call the pipeline from your own script or a REPL instead of the CLI,
configure a `dspy.LM` yourself and use `arsgrammatica` directly:

```python
import dspy
from arsgrammatica import analyze_passage, print_analysis

dspy.configure(lm=dspy.LM(model="litellm_proxy/anthropic/Claude Opus 5",
                           api_base="https://suarezai.holycross.edu/litellm",
                           api_key="your-key-here"))

sentences, results = analyze_passage("Gallia est omnis divisa in partes tres.")
for sentence, result in zip(sentences, results):
    print_analysis(sentence.tokens, result)
```

`analyze_passage()` returns `(sentences, results)`: one `Sentence` and one
`SyntaxAnalysis` result per sentence it finds in `passage`, in the same
order, however many sentences that turns out to be -- there's no
restriction to a single sentence. `result.verbalunits` is a list of
`VerbalExpression` objects; `result.tokengraph` is a list of
`TokenAnalysis` objects, one per token in that sentence, in order.
`analyze_passage()` also prints a warning if the LM refers to a token id
that doesn't exist in its sentence's input tokens -- that's a sign the
output needs a re-run or a prompt tweak, not that your code is broken.

Under the hood, `analyze_passage()` is a thin single-string convenience
wrapper: it wraps `passage` as one `CitedText` and hands it to
`analyze_sources()`, which is what actually does the work. Every call now
costs at least one extra LM call compared to the old tokenizer.py-backed
version, to segment the passage before analyzing it -- there's no more
free deterministic tokenizer. Call `analyze_sources()` directly when you
have more than one citation unit to track, or want the citation label on
each token:

```python
from arsgrammatica import analyze_sources, combined_tokengraph
from arsgrammatica.models import CitedText

sources = [
    CitedText(citation="Aeneid 1.1", text="Arma virumque canō, Trōiae quī prīmus ab ōrīs"),
    CitedText(citation="Aeneid 1.2", text="Ītaliam, fātō profugus, Lāvīniaque vēnit"),
]
sentences, results = analyze_sources(sources)
tokengraph = combined_tokengraph(results)  # one flat list, spanning every sentence
```

`analyze_sources()` handles any number of sentences and citation units;
sentence boundaries don't need to respect citation-unit boundaries (one
sentence may span two source lines, as above), and every token still
records which source unit it came from via `Token.citation`.

## Diagramming a result

```python
from arsgrammatica import tokengraph_to_mermaid

diagram, warnings = tokengraph_to_mermaid(result.tokengraph)
print(diagram)
```

`diagram` is Mermaid `graph` syntax you can paste into anything that renders
Mermaid (many Markdown viewers, mermaid.live, etc.). `warnings` lists any
edge that got skipped because it pointed at a punctuation token or an id
missing from `tokengraph` — worth checking, since it usually traces back to
a problem `validate()` already flagged. `save_mermaid()` in
`arsgrammatica/mermaid.py` (import it as
`from arsgrammatica.mermaid import save_mermaid`) writes the diagram straight
to a `.mmd` file if you'd rather not copy/paste from the terminal. Since
token ids are global, `combined_tokengraph()` (see above) needs no changes
to render a multi-sentence, multi-citation passage as one diagram.

## Testing without network access

```bash
pytest
```

Runs the whole suite against `tests/`, using DSPy's `DummyLM` in place of a
real LM call — useful for confirming the models/signatures/pipeline still
fit together after you change something, without spending API calls. Tests
that call the actual configured LM are marked `live` and skipped by default
(they're the only way to check the LM itself gets a scenario right, not
just that the code can represent a correct answer); run them explicitly
with:

```bash
pytest -m live
```

(`live` tests need a working `.env`, same as `syntaxer_main.py`; they skip
gracefully if `API_KEY` isn't set.)

## Extending the scheme

`syntax_model.md` says the current relation set is partial. To add a new
relation:

1. Add the new label to `RelationLabel` in `arsgrammatica/models.py`.
2. Describe when to use it in `SyntaxAnalysis`'s docstring in
   `arsgrammatica/latin_syntax_dspy.py`, following the pattern of the existing relations
   (which token gets `relatedtoken1`/`relationship1`, which gets the
   corresponding value on the other end).
3. Add a gold example exercising it to `tests/fixtures/gold_examples.py` and
   re-run `pytest` to confirm the models still validate before trying it
   against the real LM.
