# Two plain-text output formats: full analyses vs. tokenization-only

This codebase has two separate pipe-delimited, line-oriented plain-text formats for saving pipeline output to a file. Which one applies depends on how far a passage has gotten: has syntax analysis actually run over it, or has it only been segmented into sentences/tokens so far. The two formats share one block (`#!sentences`) but are otherwise not interchangeable -- a file in one format cannot be read by the other module's reader.

| | Module | Written by | Read by | Covers |
|---|---|---|---|---|
| **1. Full analyses** | `arsgrammatica/serialization.py` | `write_analyses()`/`serialize_analyses()` | `read_analyses()` | `Sentence`, `VerbalExpression`, `TokenAnalysis` -- the complete syntax-analysis result |
| **2. Tokenization only** | `arsgrammatica/segmentation_serialization.py` | `write_segmentation()`/`serialize_segmentation()` | `read_segmentation()` | `Sentence` only, from `segment_sources()` -- no analysis run at all |

## 1. Serializing analyses (`serialization.py`)

Three required pipe-delimited blocks, each a label line alone on its own line, then a fixed header, then one data row per record. Blocks may appear in any order and may each repeat (e.g. from concatenating two files); `read_analyses()` merges same-label blocks before parsing.

```
#!sentences
context_begin|first_token|context_end|last_token
Aeneid 1.1|t0|Aeneid 1.1|t9

#!verbal_units
context|token|syntactic_type|semantic_type
Aeneid 1.1|t5|independent|transitive active

#!tokens
context|id|tokentype|text|lemma|verbalunit|related1|relationship1|related2|relationship2
Aeneid 1.1|t0|lexical|Arma|arma|||||
```

A fourth block, `#!LM`, is optional and shaped differently -- no header line, not pipe-delimited, three `KEY=value` lines per sentence (`MODEL=`/`CONTEXT=`/`REASONING=`) recording what model produced that sentence's analysis, a `CONTEXT1.ID1-CONTEXT2.ID2` identifier for what it analyzed, and its own reasoning (collapsed to one line):

```
#!LM
MODEL=litellm_proxy/anthropic/Claude Opus 5
CONTEXT=Aeneid 1.1.t0-Aeneid 1.1.t4
REASONING=The main verb is "cano" ("I sing"), independent and transitive active...
```

It's written only when `serialize_analyses()`/`write_analyses()` are called with `reasoning=...`; `read_analyses()` accepts a file with none at all, returning an empty list for it.

Key points: `None` fields serialize as an empty string (`""`) and parse back as `None`; the literal string `"root"` (an independent verb's own `relatedtoken1`) is a real value, never confused with empty. Sentence boundaries aren't stored redundantly on every row -- `#!sentences`' `first_token`/`last_token` ids are looked up by *position* in `#!tokens`' own row order, so a sentence's tokens must form a contiguous, matching-order run in `tokengraph` (checked, and warned about, not silently trusted). Implied/elided tokens round-trip in `#!tokens` like any other row but are excluded from a sentence's reconstructed `tokens` list in both directions, since they were never part of the original per-sentence segmentation.

`read_analyses(path)` returns `(tokengraph, verbalunits, sentences, lm_infos)`, in that order. `read_analyses()` is strict, not degrade-visibly: a missing block, a mismatched header, a wrong column count, a dangling id reference, or a `#!sentences`/`#!tokens` disagreement all raise `ValueError` immediately, naming the problem.

`split_analysis_by_sentence(tokengraph, verbalunits, sentences)` is the usual next step after reading a file back: it slices the flat `tokengraph`/`verbalunits` into one `(sentence_tokengraph, sentence_verbalunits)` pair per sentence, for anything that wants to review or render one sentence at a time (e.g. `marimo/latin_syntaxer_review.py`, `marimo/latin_syntaxer_graph_metrics.py`).

`tests/test_serialization.py` (56 tests) covers round-tripping every field including `None`/`"root"`, the optional `#!LM` block, multiple concatenated blocks, every documented `ValueError` case, and `split_analysis_by_sentence()`'s own slicing including its one documented edge case (a trailing implied token past a sentence's last real token falls just outside the slice).

## 2. Tokenizations without analysis (`segmentation_serialization.py`)

A lighter counterpart for `segment_sources()`'s own output -- sentences and their tokens, with no syntax analysis run (or paid for) at all. Two required blocks, same label/header/one-row-per-record shape as above, but neither repeatable nor optional (this format is always written whole by one `serialize_segmentation()` call):

```
#!sentences
context_begin|first_token|context_end|last_token
Aeneid 1.1|t0|Aeneid 1.1|t4

#!tokens
context|sentence_index|id|text
Aeneid 1.1|0|t0|Arma
Aeneid 1.1|0|t1|virumque
```

`#!sentences` is *exactly* `serialization.py`'s own block (same label, header, and meaning -- imported directly from there so the two can't drift apart). `#!tokens` shares its name with `serialization.py`'s block but not its columns: no `tokentype`/`lemma`/relation data, since nothing here has been analyzed yet. It adds one column `#!tokens` (analyses) doesn't have -- `sentence_index`, the token's own sentence's 0-based position in the file -- so sentence boundaries don't need to be inferred from row position at all. `read_segmentation()` groups rows by `sentence_index` first, then cross-checks that grouping against `#!sentences`' own first_token/last_token/citations, raising `ValueError` on any disagreement (e.g. a hand-edited file) rather than trusting one block over the other.

Because of the `#!tokens` column mismatch, a file in this format is never readable by `serialization.read_analyses()`, even though its `#!sentences` half alone matches exactly.

`read_segmentation(path)` returns a plain `List[Sentence]` -- there's no `verbalunits`/`tokengraph`/`lm_infos` to return, since none exist yet. Same strict, raise-immediately posture as `read_analyses()`: a missing block, mismatched header, wrong column count, non-contiguous `sentence_index` values, a duplicate token id, or a `#!sentences`/`#!tokens` disagreement all raise.

`utilities/tokenize_ctsdata.py` is this format's main producer (reads a `#!ctsdata` source, segments it, writes the result here); `marimo/latin_syntaxer_tokenized.py` is its main consumer (reads a file this format wrote, lets you pick one sentence, and runs syntax analysis on just that sentence on demand).

`tests/test_segmentation_serialization.py` (28 tests) covers round-tripping, the shared-`#!sentences`-block guarantee, and every documented `ValueError` case.
