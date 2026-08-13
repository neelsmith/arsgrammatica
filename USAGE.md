# Latin Syntax Analyzer — Usage Guide

A DSPy program that analyzes a Latin passage into two structures: a table of
verbal expressions, and a token-by-token dependency graph. The analytic
scheme itself is documented in `syntax_model.md`.

## Files

- `syntaxer_main.py` — the entry point: loads `.env`, configures the LM, and
  runs an analysis for a passage given on the command line.
- `arsgrammatica/` — the package with the actual analysis logic:
  - `tokenizer.py` — deterministically splits a passage into tokens with
    fixed ids (`t0`, `t1`, ...) before the LM ever sees it. Handles enclitic
    splitting (`virumque` → `virum` + `que`) and praenomen abbreviations
    (`M.` stays one token).
  - `models.py` — pydantic models for `Token`, `VerbalExpression`, and
    `TokenAnalysis`, matching the fields and relation labels from `syntax_model.md`.
  - `latin_syntax_dspy.py` — the DSPy signature and the `analyze_passage()` /
    `print_analysis()` functions you'll actually call.
  - `mermaid.py` — turns a `tokengraph` into a Mermaid flowchart: one node
    per non-punctuation token, one labelled edge per
    `relatedtoken1`/`relationship1` and `relatedtoken2`/`relationship2` pair.
  - `__init__.py` — re-exports the public names above, so callers do
    `from arsgrammatica import ...` rather than reaching into submodules.
- `test_pipeline.py` — a network-free test using DSPy's `DummyLM`, useful for
  checking the pipeline still works after you edit the signature or models.

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

tokens, result = analyze_passage("Gallia est omnis divisa in partes tres.")
print_analysis(tokens, result)
```

`result.verbalunits` is a list of `VerbalExpression` objects; `result.tokengraph`
is a list of `TokenAnalysis` objects, one per input token, in order.
`analyze_passage()` also prints a warning if the LM refers to a token id that
doesn't exist in the input — that's a sign the output needs a re-run or a
prompt tweak, not that your code is broken.

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
to a `.mmd` file if you'd rather not copy/paste from the terminal.

## Testing without network access

```bash
python test_pipeline.py
```

Runs the same signature through a scripted fake response instead of a real
model call. Useful for confirming the tokenizer/models/signature still fit
together after you change something, without spending API calls.

## Extending the scheme

`syntax_model.md` says the current relation set is partial. To add a new relation:

1. Add the new label to `RelationLabel` in `arsgrammatica/models.py`.
2. Describe when to use it in `SyntaxAnalysis`'s docstring in
   `arsgrammatica/latin_syntax_dspy.py`, following the pattern of the existing relations
   (which token gets `relatedtoken1`/`relationship1`, which gets the
   corresponding value on the other end).
3. Re-run `test_pipeline.py` with an updated `CANNED_ANSWER` to confirm the
   models still validate before trying it against the real LM.
