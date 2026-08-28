# Latin Syntax Analyzer — Usage Guide

## Running an analysis from the command line

*Prerequisite*: an `.env` with with your LM credentials, like this:

```
API_BASE=https://localmodel/api
MODEL=litellm/modelname
API_KEY=your-key-here
```

Then:

```bash
python3 syntaxer_main.py --passage "Gallia est omnis divisa in partes tres."
```

`--citation` is an optional second argument giving a citation label for the passage (e.g. a CTS URN):

```bash
python3 syntaxer_main.py --passage "Arma virumque canō." --citation "urn:cts:latinLit:phi0690:1.1"
```

`syntaxer_main.py` just prints the analysis to standard output.



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

tokengraph, verbalunits, sentences, lm_infos = read_analyses("analysis.txt")
```

`serialize_analyses(sentences, verbalunits, tokengraph)` builds the exact same text and returns it as a string (plus the same warnings) instead of writing it to a file -- `write_analyses()` is just a thin wrapper around it. Use this whenever you want the serialized format for something other than a standalone file: embedding it in a prompt, logging it, or handing it to some other file-writing code of your own.

The file has three required, labelled, pipe-delimited blocks (`#!sentences`, `#!verbal_units`, `#!tokens`), each with its own fixed header row, plus a fourth, optional block, `#!LM` -- see `serialization.py`'s module docstring for the exact format, why `sentences` is needed at all (it's the only place a citation is actually attached to a token id), and what `write_analyses()`'s warnings vs. `read_analyses()`'s errors each catch. Each of the three required labels (and `#!LM`) may appear more than once in the file; `read_analyses()` merges every instance of a label into that label's combined row list, in file order, so simply concatenating several `write_analyses()`/`serialize_analyses()` outputs together and reading the result back gives you one combined analysis. `read_analyses()` is otherwise deliberately strict: a malformed or internally inconsistent file raises `ValueError` naming the exact line and problem, rather than silently reconstructing something partial.

`#!LM` records, once per sentence, which model produced that sentence's analysis, what it was given to analyze, and its own reasoning -- pass `model`/`reasoning` to write it:

```python
import os

warnings = write_analyses(
    sentences, verbalunits, tokengraph, "analysis.txt",
    model=os.environ["MODEL"],
    reasoning=[result.reasoning for result in results],
)
```

Both are optional and keyword-only; omit them (as above) to skip `#!LM` entirely, exactly reproducing the file `write_analyses()` would have written before this block existed. `reasoning` needs exactly one entry per sentence (any entry can be `None`); `read_analyses()`'s fourth return value, `lm_infos`, is `[]` for a file with no `#!LM` block at all, or one `LMInfo(model, context, reasoning)` per sentence otherwise, aligned with `sentences` by position.

`read_analyses()` hands back flat, whole-file lists -- every sentence's `tokengraph`/`verbalunits` concatenated together, the same shape `combined_tokengraph()` produces. `split_analysis_by_sentence(tokengraph, verbalunits, sentences)` splits that back into one `(sentence_tokengraph, sentence_verbalunits)` slice per sentence, aligned with `sentences` itself:

```python
from arsgrammatica import read_analyses, split_analysis_by_sentence

tokengraph, verbalunits, sentences, lm_infos = read_analyses("analysis.txt")
slices = split_analysis_by_sentence(tokengraph, verbalunits, sentences)

for sentence, (sentence_tokengraph, sentence_verbalunits) in zip(sentences, slices):
    ...  # render or inspect this one sentence's own analysis
```

This is what `marimo/latin_syntaxer_review.py` (see "`marimo` notebooks" below) uses to let you pick one sentence at a time out of a saved analysis file, without needing an LM at all. An implied/elided token (see models.py's `TokenAnalysis`) is included in whichever sentence's slice it's nested inside, but one sitting *after* a sentence's own last real token (rather than between two real tokens) falls just outside that sentence's slice -- see `split_analysis_by_sentence()`'s own docstring for why, and `read_analyses()`'s note on the same underlying [first, last] real-token-position convention.


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

Each row's `urn` column must be a 5-part, colon-separated CTS URN (e.g. `urn:cts:compnov:bible.genesis.vulgate:45.1`); `read_ctsdata()` splits it into `urnbase` (the first 4 parts, rejoined with `:`, plus a trailing `:` -- `urn:cts:compnov:bible.genesis.vulgate:` for that example) and `citation` (the 5th part, `45.1`) -- the same `urnbase + citation` shape `latin_syntaxer_workflow.py`'s own manual-entry form uses for its base-URN/passage fields. Pass `delimiter=...` if the file itself uses something other than `|`. Like `read_analyses()`, this is deliberately strict (a malformed row or a urn that doesn't split into exactly 5 parts raises `ValueError`, naming the line) and merges multiple `#!ctsdata` blocks in file order.



## `marimo` notebooks

- `syntaxer.py`: an interactive notebook wrapping `analyze_passage()` -- the base URN / passage / text-to-analyze inputs each re-analyze immediately as you edit them.
- `latin_syntaxer_workflow.py`: the same notebook, built for the real-world-testing loop DEVELOPMENT.md describes -- the three inputs are one form (nothing re-analyzes, and no LM call happens, until you click *Analyze*, rather than on every keystroke), and there's a `cex`/`txt` extension choice (default `cex`) plus a *Download analysis* button that hands the current analysis (built with `serialize_analyses()`, see "Saving and loading analyses" above) to the browser's own download mechanism -- no folder path to type, at the cost of the browser (not the notebook) deciding where the file actually lands. The filename defaults to the submitted citation (base URN + passage) with the chosen extension. Ready to hand-review and, if it's a case worth keeping, turn into a fixture with `tests/fixtures/harvest.py`.
- `latin_syntaxer_ctsdata.py`: the same notebook again, but the passage(s) to analyze come from a `#!ctsdata` source file (see "Reading passages from a delimited-text source file" above) instead of being typed in by hand -- browse for the file, then pick one or more passages from the multiselect menu that appears (labelled `<citation>: <first few words>…`, e.g. `45.1: Non se poterat ultra…`), and click *Analyze*. Every selected passage becomes its own `CitedText` source and is analyzed together via `analyze_sources()` -- always in the file's own order regardless of the order they were clicked in, since consecutive sources can share a sentence across their boundary -- with the file's own urn supplying each source's base URN and citation. Everything downstream (Mermaid diagram, highlighted/indented HTML, save-to-file) covers the combined result across every selected passage, same as `latin_syntaxer_workflow.py`'s own multi-sentence output. Both this notebook and `latin_syntaxer_workflow.py` also have *See list of tokens*/*See cost*/*See prompts* checkboxes, each toggling a hidden display of the raw token list, the last LM call's own reported cost, or `dspy.inspect_history()`'s prompt/response transcript.
- `latin_syntaxer_review.py`: no LM access at all -- browse for a file previously written by `write_analyses()` (see "Saving and loading analyses" above), pick a sentence from the menu that appears (labelled `<n>. <citation>: <first six words>…`, via `split_analysis_by_sentence()`), and it displays that one sentence's own Mermaid diagram, plain (uncolored) text, verbal-unit-colored HTML, and colored-and-indented-by-subordination-depth HTML -- the same four views `latin_syntaxer_workflow.py`/`latin_syntaxer_ctsdata.py` show after an LM call, but reconstructed entirely from the saved file. A slider above the indented view caps it to that sentence's own `max_subordination_depth()` or shallower, the same depth-cap control the other two notebooks offer, except here it only appears once a sentence with at least one token has actually been picked. A *Download Mermaid diagram (.mmd)* button next to the diagram hands that sentence's raw Mermaid source (the same text `mo.mermaid()` renders) to the browser's own download mechanism, ready to paste into mermaid.live, a README code block, or any other Mermaid-aware tool -- disabled until a sentence is selected, and named from that sentence's own menu number and citation (e.g. `1_Aeneid_1_1_mermaid.mmd`). Useful for reviewing or presenting an already-completed analysis (e.g. one harvested into `GOLD_EXAMPLES`) without spending an LM call, or working at all when the LM is unreachable.
- `latin_syntaxer_graphs.py`: also no LM access needed -- browse for a previously-saved analysis file the same way `latin_syntaxer_review.py` does, but pick one *or more* sentences from a multiselect (rather than a single sentence from a dropdown), since comparing several sentences' structure side by side is the point here. For each sentence selected, it builds a NetworkX `MultiDiGraph` via `tokengraph_to_networkx()` -- the same nodes, labels, and edges `tokengraph_to_mermaid()` would draw, just as a graph object instead of diagram source (see `graphs.py`) -- and computes `graph_metrics()` on it, then displays a heading (numbered the same way `latin_syntaxer_review.py`'s own menu is), a size/complexity table (token and relation counts, cyclomatic number, longest dependency chain), a shape table (leaf-token count/fraction, mean and max dependents per token), and a relationship-type histogram. Any relation `tokengraph_to_mermaid()` would have skipped (pointing at punctuation or a missing token id) is surfaced as a warning under that sentence's tables rather than silently dropped. Useful for characterizing or comparing sentences' dependency-graph shape -- how tree-like, how deep, how bushy -- without an LM call.