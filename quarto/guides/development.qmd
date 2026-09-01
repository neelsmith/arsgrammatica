# Developing `arsgrammatica`

`USAGE.md` describes how to call the pipeline, `TESTING.md` how to run the offline test suite, `OPTIMIZING.md` how to tune `SyntaxAnalysis`'s prompt with GEPA, and `BAKEOFF.md` how to compare candidate models. Each of those describes one tool. This document describes how they fit together into a repeatable development loop, centered on testing the analyzer against real Latin text rather than just the hand-picked `GOLD_EXAMPLES` corpus.


## Why real-world testing, not just the gold-example suite

`tests/fixtures/gold_examples.py`'s `GOLD_EXAMPLES` is a deliberately curated corpus: `test_coverage.py` enforces that every documented relation label, verbal-expression classification, and token type in `syntax_model.md` has at least one example exercising it, and the whole `pytest` suite runs against `DummyLM`, not a real model. That combination is exactly right for what it's for -- proving the code (`models.py`'s pydantic models, `validate()`, `verbal_units.py`, `rendering.py`, `mermaid.py`, `serialization.py`) correctly *represents* a correct answer -- but it can't tell you whether a live model actually *produces* one, and it can't surface a construction nobody has thought to write a fixture for yet.

Running the analyzer against real Latin passages -- actual prose, not fixtures written to order -- is where you find the things the gold-example suite structurally can't show you:

- a construction `syntax_model.md` doesn't document at all yet (this is exactly how the implied/elided-token feature -- `implied sum` and `continued discourse` in `TokenAnalysis.tokentype` -- came about: a real passage needed it, `syntax_model.md` was extended first, then the models/prompt/fixtures followed; see "A worked precedent" below);
- a construction the scheme already documents, but the current prompt still gets wrong;
- a genuinely ambiguous case that exposes a modeling choice worth deciding and flagging explicitly (`syntax_model.md` calling a construction a "circumstantial participle" when `VerbalExpression.syntactic_type` has no such value is a real example already resolved this way in `models.py`'s own docstrings -- flag the judgment call in a comment near the fixture, don't just quietly pick one and move on);
- an ordinary, everyday construction the model already handles correctly -- not new information about the scheme, but real evidence worth locking in as a regression guardrail so a future prompt or model change can't silently break it without anyone noticing.


## The core loop: analyze, check automatically, review by hand, triage, act

1. **Analyze a real passage.** `analyze_passage(passage)` for a single string, or `analyze_sources(sources)` for a list of citation-labeled `CitedText` (see USAGE.md's "Analyzing citable sources") -- either returns `(sentences, results)`, one `SyntaxAnalysis` result per sentence found.

2. **Run the automated checks first, before reading anything by hand.** `analyze_sources()` already calls `validate()` for you and prints any referential problems it finds (a token id that doesn't exist, a malformed implied token); `find_unanchored_coordinated_verbs(result.tokengraph)` (`verbal_units.py`) catches one more specific, observed live-LM mistake (a coordinating-conjunction pair where only one side anchors its own verbal unit) that's self-consistent enough to slip past `validate()`. Both are cheap and mechanical -- let them rule out the "obviously broken" cases before you spend a human read on anything.

3. **Read the surviving result against `syntax_model.md` by hand.** This is the one step nothing in the codebase can do for you: `validate()` only checks referential integrity, never correctness, and neither `find_unanchored_coordinated_verbs()` nor any metric can substitute for actually knowing the Latin. `tokengraph_to_html()`/`tokengraph_to_depth_html()` (`rendering.py`, see `VISUALIZATION.md`) or `tokengraph_to_mermaid()` (`mermaid.py`) are worth rendering here -- seeing the verbal-unit coloring and subordination depth laid out is usually faster to check by eye than reading the raw `tokengraph` rows.

4. **Triage what you found into one of three outcomes, and act accordingly** (see the next section). Every outcome below can be turned into a `GoldExample` with `tests/fixtures/harvest.py`'s `gold_example_from_analysis()` -- the difference between them is what you do with the result afterward, not how you build it.


## The three outcomes, and what to do with each

### Outcome A: a failure

Something is referentially broken (`validate()`/`find_unanchored_coordinated_verbs()` caught it) or substantively wrong (you caught it by hand). Don't just note it and move on -- a failure is the most valuable signal this loop produces, because it's the main way the scheme and the prompt actually improve. Triage it further, in this order:

1. **Is `syntax_model.md` actually silent or ambiguous about this construction?** If so, this is a scheme gap, not a model mistake. Extend `syntax_model.md` first, then follow USAGE.md's "Extending the scheme" steps: add the new relation label / `tokentype` / `syntactic_type` value to the relevant `Literal` in `arsgrammatica/models.py`, describe when to use it in `SyntaxAnalysis`'s docstring in `arsgrammatica/latin_syntax_dspy.py`, and hand-write a `GoldExample` with a *correct* `canned_answer` exercising it (since the live model, by definition, didn't produce one) in `tests/fixtures/gold_examples.py`. This is exactly how the implied-token feature was built.
2. **Is the scheme already clear, but the prompt/model got it wrong anyway?** Hand-write a corrected `GoldExample` for the passage the same way, so the failure becomes a concrete, checkable trainset entry rather than an anecdote. If you're unsure between two defensible readings, say so explicitly in a comment above the fixture (matching the existing convention in `gold_examples.py` for judgment calls like the circumstantial-participle-of-*sum* case) rather than silently committing to one.
3. Re-run `pytest` (fast, `DummyLM`-backed -- see TESTING.md) to confirm the new/corrected fixture actually validates and that `test_coverage.py` is satisfied, *before* spending any real API budget re-testing it against the live model.

Either way, the corrected fixture lands in `GOLD_EXAMPLES` -- see "How this feeds `OPTIMIZING.md` and `BAKEOFF.md`" below for what that means downstream.

### Outcome B: a success against a rare or tricky construction

The model got something genuinely uncommon or structurally hard right -- a deep subordination chain, a construction with few other examples in `GOLD_EXAMPLES`, anything you'd be nervous betting the model gets right consistently. This is worth *reinforcing*, not just recording: use `gold_example_from_analysis()` to build the `GoldExample` from the real `sentences`/`result.verbalunits`/`result.tokengraph` (passing `result.reasoning` too, since `dspy.ChainOfThought` gives you a real one for free here, not a placeholder), then `format_gold_example_source()` to get paste-ready source for `gold_examples.py`. Add it straight to `GOLD_EXAMPLES` as ordinary trainset material -- a correct demonstration of a rare case is precisely the kind of thing `optimize_gepa.py`'s trainset benefits from having more of, and precisely what `model_bakeoff.py`'s `bootstrap` stage is designed to lock in as a few-shot demo for a candidate model that doesn't reliably get it right zero-shot.

### Outcome C: a success against a common, ordinary construction

The model got something right that it was already expected to get right -- a plain independent clause, an ordinary direct object, nothing structurally novel. This is real evidence, but low-value as *training* signal: `optimize_gepa.py` has no held-out split at all today (see below), so anything added to `GOLD_EXAMPLES` is immediately part of what GEPA both trains against and scores itself against, and an easy case the model already nails teaches the optimizer nothing new -- it just dilutes the trainset with redundant coverage. The better default is to harvest it the same way, add it to `GOLD_EXAMPLES`, *and* add its slug to `model_bakeoff.py`'s `HELD_OUT_SLUGS` (see BAKEOFF.md's "The held-out evaluation set"). That turns it into a regression check: something that already works today, now protected against silently breaking as the prompt, the scheme, or the underlying model changes later -- exactly the role `model_bakeoff.py`'s held-out set exists to play, and one that only gets more useful as it grows more diverse.

The dividing line, in short: rare-and-tricky successes are worth teaching the optimizer with; common-and-already-reliable successes are worth protecting with a regression check. "Which bucket does this belong in" is a judgment call about how common the construction already is in `GOLD_EXAMPLES`, not about whether the analysis happened to be correct -- both outcomes started from a correct analysis.


## How this feeds `OPTIMIZING.md` and `BAKEOFF.md`

`optimize_gepa.py` (OPTIMIZING.md) trains `SyntaxAnalysis`'s prompt against *all* of `GOLD_EXAMPLES`, with no separate held-out valset at all -- per `dspy.GEPA`'s own behavior when none is given, the trainset doubles as the Pareto-tracking set GEPA scores itself against. That means every fixture this loop adds to `GOLD_EXAMPLES` -- a corrected failure (Outcome A) or a harvested rare-construction success (Outcome B) -- becomes real trainset material the next time `optimize_gepa.py` runs, which is the main way the shipped prompt actually improves over time: not synthetic examples, but real passages that either broke something or demonstrated something worth reinforcing.

**A known gap worth being aware of**: `optimize_gepa.py` has no mechanism today to *exclude* anything from its trainset -- unlike `model_bakeoff.py`, it doesn't consult `HELD_OUT_SLUGS` (or anything else) to keep held-out examples out of what it trains against. So an Outcome-C fixture you add specifically to protect as a held-out regression check for `model_bakeoff.py` purposes still gets folded into `optimize_gepa.py`'s trainset the next time it runs -- the two scripts don't currently share one consistent notion of "held out." Until that's addressed (e.g. by teaching `optimize_gepa.py` to skip `HELD_OUT_SLUGS` too), treat the held-out/trainset distinction described above as meaningful specifically *for `model_bakeoff.py`'s cross-model comparisons*, not as an airtight guarantee that held-out examples never influence the production prompt.

`model_bakeoff.py` (BAKEOFF.md) is the one place in this repo with an actual train/eval firewall: its `gepa`/`bootstrap` stages never train against `HELD_OUT_SLUGS`, so every candidate model is compared on the same untouched slice. That slice was deliberately stratified by hand when it was first built (one plain independent clause, a couple of dependent-clause shapes, a coordinated-verb pair, an indirect statement, a circumstantial participle, a depth-2 nesting case, three newer relations); every Outcome-C fixture this loop produces is a natural way to keep growing that stratification with real passages rather than more hand-constructed ones, making `model_bakeoff.py`'s cross-model comparisons more representative as the held-out set grows.

Put together: this loop is the thing that keeps both downstream tools honest over time. Without it, `optimize_gepa.py` only ever optimizes against a fixed, hand-written snapshot of the scheme, and `model_bakeoff.py` only ever compares candidates against that same fixed snapshot -- neither one improves just by running the scripts again. Real-world testing is what actually grows and diversifies the corpus both scripts depend on.


## A worked precedent: the implied/elided-token feature

The `implied sum`/`continued discourse` `tokentype` values (`arsgrammatica/models.py`'s `IMPLIED_TOKENTYPES`) are a concrete example of the Outcome-A loop above, in the order it actually happened:

1. A real passage needed a construction `syntax_model.md` didn't document: an elided form of *sum*, and a shared governing verb of indirect discourse left unrepeated across coordinate clauses.
2. `syntax_model.md` was extended with an "understood or implied verbal expressions" section describing both cases and the id-naming convention for a token with no surface realization.
3. `arsgrammatica/models.py`'s `TokenAnalysis.tokentype` gained the two new `Literal` values (plus the shared `IMPLIED_TOKENTYPES` constant so every consumer -- `validate()`, `rendering.py`, `serialization.py`, `conftest.py` -- checks membership in one place rather than hardcoding either string), and `SyntaxAnalysis`'s docstring in `latin_syntax_dspy.py` documented exactly when to use each one and how to name the new token's id.
4. Four new hand-written `GoldExample` entries were added to `gold_examples.py`, one per documented sub-case, each with a correct `canned_answer` -- since this was new scheme, not something a live model had already demonstrated -- and `test_coverage.py` confirmed both new `tokentype` values were now exercised.
5. One genuine judgment call came up along the way (whether an implied ablative-absolute participle's `syntactic_type` should be `'dependent'`, since `syntax_model.md`'s own phrase "circumstantial participle" isn't a valid `syntactic_type` value) -- it was resolved by matching this codebase's existing convention for every other circumstantial participle, and flagged explicitly rather than decided silently.

Nothing about this loop required a live model at all -- it's the pure Outcome-A path, scheme-gap-first. A rare-construction success (Outcome B) or a common-construction success (Outcome C) follows the same shape starting from step 4/5 instead, using `tests/fixtures/harvest.py` to build the fixture from a real analysis rather than writing the `canned_answer` by hand.


## Suggested cadence

- After any batch of real-world testing/harvesting, run `pytest` (TESTING.md) first -- it's fast and `DummyLM`-backed, and will immediately tell you if a new or corrected fixture doesn't actually validate or if `test_coverage.py` regressed.
- Run `optimize_gepa.py` (OPTIMIZING.md) periodically to refresh the shipped, production prompt against whatever `GOLD_EXAMPLES` has grown into since the last run -- this is a live-LM script with real API cost, so batch it rather than running it after every single new fixture.
- Run `model_bakeoff.py` (BAKEOFF.md) periodically -- before adopting a new candidate model, or whenever the held-out set has grown enough to be worth re-checking -- to confirm existing candidates still stand where you last measured them, now against a larger, more representative held-out slice.
