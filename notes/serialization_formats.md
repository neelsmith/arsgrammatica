# Two plain-text output formats: full analyses vs. tokenization-only

This codebase has two separate pipe-delimited, line-oriented plain-text formats for saving pipeline output to a file. Which one applies depends on how far a passage has gotten: has syntax analysis actually run over it, or has it only been segmented into sentences/tokens so far. The two formats share one block (`#!sentences`) but are otherwise not interchangeable -- a file in one format cannot be read by the other module's reader.

| | Module | Written by | Read by | Covers |
|---|---|---|---|---|
| **1. Full analyses** | `arsgrammatica/serialization.py` | `write_analyses()`/`serialize_analyses()` | `read_analyses()` | `Sentence`, `VerbalExpression`, `TokenAnalysis` -- the complete syntax-analysis result |
| **2. Tokenization only** | `arsgrammatica/segmentation_serialization.py` | `write_segmentation()`/`serialize_segmentation()` | `read_segmentation()` | `Sentence` only, from `segment_sources()` -- no analysis run at all |

## 1. Serializing analyses (`serialization.py`)

Implements the format specified in `quarto/reference/analysisformat.qmd`. Three required pipe-delimited blocks, each a label line, then a fixed header, then data rows. Blocks may appear in any order and may repeat (e.g. from concatenating two files); `read_analyses()` merges same-label blocks before parsing.

```
#!sentences
context_begin|first_token|context_end|last_token
Aeneid 1.1|t0|Aeneid 1.1|t4

#!verbal_units
context|token|syntactic_type
Aeneid 1.1|t3|independent

#!tokens
context|id|tokentype|text|lemma|related|relationship
Aeneid 1.1|t0|lexical|arma|arma|t3|direct object
Aeneid 1.1|t1|lexical|virum|vir|t3|direct object
Aeneid 1.1|t2|enclitic|que|que|t0|coordinating word
Aeneid 1.1|t2|enclitic|que|que|t1|coordinating word
Aeneid 1.1|t3|lexical|cano|cano|root|unit verb
Aeneid 1.1|t4|punctuation|.|||
```

`#!tokens` has one row per *relation* (`TokenAnalysis.relations`), not per token: a token's rows must be adjacent and identical except for `related`/`relationship`; their order is unspecified. A token with no relations (punctuation) has one row with both empty. `read_analyses()` merges each run of same-id rows into one `TokenAnalysis` and raises if a token's rows are not adjacent or disagree.

`TokenAnalysis.verbalunitid` is not stored; `read_analyses()` rebuilds it from `#!verbal_units`.

Implied tokens (`IMPLIED_TOKENTYPES`: 'implied sum', 'implied verb', 'implied substantive') have empty text and must lie between their sentence's first and last token rows. `serialize_analyses()` moves an implied token that sits outside every sentence's span (e.g. after a sentence's last token) to just before that sentence's last token, so a round trip can change the position (never the content) of an implied token. Implied tokens use their sentence's first token's citation as context and are excluded from the reconstructed `Sentence.tokens`.

The optional `#!lm` block (no header, three `MODEL=`/`CONTEXT=`/`REASONING=` lines per sentence) is unchanged; the legacy label `#!LM` is still accepted on read.

Files in the pre-1.0 format (a `semantic_type` column in `#!verbal_units`, or the 10-column `#!tokens` header with `verbalunit` and `related1`...`relationship2`) are rejected with a `ValueError` saying the format is no longer supported.

`read_analyses(path)` returns `(tokengraph, verbalunits, sentences, lm_infos)`, in that order, and is strict: a missing block, mismatched header, wrong column count, invalid label/type value, dangling id reference, or `#!sentences`/`#!tokens` disagreement raises `ValueError`.

`split_analysis_by_sentence(tokengraph, verbalunits, sentences)` slices the flat lists into one `(sentence_tokengraph, sentence_verbalunits)` pair per sentence; implied tokens placed after a sentence's last real token (before the next sentence) are included in that sentence's slice.

`tests/test_serialization.py` covers round-tripping (including multi-relation tokens and implied tokens), the optional `#!lm` block, concatenated blocks, rejection of the old format, and every documented `ValueError` case.

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
