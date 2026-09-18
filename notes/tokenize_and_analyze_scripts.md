# Corpus scripts: what each one does (`utilities/tokenize_ctsdata.py`, `utilities/analyze_ctsdata_to_files.py`, `utilities/analyze_tokendata_to_files.py`, `utilities/analyze_w_diagrams.py`)

Four command-line scripts turn a `#!ctsdata` (CEX) source file into syntax analyses and diagrams, at different stages and granularities. All four are corpus-scale siblings of `syntaxer_main.py` (which handles one hand-typed passage); none of them needs anything beyond the same `.env` that script does (`API_BASE`/`MODEL`/`API_KEY`).

## `tokenize_ctsdata.py` -- segmentation only, no syntax analysis

Reads a CEX file's passages and writes a tokenized `#!sentences`/`#!tokens` file to stdout -- no `SentenceAnalysis` call, no `TokenAnalysis`/`VerbalExpression`, just "what are the sentences and tokens." It doesn't segment the whole file in one LM call: it first clusters the passages into the smallest runs that each begin and end at a likely sentence boundary (`passage_grouping.group_passages_by_sentence_boundary()` -- a fast, LM-free text-ending heuristic), then runs one `segment_sources()` call per cluster rather than one for the whole file. Each cluster's own call restarts its token numbering at `t0`, so afterward every token whose citation is a CTS URN gets its id rewritten to a passage-scoped composite id instead (`arsgrammatica.assign_passage_scoped_ids()` -- e.g. citation `...:1.1` gives `1.1.t0`, `1.1.t1`, ...): each passage keeps its own `t0, t1, ...` run no matter which cluster it ended up in, so the same passage gets the same ids regardless of how a given run happened to group it -- which is also what lets this script's own output share the LM's response cache with `analyze_ctsdata_to_files.py` analyzing the same corpus directly (see below). This is the cheapest and fastest of the three -- useful on its own to inspect how a corpus segments, or as input to `analyze_tokendata_to_files.py` below.

```sh
python utilities/tokenize_ctsdata.py corpus.cex > tokenized.txt
```

## `analyze_ctsdata_to_files.py` -- the full pipeline in one shot

Reads a CEX file and runs it straight through BOTH stages -- segmentation, then one `SentenceAnalysis` call per sentence (`analyze_sources()`) -- writing each sentence's own analysis to its own file in an output directory (`serialization.py`'s `#!sentences`/`#!verbal_units`/`#!tokens`/`#!lm` format). It uses the SAME clustering strategy as `tokenize_ctsdata.py`: passages are grouped into the smallest sentence-boundary-respecting runs first (no LM call), and `analyze_sources()` then runs once per group rather than once for the whole corpus. `analyze_sources()` itself rewrites every CTS-URN-cited token's id to the same passage-scoped composite id `tokenize_ctsdata.py` would give it, before ever calling `SentenceAnalysis` -- not for uniqueness (each sentence here is written to its own self-contained file, so that was never at risk), but so that a passage analyzed this way gets an IDENTICAL prompt to running `tokenize_ctsdata.py` then `analyze_tokendata_to_files.py` on the same corpus, letting the two pipelines actually share the LM's response cache for a passage they both segment the same way. Use this when there's no reason to keep the segmentation and analysis steps separate.

```sh
python utilities/analyze_ctsdata_to_files.py corpus.cex --output-dir analyses/
```

## `analyze_tokendata_to_files.py` -- analysis only, starting from an already-tokenized file

The second half of the pipeline above, taken on its own: reads one or more files written by `tokenize_ctsdata.py` (accepts several at once, unlike the other two scripts) and runs full syntax analysis on each sentence they already contain -- no segmentation call at all, since that already happened. Also one output file per sentence. A file it reads may carry other `#!`-labeled blocks besides `#!sentences`/`#!tokens` (an `#!lm` block, say) without a problem -- anything it doesn't need is simply ignored. Use this to split tokenizing and analyzing into separate runs (e.g. tokenize once, analyze several times, or review the tokenized file by hand before spending anything on real analysis).

```sh
python utilities/analyze_tokendata_to_files.py tokenized.txt --output-dir analyses/
python utilities/analyze_tokendata_to_files.py a.txt b.txt --output-dir analyses/
```

## `analyze_w_diagrams.py` -- the full pipeline, plus diagrams, in one command

Runs a CEX corpus through all three stages above end to end, in one invocation: `tokenize_ctsdata.py`'s own tokenizing function, then `analyze_tokendata_to_files.py`'s own analyzing function on the result, then renders every resulting analysis file as a Graphviz PNG (the same rendering `analyses_to_dot_pngs.py` does). Everything lands under one output directory: the tokenized-data file (kept on disk, not discarded, in case it's useful to inspect or reanalyze later), one analysis file per sentence directly inside it, and the PNGs in a `dots/` subdirectory. One `.env` read and one combined LM-cost total cover both LM-calling stages (diagramming makes no LM calls). Use this for the common case of wanting everything -- tokenized data, analyses, and diagrams -- from a single corpus file in one command, rather than three.

```sh
python utilities/analyze_w_diagrams.py corpus.cex --output-dir out/
```

## What they all share

Each keeps stdout clean for its own real output -- the serialized segmentation for `tokenize_ctsdata.py`, one "Wrote ..." line per file for the other three -- and sends everything else (per-item progress messages, validation warnings, and a final total-LM-cost line via `arsgrammatica.summarize_lm_cost()`/`format_lm_cost()`) to stderr instead. The progress messages print right before each real LM call starts, so a long run over a large corpus doesn't look hung.
