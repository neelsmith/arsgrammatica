# Estimating the cost of analyzing a whole corpus (`utilities/estimate_corpus_cost.py`)

A command-line utility: read a `#!ctsdata` (CEX) corpus file, sample `n` passages out of it at random, and run only THOSE through full syntax analysis (segmentation, then every sampled sentence's own `SentenceAnalysis`) -- writing their combined analyses to one output file (`serialization.py`'s `write_analyses()` format, same as `utilities/analyze_ctsdata_to_files.py`'s own per-sentence output). The point is the report it then writes to stdout: the sample's own cost per sentence and per token, multiplied out against a mechanical, LM-free APPROXIMATION of the WHOLE corpus's own sentence/token counts, to estimate what fully analyzing every passage in the file would cost -- without actually paying for that yet, and without spending a real LM call just to count the corpus either.

## Usage

```sh
python3 utilities/estimate_corpus_cost.py corpus.cex
python3 utilities/estimate_corpus_cost.py corpus.cex --n 10
python3 utilities/estimate_corpus_cost.py corpus.cex --n 10 --output-file sample.cex
python3 utilities/estimate_corpus_cost.py corpus.cex --seed 42
python3 utilities/estimate_corpus_cost.py corpus.cex --delimiter ';'
```

`--n` (default 5) is how many passages to sample; `--output-file` (default `analyses.cex`) is where the sample's own combined analyses are written; `--delimiter` is the SOURCE file's own column delimiter (passed to `read_ctsdata()`, unrelated to the '|'-delimited output file); `--seed` seeds the random sample for a reproducible selection across runs (omit it for a different sample every run). Needs the same `.env` as `syntaxer_main.py` (`API_BASE`/`MODEL`/`API_KEY`) -- this makes real LM calls.

## The whole corpus's own counts are mechanical, not real segmentation

An earlier version of this script got the corpus's own total sentence/token counts from one real `segment_sources()` call over the ENTIRE corpus, up front -- accurate, but itself a real (if usually much smaller) LM call, and for a genuinely large corpus, slow or costly in its own right: exactly the kind of expense this script exists to help avoid paying blindly. So the corpus-wide counts are now purely mechanical -- no LM call at all, via `_approximate_corpus_counts()`:

- **Tokens**: a plain whitespace word count across every passage's own raw text (`len(text.split())`, summed) -- the same rough measure `wc -w` gives on the command line. This is NOT the same notion as the sample's own real token count (see below): a whitespace split undercounts relative to real segmentation, since e.g. "cano." is one whitespace-word but two real tokens ("cano", "."). Any estimate built on it should be read as a rough, likely UNDER-estimate for exactly that reason.
- **Sentences**: `len(groups)` from `passage_grouping.py`'s own fast, LM-free `group_passages_by_sentence_boundary()` (also used by `utilities/group_ctsdata_by_sentence.py`) -- a per-passage text-ending heuristic with no cross-passage reasoning at all. It already documents getting abbreviations/elisions wrong (a trailing period misread as sentence-final -- see `notes/passage_grouping.md`), and using its group COUNT as a sentence count adds a second source of error on top of that: a single passage whose own raw text already contains more than one complete sentence is still only ONE group, so this can UNDER-count on exactly that kind of passage too.

Both are deliberately rough stand-ins, not a substitute for real segmentation -- the two extrapolated cost estimates at the end of the report are approximations of an approximation. `_approximate_corpus_counts()` also returns whatever warnings `group_passages_by_sentence_boundary()` itself raised (only ever the one case: its final group not ending at a sentence boundary) -- printed to stderr, not part of the report itself (see below).

## Isolating the sample's own cost

The report's "total cost" (and everything derived from it) only ever covers the `n`-passage sample's own full analysis -- one `analyze_sources([candidate])` call per sampled passage (see "A passage that fails is skipped, not fatal" below for why it's one call per passage rather than one batched call). This is done by snapshotting `len(lm.history)` immediately before the first candidate is tried and only summing (`summarize_lm_cost()`) history entries recorded from that point on, in `estimate_corpus_cost()`. There's no longer a separate whole-corpus LM call for this to also need to exclude -- the corpus-wide counts above make none at all.

## What "sentences"/"tokens" mean for the sample

The sample's own counts are always real segmentation's counts: `len(sentences)`, and each sentence's own `len(sentence.tokens)`, i.e. the tokens actually fed INTO analysis. This deliberately excludes any "implied" token (an implied subject, an implied "sum", etc. -- see `serialization.py`'s module docstring) a sentence's own full analysis might additionally synthesize into its `tokengraph`. There's no comparable "implied token" notion for the corpus-wide word count to match either way, so the sample side stays built the same, narrower way it always was -- it's the corpus side that's now a rough approximation, not the sample side.

## The report

One labelled item per line, written to stdout (diagnostics -- any `group_passages_by_sentence_boundary()` warning, `write_analyses()`'s own warnings if any, and a "Wrote ..." line -- go to stderr instead, same stdout/stderr split `analysis_to_dot.py`/`analyses_to_dot_pngs.py` already use, so stdout carries nothing but the report):

- Passages analyzed (always `n`)
- Sentences analyzed / Tokens analyzed -- the sample's own, real counts
- Total cost / Cost per sentence / Cost per token -- the sample's own, isolated cost (see above)
- Sentences in entire corpus (approx.) / Tokens in entire corpus (approx., word count) -- from `_approximate_corpus_counts()`, no LM call
- Estimated cost (approx. corpus sentences x cost per sentence)
- Estimated cost (approx. corpus tokens x cost per token)

If every one of the sample's own LM calls happened to be served from cache (`summarize_lm_cost()`'s own `total_cost=None` case -- see `lm_cost.py`'s module docstring), or `n` was 0, every cost-derived line reads "N/A" with a reason, rather than raising `ZeroDivisionError` or printing a misleading `$0.00`. `--n` below 1, or greater than the corpus's own passage count, is rejected by the CLI before any LM is even configured.

## A passage that fails is skipped, not fatal

A live LM call can fail outright -- a malformed/unparseable response, a rate limit, a timeout. Rather than losing the whole sample (and whatever it already cost) to one bad passage, each of the `n` passages is analyzed with its OWN, individual `analyze_sources([candidate])` call, one at a time, in a random order built up front (`_random_order()` -- a full shuffled permutation of every passage in the corpus, not just `n` of them). A candidate whose call raises is skipped: its citation and the exception (`f"{type(exc).__name__}: {exc}"`) are recorded in `estimate_corpus_cost()`'s returned `failed_passages`, and the loop just moves on to the next untried candidate in that same random order -- so the sample still always ends up with exactly `n` successfully analyzed passages, and `--n` in the report's "Passages analyzed" line is never a lie. The broad `except Exception` this needs (a live LM call can fail in more ways than any one exception type covers) matches `utilities/model_bakeoff.py`'s own `_score_program()` precedent -- "that's data about this one item, not a bug in the script."

Every passage is tried AT MOST ONCE, success or failure -- there's no retrying a passage that already failed. If the corpus runs out of untried passages before `n` have succeeded (e.g. `--n 4` against a corpus where only 3 of its passages can ever be analyzed successfully), `estimate_corpus_cost()` raises `RuntimeError` naming how many succeeded, how many failed, and why for each -- rather than silently reporting fewer than `n`, which would make "Passages analyzed" a fixed `n` that quietly wasn't true anymore.

This costs giving up `analyze_sources()`'s own cross-passage sentence-spanning: `utilities/analyze_ctsdata_to_files.py`'s batched `analyze_sources(cited_texts)` call lets one sentence run from the end of one passage's text into the start of the next, but batching several passages into one call is exactly what would let a single bad response discard however many good sentences the OTHER passages in that batch would otherwise have contributed -- and leave no one passage to blame (and replace) for it. Analyzing one passage at a time is what makes "skip this one, try another" possible at all. Passages that succeed are still combined into the output file in the corpus's own file order (not the random order they happened to succeed in), by sorting on each accepted passage's original corpus index before flattening -- purely for a human reading the file, since nothing downstream needs it sorted.

Cost accounting deliberately still includes whatever a failed passage spent before failing (e.g. a real, billed call that came back malformed) -- `len(lm.history)` is snapshotted once, before the FIRST candidate (successful or not) is tried, so `summarize_lm_cost()` sums every entry from that point on, failures included. That's real spend incurred getting to an n-passage sample, not overhead worth hiding from the report.

Failures are diagnostic detail, not part of the report itself: `__main__` prints one "Skipped passage ... after a failed analysis: ..." line per failure to stderr (plus a one-line summary count), same stdout/stderr split as `write_analyses()`'s own warnings -- stdout carries nothing but `format_report()`'s own lines.

## Progress heartbeat

Analyzing `n` passages one at a time is `n` (or more, with failures -- see above) separate, real LM calls, and nothing prints between them by default -- a long-running sample can go quiet for a while and look hung even though it's working normally. So every `n` ATTEMPTS (successful or not -- not `n` successes; with a failed-and-replaced passage in the mix, this can fire before the sample is actually done), `_log_progress_banner()` prints a conspicuous, hard-to-miss banner to stderr:

```
======================================================================
>>> PROGRESS: 10 passage(s) tried so far -- 8 accepted, 2 failed (need 10 accepted total) <<<
======================================================================
```

This is a heartbeat, not a diagnostic -- it's not part of `CorpusCostEstimate`, doesn't appear in `format_report()`'s own report, and (like every other diagnostic in this script) is stderr-only, so it never contaminates stdout's report. It exists purely so a long run's own silence doesn't read as stuck.

## Testing

Its own separable functions -- `_approximate_corpus_counts(cited_texts)`, `_random_order(cited_texts, rng=None)`, and `estimate_corpus_cost(cited_texts, n, output_path, lm, model=None, rng=None)` -- were exercised directly (bypassing argument parsing and `_configure_lm()`). `_approximate_corpus_counts()` was checked directly against a hand-counted fixture (confirming the word count and the group count both match by hand, with no LM configured at all -- there's nothing to stub, since this function makes no calls). `estimate_corpus_cost()` was then exercised with `analyze_sources` monkeypatched to fake per-passage results (one fixed to always raise) across a four-passage corpus, confirming: the mechanical corpus counts land unchanged in the returned `CorpusCostEstimate`; a mid-run failure is recorded in `failed_passages` and a replacement is drawn so the sample still reaches exactly `n`; the failed passage's own data never appears in the output file; the output stays in corpus file order despite the random trial order; requesting more successes than the corpus can ever provide raises `RuntimeError`; and an oversized `n` still raises `ValueError` before any LM call at all. `format_report()` was checked rendering both cache-served ("N/A") and priced report variants. No dedicated pytest file, matching every other CLI entry point in `utilities/` (e.g. `analyze_ctsdata_to_files.py`, `tokenize_ctsdata.py`) -- each is a thin wrapper around already-tested library functions (`read_ctsdata()`, `analyze_sources()`, `group_passages_by_sentence_boundary()`, `write_analyses()`, `summarize_lm_cost()`).
