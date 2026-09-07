# Growing `optimize_gepa.py`'s data pool from real texts (`--eval-file`/`--eval-dir`/`--val-fraction`)

`utilities/optimize_gepa.py` used to build its entire trainset from `tests/fixtures/gold_examples.py`'s `GOLD_EXAMPLES` -- a small, hand-curated set built to exercise every documented construction at least once, not a representative sample of real texts. With `arsgrammatica` now being used to read actual passages, and the resulting hand-verified-correct analyses piling up as saved files, `optimize_gepa.py` can pull those in too, on top of `GOLD_EXAMPLES` rather than instead of it -- and, since the pool can now grow past a couple dozen examples, it can hold out a real valset for GEPA instead of reusing the whole trainset for Pareto tracking.

## Usage

```
python utilities/optimize_gepa.py --eval-file corpus/livy1.cex corpus/livy2.cex
python utilities/optimize_gepa.py --eval-dir corpus/ --val-fraction 0.25
python utilities/optimize_gepa.py --eval-dir corpus/ --val-fraction 0   # old behavior: no held-out valset
```

`--eval-file` takes one or more paths directly; `--eval-dir` takes a directory and loads every file directly inside it (not recursive) -- combine both if you like, they add to the same pool. Neither is required: with no `--eval-file`/`--eval-dir` at all, the pool is still just `GOLD_EXAMPLES`, exactly as before.

## How a saved file becomes training examples

`build_trainset_from_analysis_files(paths)` reads each path with `read_analyses()`/`split_analysis_by_sentence()` -- the same two functions `marimo/latin_syntaxer_review.py` and `utilities/analyses_to_dot_pngs.py` already use to browse a saved analysis one sentence at a time, not anything new. For each sentence: its own `Sentence.tokens` (the pre-analysis token list -- implied/elided tokens were never part of it to begin with, see `notes/serialization_formats.md`) becomes the `tokens` input field directly, and `passage` is reconstructed from that sentence's own tokengraph slice via `rendering.tokengraph_to_text()` -- the same reconstruction `tests/fixtures/harvest.py`'s `gold_example_from_analysis()` defaults to when no explicit passage is given.

This does **not** verify a file's analyses are actually correct -- same caveat as `gold_example_from_analysis()`'s own docstring: judging that is still on you, before you ever save the file. It only checks that the file parses and each sentence's graph is well-formed enough to split. A file that fails either check is skipped, with a message on stderr, rather than aborting the whole run -- one bad file shouldn't cost you every other one.

## Holding out a real valset

`split_train_val(pool, val_fraction, seed)` shuffles a copy of the combined `GOLD_EXAMPLES` + harvested pool with a fixed `--seed` and slices off `--val-fraction` (default `0.2`) of it as a genuine valset, passed to `dspy.GEPA` separately from the trainset via `gepa.compile(..., valset=valset)`. Baseline and optimized scoring are now reported for trainset and valset separately, so a run can show whether GEPA is generalizing or just fitting the examples it's judged on. `--val-fraction 0` returns the whole pool as the trainset and an empty valset, `main()`'s cue to pass `valset=None` instead -- exactly the original behavior (GEPA reuses the trainset for Pareto tracking too), worth falling back to while the pool is still too small to split sensibly.

This is a different held-out mechanism from `utilities/model_bakeoff.py`'s `HELD_OUT_SLUGS`: that one is a fixed, hand-picked, stratified slice of `GOLD_EXAMPLES` (by slug) used to keep cross-*model* comparisons apples-to-apples run after run. `split_train_val()` is an ordinary random split of whatever pool one particular `optimize_gepa.py` invocation was given, used only to give that one GEPA run an honest generalization signal while it tunes a single model's prompt. Neither script reads or writes the other's held-out set.

It's also a different tool from `tests/fixtures/harvest.py`'s `gold_example_from_analysis()`/`format_gold_example_source()`, which hand-turns one real analysis into pasteable `GOLD_EXAMPLES` source (with a real slug, tags, and reasoning) for a permanent, documented regression fixture. That's still the right choice for a single example worth keeping forever in the test suite; `--eval-file`/`--eval-dir` is the lower-friction path for folding in dozens or hundreds of sentences at once just to give GEPA more to train/validate against.

## Tests

No dedicated pytest coverage, matching this codebase's existing convention for `optimize_gepa.py` and `model_bakeoff.py` (both live-LM scripts with no test file at all -- see `TESTING.md`). `build_trainset_from_analysis_files()` and `split_train_val()` are themselves pure functions with no LM calls, so they could get one if that convention changes, but neither has today.
