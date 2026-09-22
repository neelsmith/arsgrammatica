# Making arsgrammatica dspy-free at import time, for WASM export

Neel's question: `marimo/latin_syntaxer_review.py` (and its sibling read/render-only notebooks) is useful entirely apart from the DSPy pipeline -- it loads an already-saved analysis and renders it -- and `marimo export html-wasm` would let it run as a standalone page with no Python install at all. Three packages block that today, per Neel's own investigation:

- **litellm**: current releases (1.102.0 when checked) ship only native `cp310-abi3` wheels -- no `py3-none-any` build -- because of a new Rust extension. `dspy` hard-requires `litellm>=1.65.8` with no way around it from arsgrammatica's side. (The last pure-Python litellm release, 1.91.5, would still satisfy that constraint if pinned, but that's a workaround for dspy's own dependency, not something this package controls.)
- **tokenizers**: native-only wheels (0.23.2 when checked); a known, currently-unresolved Pyodide build limitation on Hugging Face's side.
- **fastuuid**: native-only wheels (0.14.0 when checked), no pure-Python fallback anywhere.

All three come in transitively, through `dspy` -> `litellm` (and `dspy`'s own use of `tokenizers`/`fastuuid`). Nothing in arsgrammatica imports any of them directly.

## The package already splits cleanly along dspy lines

Tracing every `import dspy`/`from dspy...` in `arsgrammatica/`: only four modules ever touch it -- `latin_syntax_dspy.py`, `segmentation_dspy.py`, `token_budget.py`, and `gepa_metric.py` (the last isn't even re-exported from `__init__.py`; only `optimize_gepa.py` uses it directly). `pipeline.py` imports from the first two plus `token_budget.py`, so it inherits the dependency rather than introducing a new one.

Nothing else -- `models.py`, `mermaid.py`, `dot.py`, `graphs.py`, `verbal_units.py`, `rendering.py`, `displacy_viz.py`, `serialization.py`, `segmentation_serialization.py`, `ctsdata.py`, `passage_grouping.py`, `token_ids.py`, `lm_cost.py`, `run_report.py`, `lewis_short.py`, `aat_bridge.py` -- imports dspy at all. That's the entire "read/render/serialize a saved analysis" half of the package, and it needs only `pydantic` and `networkx`.

`token_budget.py` was a partial exception: it imports `dspy`, `dspy.utils.exceptions.AdapterParseError`, and `.latin_syntax_dspy.analyze` at module scope, but only two of its functions (`_finish_reason_was_length()`, `analyze_with_retry()`) actually use any of the three. `DEFAULT_CEILING`, `get_calibration()`, `estimate_max_tokens()`, `_looks_truncated()`, and `_missing_token_ids()` never touch dspy at all -- they were just unable to import cleanly because of the three names sitting at the top of the same file.

## What was actually blocking `latin_syntaxer_review.py`

Not the notebook itself -- its own `from arsgrammatica import (...)` (in its "Imports" cell) names only: `aatgraph`, `filter_tokengraph_by_aat_depth`, `max_subordination_depth`, `read_analyses`, `split_analysis_by_sentence`, `tokengraph_to_depth_html`, `tokengraph_to_displacy_svg`, `tokengraph_to_dot`, `tokengraph_to_html`, `tokengraph_to_mermaid`, `tokengraph_to_text` -- every one of them from the dspy-free half above. `marimo/latin_syntaxer_graph_metrics.py` and `marimo/lewis_short_lookup.py` are the same story (`graph_metrics`, `read_analyses`, `split_analysis_by_sentence`, `tokengraph_to_networkx`, `tokengraph_to_text`; `LEWIS_SHORT_URL`, `LewisShortLexicon`).

What actually blocked all three was `arsgrammatica/__init__.py` itself: it unconditionally did `from .latin_syntax_dspy import (...)`, `from .segmentation_dspy import (...)`, and `from .pipeline import (...)` before any of those notebooks' own names were reachable -- so a bare `import arsgrammatica`, even just to get `read_analyses`, dragged in dspy regardless. `pyproject.toml` compounded this by listing `dspy>=3.0` as an unconditional dependency, which would trip up any installer trying to resolve arsgrammatica's declared requirements (not just a `sys.path`-based checkout import).

The other four marimo notebooks -- `latin_syntaxer_ctsdata.py`, `latin_syntaxer_selected_ids.py`, `latin_syntaxer_textinput.py`, `latin_syntaxer_tokenized.py` -- do call `analyze()`/`analyze_sources()`/`analyze_string()`/`analyze_with_retry()`/`validate()`, i.e. they actually invoke the live LM pipeline. **Those stay blocked from WASM export regardless of anything in this repo**, since litellm/tokenizers/fastuuid's native-wheel situation is upstream Pyodide/Hugging-Face/dspy territory, not something `reader.py`-side code can route around.

## What changed

1. **`arsgrammatica/__init__.py`**: the three dspy-dependent import blocks (`latin_syntax_dspy`, `segmentation_dspy`, `pipeline`) are now wrapped in a `try`/`except ImportError`, following the exact pattern already established here for the optional `aat` package (`aatgraph()`, just below this new block). With dspy installed, every name (`SentenceAnalysis`, `analyze`, `validate`, `print_analysis`, `SegmentPassage`, `segment_sources`, `analyze_string`, `analyze_sources`, `analyze_selected_passages`, `analyze_ctsdata`, `combined_tokengraph`) is the real thing, unchanged. Without it, each becomes a stub that raises a clear `ImportError` -- naming `pip install 'arsgrammatica[llm]'` -- only when actually *called*, not on import.

2. **`arsgrammatica/token_budget.py`**: its three dspy-touching imports (`import dspy`, `from dspy.utils.exceptions import AdapterParseError`, `from .latin_syntax_dspy import analyze`) are now inside a `try`/`except ImportError` too, with fallbacks: `dspy = None` (so `_finish_reason_was_length()`'s existing `dspy.settings.lm` lookup fails with `AttributeError`, which that function already catches and treats as "no" -- no code changes needed there), a placeholder `AdapterParseError` exception class (so `except AdapterParseError:` in `analyze_with_retry()` stays syntactically valid), and a stub `analyze()` that raises the same `arsgrammatica[llm]` `ImportError`. `analyze` and `AdapterParseError` stay real *module-level* names either way -- deliberately not deferred into the functions that use them -- because `tests/test_token_budget.py` does `monkeypatch.setattr("arsgrammatica.token_budget.analyze", fake_analyze)` in three places; deferring the import into the function body would have removed that attribute entirely and broken those tests.

3. **`pyproject.toml`**: `dspy>=3.0` moved out of `dependencies` into a new `llm` extra (`llm = ["dspy>=3.0"]`); base `dependencies` is now just `pydantic>=2.0` and `networkx>=3.0`. The `dev` extra now depends on `arsgrammatica[llm]` (a self-referential extra, supported since pip 21.2/modern setuptools) so nothing about the documented dev workflow (`pip install -e ".[dev]"`) changes -- dspy is still there for anyone running the test suite or the notebooks that need it.

No changes were needed to any marimo notebook -- they already only import the dspy-free names.

### A gotcha worth flagging (caught during verification, not left in)

The first draft of the `token_budget.py` fallback wrote `except ImportError as _dspy_import_error:` and referenced `_dspy_import_error` later, inside `analyze()`'s stub body. That's exactly the "Python gotcha" `aatgraph()`'s own existing comment in `__init__.py` already warns about: `except ... as name` implicitly deletes `name` once the `except` block ends, so by the time `analyze()` is actually *called*, `_dspy_import_error` no longer exists and the stub raises `NameError` instead of the intended `ImportError`. Fixed by reassigning to a plain variable inside the block (`_dspy_import_error = _dspy_exc`) before the block ends, matching `__init__.py`'s own `_llm_import_error = _llm_exc` pattern. Caught by actually exercising the no-dspy path (see Verification below), not by inspection -- worth remembering that this class of bug is invisible unless the fallback branch is actually executed at least once.

## Verification

Two throwaway venvs (both outside version control, deleted afterward):

- One with the full normal dev environment (`dspy`, `pydantic`, `networkx`, `pytest`, `aat`): `pytest -q` -> **1826 passed, 2 skipped, 7 deselected**, identical to before this change.
- One with only `pydantic`+`networkx` installed -- no `dspy`, no `litellm`, no `tokenizers`, no `fastuuid` anywhere on the path -- confirming: `import arsgrammatica` succeeds; the exact `from arsgrammatica import (...)` lines from `latin_syntaxer_review.py`, `latin_syntaxer_graph_metrics.py`, and `lewis_short_lookup.py` all succeed unchanged; every dspy-only name (`analyze`, `segment_sources`, `analyze_string`, `analyze_sources`, `validate`, `print_analysis`, `analyze_selected_passages`, `analyze_ctsdata`, `combined_tokengraph`, `analyze_with_retry`) raises a clean `ImportError` naming the `llm` extra when called; `DEFAULT_CEILING`, `estimate_max_tokens()`, and `get_calibration()` all still work normally.

## What this does *not* solve

Splitting the import graph is necessary but not sufficient for "import arsgrammatica directly from GitHub" inside an actual `marimo export html-wasm` bundle. That export installs dependencies through Pyodide's `micropip`, which only reliably installs pure-Python **wheels** -- from PyPI, or a direct URL to a `.whl` file served with CORS headers -- not a bare `git+https://...` reference or an sdist it would build on the fly. (That syntax works fine for a normal desktop `marimo edit`/venv, which is a completely different code path from the WASM export.) `raw.githubusercontent.com` is also inconsistent about CORS headers, so pointing micropip straight at a raw file URL is not reliable.

Two realistic paths once arsgrammatica itself is a pure-Python package (true as of this change, modulo the `llm`/`aat` extras neither of which the review notebooks need): publish it as a normal wheel to PyPI or TestPyPI (the standard, most-assumed-by-tooling path), or build the wheel and serve it through jsDelivr's GitHub-CDN mirror (`cdn.jsdelivr.net/gh/neelsmith/arsgrammatica@<tag-or-commit>/dist/...whl`), which does serve GitHub repo contents with proper CORS headers. Either way, the notebook's own dependency declaration (a PEP 723 `# /// script` header, for `marimo export`) would need to point at that wheel URL rather than the git repo directly.

Separately: `pydantic-core` now ships official Emscripten/Pyodide wheels as of pydantic v2.14 (2026), under the new PEP 783, so pydantic itself is no longer a WASM blocker; `networkx` is pure Python and was never a concern.

## Left alone (possible follow-up, not done here)

`validate()` (referential-integrity checking of an already-produced `tokengraph` -- no LM call in its own body) still lives in `latin_syntax_dspy.py`, so it's still gated behind the `llm` extra even though nothing in its own logic needs dspy -- only the module it happens to live in does, because that module also defines `SentenceAnalysis(dspy.Signature)`. Same story for `combined_tokengraph()` in `pipeline.py`. Neither is used by any of the three currently-WASM-target notebooks, so this wasn't worth the larger, more invasive move (relocating functions between modules, updating every other importer) for this pass -- but if a future viz-only notebook wants `validate()` specifically, that's the natural next refactor: split it out into a dspy-free module (or `models.py` itself) rather than adding another `__init__.py`-level stub for it.

## Files touched

- `arsgrammatica/__init__.py`
- `arsgrammatica/token_budget.py`
- `pyproject.toml`

Not committed -- per `CLAUDE.md`, that's Neel's call.
