---
title: Tokenizing a source file without full syntax analysis
---

`utilities/tokenize_ctsdata.py` is a command-line script that reads every passage out of a `#!ctsdata` (CEX) source file, tokenizes and sentence-splits the WHOLE collected text in one shot via `segment_sources()` (the same LM-driven segmentation stage `analyze_sources()` runs before syntax analysis, and the same way `latin_syntaxer_ctsdata.py`'s own "Analyze every selected passage, together" cell does), and writes the result to standard output using `arsgrammatica.serialize_segmentation()` -- no `SyntaxAnalysis` call, no `TokenAnalysis`/`VerbalExpression`, one LM call for the whole file rather than one per sentence:

```bash
python3 utilities/tokenize_ctsdata.py passages.txt > tokenized.txt
```

Every row is segmented together, in file order, so a sentence may run from the end of one row's text into the start of the next -- exactly like `analyze_sources()` -- and token ids (`t0`, `t1`, ...) are globally unique across the whole output.

The output has two `#!`-labeled, pipe-delimited blocks. The first, `#!sentences`, is in exactly the same shape `arsgrammatica.serialization` writes for its own `#!sentences` block (this script imports those constants directly, so the two can't drift apart). The second, `#!tokens`, lists every token in every sentence; it shares that name with `arsgrammatica.serialization`'s own `#!tokens` block, but not its columns -- there's no `tokentype`/`lemma`/relation data to write here, since nothing in this script ever runs syntax analysis. Because of that column mismatch, `read_analyses()` still can't parse this file as a whole, even though its `#!sentences` half alone is exactly what that function expects:

```
#!sentences
context_begin|first_token|context_end|last_token
urn:cts:compnov:bible.genesis.vulgate:45.1|t0|urn:cts:compnov:bible.genesis.vulgate:45.1|t4

#!tokens
context|sentence_index|id|text
urn:cts:compnov:bible.genesis.vulgate:45.1|0|t0|Non
urn:cts:compnov:bible.genesis.vulgate:45.1|0|t1|se
...
```

`#!sentences` has one row per sentence: `context_begin`/`first_token` are that sentence's own first token's citation/id, `context_end`/`last_token` its own last token's citation/id -- same fields `serialize_analyses()` itself writes. `#!tokens` has one row per token: `context` is that token's own citation, `sentence_index` is that token's own sentence's 0-based position *across the whole file* (not reset per source row), and `id`/`text` are the token's own id/surface text. `--delimiter` controls the *source* `#!ctsdata` file's own column delimiter, matching `read_ctsdata()`'s own option; the output this script writes always uses `|`.

This format is written and read by `arsgrammatica.segmentation_serialization`, exported at package level as `serialize_segmentation()`/`write_segmentation()`/`read_segmentation()` -- a lighter counterpart to `serialize_analyses()`/`write_analyses()`/`read_analyses()` for a plain `List[Sentence]` with no syntax analysis run over it at all. Unlike that format, a `#!sentences`/`#!tokens` label here may not repeat: `read_segmentation()` raises `ValueError` on a second occurrence of either label, since (unlike `serialization.py`'s globally-unique token ids) this format's token ids and `sentence_index` values are only unique within one `segment_sources()` call's own output, so silently concatenating two such files would produce colliding ids and sentence numbers rather than a combined result. `read_segmentation()` groups `#!tokens` rows by `sentence_index` (validated to run `0..N-1` with no gaps) to reconstruct each `Sentence`, then cross-checks the `#!sentences` block's own first/last token and citation fields against that grouping, raising `ValueError` naming the line on any mismatch. `marimo/latin_syntaxer_tokenized.py` (see below) is the notebook that reads a file back this way to pick a sentence and analyze it on demand.

