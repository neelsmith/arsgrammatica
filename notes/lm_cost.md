# LM cost display (`arsgrammatica.lm_cost`)

`marimo/` has 7 notebooks; 4 of them actually make LM calls (`latin_syntaxer_ctsdata.py`, `latin_syntaxer_selected_ids.py`, `latin_syntaxer_workflow.py`, `latin_syntaxer_tokenized.py` -- each configures a `dspy.LM` and calls `analyze_sources()`/`analyze_string()`/`analyze_selected_passages()`/`analyze_with_retry()`), and all 4 now show a cost. The other 3 (`latin_syntaxer_dot.py`, `latin_syntaxer_graphs.py`, `latin_syntaxer_review.py`) never import `dspy` at all -- they only browse a previously-saved analysis file (`read_analyses()`), with no LM involved anywhere, so there's no `lm.history` for them to report and no cost cell was added to them. (Verified by grep, not assumption: `grep -n "import dspy\|dspy\." marimo/latin_syntaxer_{dot,graphs,review}.py` returns nothing.)

The first 3 LM-consuming notebooks had converged on the same small, broken pattern for reading cost out of `lm.history`:

```python
last_call = lm.history[-1] if lm.history else None
cost = last_call.get('cost')
```

Two separate problems with that, both fixed by `arsgrammatica.lm_cost`:

## `lm.history[-1]` is `None` before the first LM call -- which is the default state

`lm.history` is a `dspy.LM` instance's own list of every call it's made -- always a list, never `None` itself, but empty (`[]`) until at least one call happens. Every one of these notebooks starts that way: `lm.history` is empty the moment the notebook loads, before the Analyze button has ever been clicked. The old pattern's own `if lm.history: last_call = lm.history[-1]` guard correctly left `last_call` as `None` in that case -- but nothing downstream guarded `last_call` itself, so the very next cell's `last_call.get('cost')` raised `AttributeError: 'NoneType' object has no attribute 'get'` unconditionally, on load, regardless of whether the "See cost" checkbox was even checked. This is the crash Neel kept running into.

## `cost` on one call is `None` on a cache hit -- not a bug, but unlabeled

Even once there IS a `last_call`, its own `cost` can legitimately be `None`: `dspy.LM` caches responses by default (keyed on model + messages + config -- see each notebook's own "Disable LM cache (debugging)" checkbox), and `dspy`'s own history-recording code sets `cost` to `None` specifically when a call was served from that cache rather than actually billed (`BaseLM._process_lm_response()`'s own comment: "cost is None on cache hit"). The old display just printed `f"...: {cost}"`, so a cached call showed up as a bare, unexplained "None" with no indication that this was expected, not broken.

## `lm.history[-1]` is also just the LAST call, not the total

A single Analyze click can make several LM calls -- one for segmentation, plus one more per sentence (`analyze_sources()`/`analyze_string()`, both of which may segment their input into multiple sentences). Looking only at `lm.history[-1]` reports the cost of whichever sentence happened to be analyzed last, not the cost of the click that triggered all of them. `latin_syntaxer_workflow.py` had even labeled this "**Total cost**", which it never was.

## A fourth problem, found only after the first three were fixed: the cost cell never re-runs at all

Fixing the crash (above) surfaced a deeper issue that had been masked by it: after fixing the `AttributeError`, the cost display still read "no LM calls yet" forever, even after a successful Analyze click. The cause is a marimo reactivity gotcha, not a `dspy` one. `lm.history` is a list that gets APPENDED to in place by each LM call -- but `lm` itself, the variable, is never reassigned after `configure_lm()` first creates it. marimo's reactive execution only re-runs a cell when a variable it actually reads gets reassigned to something new; it has no way to see that `lm.history`'s CONTENTS changed underneath an unchanged `lm` reference. So a cell written as `def _(lm, summarize_lm_cost): cost_summary = summarize_lm_cost(lm.history)` runs exactly once -- when `lm` is first configured, while `lm.history` is still empty -- and then never again, no matter how many analyses happen afterward. (The original `last_call`/`cost` cells had this exact same blind spot; it was simply invisible behind the crash the first three fixes above already removed.)

The fix is to give the cost cell a second, genuine dependency on something that DOES get reassigned on every Analyze click -- each notebook's own `results` list, rebuilt fresh by the Analysis cell every time. The subtlety: marimo derives a cell's dependencies from actual name usage inside the cell's BODY (via its own static analysis), not from whatever names happen to be listed in the function signature -- so merely adding `results` to the parameter list, without reading it anywhere in the body, has NO effect and was silently ignored (confirmed directly against marimo's own dependency graph while fixing this). The working fix reads it, even though nothing is done with the value:

```python
@app.cell
def _(lm, results, summarize_lm_cost):
    _ = results  # forces this cell to re-run on every new `results` -- see the cell's own comment
    cost_summary = summarize_lm_cost(lm.history)
    return (cost_summary,)
```

Verified directly against marimo's own dependency graph (`app._graph`, via `marimo._ast.load.load_app`) rather than by inference: before this fix, the cell defining `cost_summary` had `refs = {'lm', 'summarize_lm_cost'}`; after it, `refs = {'lm', 'results', 'summarize_lm_cost'}`, with `results` itself transitively descending from each notebook's actual trigger (`analyze_button` for the two ctsdata-based notebooks, `input_form` for `latin_syntaxer_workflow.py`) -- confirming the cost cell now genuinely reruns on the same click/submission that produces a new analysis, not just once at notebook load.

## The cost-computation fix

`arsgrammatica.summarize_lm_cost(history)` sums `cost` across every entry in `lm.history` (or any list shaped like it), counting priced vs. cache-hit ("uncosted") entries separately, and never raises -- an empty or all-cache-hit history comes back with `total_cost=None` rather than a crash or a made-up `$0.00`. `arsgrammatica.format_lm_cost(summary)` renders that as one line covering every case: no calls yet, calls but all cached, a mix (priced total plus a note that some calls aren't included), or every call priced. Each notebook's own cost cell is now, combined with the reactivity fix above:

```python
@app.cell
def _(lm, results, summarize_lm_cost):
    _ = results  # forces a re-run on every new analysis -- see the reactivity fix above
    cost_summary = summarize_lm_cost(lm.history)
    return (cost_summary,)

@app.cell(hide_code=True)
def _(cost_summary, format_lm_cost, mo, seecost):
    costdisplay = None
    if seecost.value:
        costdisplay = mo.md(f"**LM cost so far**: {format_lm_cost(cost_summary)}")
    costdisplay
    return
```

## Tests

`tests/test_lm_cost.py` covers: empty history, an all-cache-hit history, a mix of priced and cached calls (the realistic multi-sentence case), singular-vs-plural wording, an entry missing its `cost` key entirely (treated the same as `cost=None`, not a `KeyError`), a `cost=0.0` call (a real, non-cached, genuinely free call -- correctly NOT lumped in with cache hits, since `0.0 is not None`), and a defensive check that a non-dict entry with a `.cost` attribute is still read correctly (today's `dspy.LM` always produces plain dicts, but this guards against a future version that doesn't). No dspy involved in any of it -- these functions only care that `history` entries are dict- or attribute-shaped with a `cost` key, so the tests use hand-built fixtures, not `DummyLM`.

## Notebooks updated

`latin_syntaxer_ctsdata.py`, `latin_syntaxer_selected_ids.py`, and `latin_syntaxer_workflow.py`'s "Analysis" section each have a single `cost_summary = summarize_lm_cost(lm.history)` cell (with a `_ = results` reactivity line -- see above) in place of the old `last_call`/`cost` pair, and their "See cost" display cell calls `format_lm_cost(cost_summary)`.

`latin_syntaxer_tokenized.py` never had a cost cell (or a "See cost" checkbox, or any of `latin_syntaxer_ctsdata.py`'s other debug checkboxes -- `seetokens`/`seeprompts`/`disable_cache`) at all, despite making real LM calls of its own (`analyze_with_retry()` in its Analysis cell) -- it was simply missing this whole feature, not carrying a broken version of it. It now has the same `seecost` checkbox and `cost_summary`/`costdisplay` pair as the other three, using its own per-click signal (`result`, singular -- this notebook analyzes one sentence at a time, not a list) in place of `results` for the same reactivity trick: `_ = result` inside the `cost_summary` cell. Its other debug checkboxes (`seetokens`/`seeprompts`/`disable_cache`) were deliberately NOT added -- out of scope for "this feature" (LM cost), and adding UI this notebook never had before, beyond what was asked, isn't this note's call to make.

Verified three different ways, since the underlying bugs needed different kinds of check:

- The crash and the cost math: exporting each notebook to a plain script (`marimo export script`, confirming the cell graph itself still resolves) and running it against a dummy `.env` with no LM calls made (`lm.history` empty, the exact state that used to crash) -- all four now get past the cost cell cleanly. `latin_syntaxer_workflow.py` and `latin_syntaxer_tokenized.py` run start to finish with no errors at all outside marimo's interactive kernel; `latin_syntaxer_ctsdata.py` and `latin_syntaxer_selected_ids.py` still hit one unrelated, pre-existing issue further down (their own depth-slider cell dereferences `maxdepth.value` while `maxdepth` is `None`, before any sentence has been analyzed) -- that's marimo's own per-cell error isolation not applying outside its interactive kernel, present before this change and unrelated to `lm.history`/cost, so it's left alone here.
- The reactivity fix: exporting a script only proves a cell runs once, top to bottom -- it can't show whether a cell would re-run on a SECOND interaction, since there's no interactive kernel driving it. That was checked directly against marimo's own dependency graph instead (see "A fourth problem" above) -- confirming `results`/`result` actually became one of `cost_summary`'s cell's real dependencies in each of the four notebooks, and that it transitively traces back to each notebook's own click/submit trigger (`analyze_button` in three of them, `input_form` in `latin_syntaxer_workflow.py`).
- The 3 excluded notebooks: confirmed by grep, not by reading each one end to end, that none of them import `dspy` at all -- see the module intro above.
