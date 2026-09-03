# Selecting passages to analyze (`pipeline.analyze_selected_passages()`)

`analyze_sources()` (`pipeline.py`) already takes a `List[CitedText]` and analyzes all of it. `analyze_selected_passages()` is a thin wrapper in front of it, for the common case of a bigger source list (e.g. everything `read_ctsdata()` loaded from a file) where only some passages are wanted for a given run.

## Usage

```python
from arsgrammatica import analyze_selected_passages, read_ctsdata

cited_texts = read_ctsdata("genesis.ctsdata")
sentences, results = analyze_selected_passages(
    ["urn:cts:compnov:bible.genesis.vulgate:12.7", "urn:cts:compnov:bible.genesis.vulgate:12.8"],
    cited_texts,
)
```

Same return shape as `analyze_sources()`: `(sentences, results)`, one entry per sentence segmentation finds across the selected passages, in order.

## Ordering: selection order, not request order

`passage_ids` is a *filter*, not a sort key. The selected passages are analyzed in `cited_texts`' own order -- the order they appear in the source list -- regardless of what order `passage_ids` lists them in. This matches `marimo/latin_syntaxer_ctsdata.py`'s own `selected_rows` cell, which filters the same way for the same reason: `segment_sources()` (inside `analyze_sources()`) treats consecutive sources as potentially sharing a sentence, so handing it an out-of-file-order list could segment incorrectly, or produce citations in a confusing order. If you want passages analyzed in some order other than the source file's own, reorder `cited_texts` itself before calling, not `passage_ids`.

## Unknown ids

Every entry of `passage_ids` must match some `cited_texts` entry's `citation`. If any don't, `analyze_selected_passages()` raises `ValueError` naming every missing id at once, before calling out to segmentation or the LM at all -- a typo'd or stale passage id fails loudly rather than silently analyzing fewer passages than asked for.

## Tests

`tests/test_pipeline_selection.py` covers: selecting a proper subset skips the rest; selection follows `cited_texts`' order even when `passage_ids` is given out of order; an unknown id raises without any DummyLM configured (so an unexpected LM call would surface as a different, more confusing failure instead of silently passing).

## `marimo/latin_syntaxer_selected_ids.py`

A notebook UI for `analyze_selected_passages()`, alongside `latin_syntaxer_ctsdata.py`'s own multiselect-menu notebook: browse for a `#!ctsdata` source file, then type or paste the exact list of passage ids to analyze -- separated by whitespace (spaces and/or newlines; `parse_passage_ids()` is just Python's own `str.split()`), NOT commas -- rather than picking them off a menu. This is deliberately whitespace-delimited so a line of `utilities/group_ctsdata_by_sentence.py`'s own stdout output (space-joined by default -- see `notes/passage_grouping.md`) can be pasted straight into the box with no reformatting; a CTS URN never contains whitespace, so this never splits an id in half. Meant for the case where the ids are already in hand (piped in from that script's output, or copied from some other process), where re-clicking through a multiselect menu would just be friction.

A reference listing of every id actually available in the loaded file is shown above the id text box, since this notebook has no menu of its own to browse. Any typed id that doesn't match a passage in the loaded file is named in a callout immediately (a `missing_ids` cell checks this up front, the same way `ctsdata_error` handles an unreadable file), and the Analyze button stays disabled until every typed id resolves -- `analyze_selected_passages()`'s own `ValueError` is still caught as a defensive backstop, but shouldn't ordinarily fire, since the button is what normally prevents an invalid selection from ever reaching it.

Everything downstream of selection -- the Mermaid diagram, the highlighted/indented HTML views, the `#!LM`-tagged `write_analyses()`-format download -- is unchanged from `latin_syntaxer_ctsdata.py`, since both notebooks feed the exact same `(sentences, results)` shape into the same rendering cells.

No dedicated test file, matching this codebase's existing convention for marimo notebooks (none of them have one) -- its own new logic (`parse_passage_ids()`, the id-validation cells) is plain, easily-inspected list/set comprehensions, and the notebook's cell graph itself was checked with `marimo export script` (confirms every cell's dependencies resolve, with no undefined variables) plus a run of the exported script against a dummy `.env`, both cross-checked against an identical run of `latin_syntaxer_ctsdata.py` itself to confirm the two behave the same way outside marimo's interactive kernel.
