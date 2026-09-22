# Corpus scripts: what each one does (`utilities/tokenize_ctsdata.py`, `utilities/analyze_ctsdata_to_files.py`, `utilities/analyze_tokendata_to_files.py`, `utilities/analyze_w_diagrams.py`, `utilities/analyze_tokendata_w_diagrams.py`)

Five command-line scripts turn a `#!ctsdata` (CEX) source file, or an already-tokenized file derived from one, into syntax analyses and diagrams, at different stages and granularities. All five are corpus-scale siblings of `syntaxer_main.py` (which handles one hand-typed passage); none of them needs anything beyond the same `.env` that script does (`API_BASE`/`MODEL`/`API_KEY`).

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

## `analyze_tokendata_w_diagrams.py` -- analysis and diagrams, starting from already-tokenized files

The second half of `analyze_w_diagrams.py`'s own pipeline, taken on its own, same relationship `analyze_tokendata_to_files.py` has to `analyze_ctsdata_to_files.py`: reads one or more files written by `tokenize_ctsdata.py` (accepts several at once, like `analyze_tokendata_to_files.py` and unlike `analyze_w_diagrams.py`, which always takes exactly one raw corpus file), runs full syntax analysis on each sentence they already contain (`analyze_tokendata_to_files.py`'s own analyzing function, reused directly), then renders every resulting analysis file as a Graphviz PNG (`analyze_w_diagrams.py`'s own diagram-writing helper, reused directly). One analysis file per sentence lands directly under the output directory, with PNGs in a `dots/` subdirectory -- same layout `analyze_w_diagrams.py` itself produces, minus the tokenized-data file (there's nothing to write there: the input already *is* tokenized data). One `.env` read and one combined LM-cost total cover the single LM-calling stage (diagramming makes no LM calls). A file that can't be read as tokenized data is skipped, with a message on stderr, rather than aborting the whole run -- same convention `analyze_tokendata_to_files.py` uses. Use this instead of `analyze_w_diagrams.py` to split tokenizing from analyzing-and-diagramming (e.g. tokenize once, then analyze and diagram several times), or to review a tokenized file by hand before spending anything on real analysis.

```sh
python utilities/analyze_tokendata_w_diagrams.py tokenized.txt --output-dir out/
python utilities/analyze_tokendata_w_diagrams.py a.txt b.txt --output-dir out/
```

## What they all share

Each keeps stdout clean for its own real output -- the serialized segmentation for `tokenize_ctsdata.py`, one "Wrote ..." line per file for the other four -- and sends everything else (per-item progress messages, validation warnings, and a final total-LM-cost line via `arsgrammatica.summarize_lm_cost()`/`format_lm_cost()`) to stderr instead. The progress messages print right before each real LM call starts, so a long run over a large corpus doesn't look hung.

The four scripts that write to an output directory (every one above except `tokenize_ctsdata.py`, which writes a single combined stream to stdout instead) also share a `warnings.txt` file, written to that same directory once the run finishes, via `arsgrammatica.FailedPassage`/`write_warnings_report()`: one line per passage that failed to analyze outright, followed by the same total-LM-cost statement the stderr line above already gives. It's always written, even when nothing failed (it then just says so), and gets its own "Wrote ..." line on stdout like every other output file. This is deliberately a DIFFERENT notion of "failure" than the validation warnings and `write_analyses()` warnings already printed to stderr per file above: those cover an analysis that still happened but looks a little off (a referential problem `validate()` catches, a boundary-token mismatch `write_analyses()` catches); `warnings.txt` covers a passage that never produced an analysis at all -- its own `SentenceAnalysis` call raised outright, even after `token_budget.analyze_with_retry()`'s own retries were exhausted.

Before this, a single bad passage anywhere in a run aborted the WHOLE run -- worst of all in `analyze_ctsdata_to_files.py`, where every group's own sentences were batched in memory and only written to disk after every group had finished, so a failure in the last group could lose every earlier group's already-successful work too. That's no longer true for any of the four: one sentence's own analysis failing is caught and skipped (`pipeline.analyze_sources()`'s own `on_sentence_error` hook, for the two `ctsdata`-driven scripts; a plain per-sentence `try`/`except` in `analyze_tokendata_to_files()`, reused by both `tokendata`-driven scripts) -- every OTHER sentence, including the rest of its own group or file, still gets analyzed, written, and (for the two diagram scripts) diagrammed normally. `analyze_ctsdata_to_files.py` goes one level further: if a whole GROUP's own segmentation call fails outright (before any of its sentences even exist to fail individually), every passage in that group is recorded as failed by citation and the run moves on to the next group instead -- safe here specifically because this script writes one independent file per sentence, unlike `tokenize_ctsdata.py`'s own combined multi-block stream, where dropping a group would gap the contiguous id sequence `read_segmentation()` requires (so `tokenize_ctsdata.py`'s identical `segment_sources()` call is still deliberately fail-fast, and so is stage 1 of `analyze_w_diagrams.py`, which reuses it). Any of the four scripts still exits non-zero if any passage failed, on top of every exit-1 case it already had (an unreadable input file, or nothing written at all).
