# Batch-analyzing a CEX corpus, one file per sentence (`utilities/analyze_ctsdata_to_files.py`)

A command-line utility: read a `#!ctsdata` (CEX) corpus file, run it through full syntax analysis (segmentation, then every sentence's own `SentenceAnalysis`), and write each sentence's own analysis to its own file in an output directory -- `serialization.py`'s `write_analyses()` format, the same format `read_analyses()`, `analysis_to_dot.py`, and `analyses_to_dot_pngs.py` already read.

It's essentially `syntaxer_main.py` (which analyzes one hand-typed passage and writes one combined file to stdout) generalized to a whole CEX corpus file, writing one file per sentence instead. It's also the full-analysis sibling of `utilities/tokenize_ctsdata.py`, which stops at segmentation and never calls `SentenceAnalysis` at all.

## Usage

```sh
python utilities/analyze_ctsdata_to_files.py corpus.cex --output-dir analyses/
python utilities/analyze_ctsdata_to_files.py corpus.cex --output-dir analyses/ --delimiter ';'
```

Two required parameters: the input CEX file (positional) and `--output-dir`. Needs the same `.env` as `syntaxer_main.py` (`API_BASE`/`MODEL`/`API_KEY`) -- this makes real LM calls, both for segmentation and for every sentence's own analysis.

## What gets written

One `#!sentences`/`#!verbal_units`/`#!tokens`/`#!LM` file per sentence (see `serialization.py`'s module docstring for the exact shape), named `<input_file_stem>_<sentence_number>_<citation>.cex` -- alphanumeric-sanitized, the same convention `analyses_to_dot_pngs.py`'s own `sentence_filename_stem()` uses for its PNGs, prefixed with the input file's own stem so a second corpus analyzed into the same output directory doesn't collide with the first. The output directory is created if it doesn't already exist.

Each file's `#!LM` block records the configured model and that one sentence's own reasoning, matching `syntaxer_main.py`'s own convention. Every file written this way reads back with `read_analyses()` exactly like any other saved analysis -- `analysis_to_dot.py`, `analyses_to_dot_pngs.py`, and every marimo notebook that browses for a saved analysis file all work with it unchanged.

## Segmentation is corpus-wide, output is per-sentence

`segment_sources()` (inside `analyze_sources()`) runs once across the WHOLE corpus, in file order -- a sentence is free to run from the end of one `#!ctsdata` row's text into the start of the next, same as every other entry point in this codebase that calls `analyze_sources()`. Only the OUTPUT is split one file per sentence; the LM's view of the corpus while segmenting and analyzing is never chopped up passage-by-passage.

## Validation and warnings

Any validation problem `analyze_sources()` finds for a sentence is printed by `analyze_sources()` itself (its own existing, unchanged behavior -- see `pipeline.py`) before this script ever gets to write anything. Any warning `write_analyses()` itself returns for one particular file (e.g. a sentence's tokens not forming a contiguous run -- see `serialize_analyses()`'s own docstring) is printed to stderr, tagged with that file's own path, alongside a "Wrote ..." line per file on stdout -- same stdout/stderr split `analyses_to_dot_pngs.py` uses. The script exits non-zero if the corpus had no sentences at all (nothing was written).

## Testing

Its own separable function, `analyze_ctsdata_to_files(cited_texts, output_dir, file_stem, model=None)`, was exercised directly (bypassing argument parsing and `_configure_lm()`) with `DummyLM` standing in for the LM across a three-sentence corpus, confirming: one file per sentence, correctly named; each file round-trips through `read_analyses()` with the right tokens, verbal units, and `#!LM` entry; and no warnings on a clean corpus. No dedicated pytest file, matching `utilities/tokenize_ctsdata.py`'s own precedent -- no CLI entry-point script in this codebase has one, since each is a thin wrapper around already-tested library functions (`read_ctsdata()`, `analyze_sources()`, `write_analyses()`).
