"""arsgrammatica: a DSPy program analyzing the syntax of Latin passages
according to the scheme documented in syntax_model.md.
"""
 
from .models import Token, CitedText, Sentence, VerbalExpression, TokenAnalysis, RelationLabel
from .mermaid import tokengraph_to_mermaid, token_label, save_mermaid
from .dot import tokengraph_to_dot, compute_graph_depths, max_graph_depth, save_dot
from .graphs import GraphMetrics, tokengraph_to_networkx, graph_metrics
from .verbal_units import (
    assign_verbal_units,
    assign_verbal_unit_colors,
    compute_aat_depths,
    compute_subordination_depths,
    filter_tokengraph_by_aat_depth,
    find_governing_verbal_expression,
    max_aat_depth,
    max_subordination_depth,
    find_unanchored_coordinated_verbs,
)
from .rendering import tokengraph_to_text, tokengraph_to_html, tokengraph_to_depth_html
from .displacy_viz import (
    tokengraph_to_displacy_data,
    tokengraph_to_displacy_svg,
    save_displacy_html,
)
# latin_syntax_dspy.py, segmentation_dspy.py, and pipeline.py all touch
# dspy at *class-definition* time (dspy.Signature subclasses), not just at
# call time, so -- unlike aatgraph()'s lazy import below -- there's no way
# to defer dspy out of these three modules' own imports. That makes dspy
# the one thing standing between "import arsgrammatica" and working in an
# environment that can't have dspy installed at all: current dspy releases
# hard-require litellm>=1.65.8, and current litellm releases ship native
# cp310-abi3 wheels only (a Rust extension), which blocks Pyodide/WASM
# environments outright -- see notes/wasm_export.md. None of that is
# specific to *this* package, though: nothing else in arsgrammatica
# (models.py, rendering.py, mermaid.py, dot.py, graphs.py, verbal_units.py,
# displacy_viz.py, serialization.py, ctsdata.py, lewis_short.py, ...) ever
# imports dspy, so a caller who only wants to read/render/serialize
# already-saved analyses -- exactly what marimo/latin_syntaxer_review.py
# does -- has no actual need for dspy at all. Following the same
# lazy-import-with-a-helpful-stub pattern aatgraph() already uses below for
# the optional `aat` package, this block lets `import arsgrammatica` (and
# now, per pyproject.toml's new `llm` extra, the base install itself)
# succeed either way: with dspy installed, every name below is the real
# thing; without it, calling any of them raises a clear ImportError naming
# `pip install 'arsgrammatica[llm]'` instead of failing this whole import
# with dspy's own, less legible ImportError.
try:
    from .latin_syntax_dspy import (
        SentenceAnalysis,
        analyze,
        validate,
        print_analysis,
    )
    from .segmentation_dspy import SegmentPassage, segment_sources
    from .pipeline import (
        analyze_string,
        analyze_sources,
        analyze_selected_passages,
        analyze_ctsdata,
        combined_tokengraph,
    )
except ImportError as _llm_exc:
    _llm_import_error = _llm_exc

    def _llm_stub(_name):
        def _stub(*_args, **_kwargs):
            raise ImportError(
                f"{_name}() needs the optional 'llm' extra (dspy, and a "
                "configured LM) to analyze new Latin text -- install it "
                "with: pip install 'arsgrammatica[llm]'. Reading, "
                "rendering, or serializing an already-saved analysis "
                "(read_analyses(), tokengraph_to_html(), etc.) doesn't "
                "need dspy at all and works without this extra."
            ) from _llm_import_error

        _stub.__name__ = _name
        return _stub

    SentenceAnalysis = _llm_stub("SentenceAnalysis")
    analyze = _llm_stub("analyze")
    validate = _llm_stub("validate")
    print_analysis = _llm_stub("print_analysis")
    SegmentPassage = _llm_stub("SegmentPassage")
    segment_sources = _llm_stub("segment_sources")
    analyze_string = _llm_stub("analyze_string")
    analyze_sources = _llm_stub("analyze_sources")
    analyze_selected_passages = _llm_stub("analyze_selected_passages")
    analyze_ctsdata = _llm_stub("analyze_ctsdata")
    combined_tokengraph = _llm_stub("combined_tokengraph")
from .passage_grouping import group_passages_by_sentence_boundary
from .token_ids import assign_passage_scoped_ids
from .serialization import (
    LMInfo,
    serialize_analyses,
    write_analyses,
    read_analyses,
    split_analysis_by_sentence,
)
from .ctsdata import read_ctsdata
from .segmentation_serialization import (
    serialize_segmentation,
    write_segmentation,
    read_segmentation,
)
from .token_budget import estimate_max_tokens, analyze_with_retry, get_calibration, DEFAULT_CEILING
from .lm_cost import LMCostSummary, summarize_lm_cost, format_lm_cost
from .run_report import FailedPassage, format_warnings_report, write_warnings_report
from .lewis_short import (
    LewisShortEntry,
    LewisShortMatch,
    LewisShortLexicon,
    LEWIS_SHORT_URL,
    read_lewis_short,
    read_lewis_short_from_url,
)

# aatgraph() depends on the separate `aat` package, which most callers of
# arsgrammatica have no need to install at all -- not on PyPI, so
# `pip install git+https://github.com/neelsmith/aat.git` (not a bare
# `pip install aat`) is what actually installs it; pyproject.toml's own
# "aat" extra, or its `dev` extra (which includes "aat" too, since
# marimo/latin_syntaxer_review.py -- itself only reachable via `dev` --
# is the one thing in this repo that actually calls aatgraph()), are only
# reachable if arsgrammatica itself is pip-installed (`pip install
# '.[dev]'` from a checkout, or an editable install) rather than just run
# from a checkout on sys.path, which is how this project is normally used
# -- see notes/install.md's "Dev-only tools" for installing `aat` by hand
# in that case instead. Importing it lazily/defensively here, rather than
# unconditionally like every other submodule above, means `import
# arsgrammatica` still succeeds without `aat` installed; only actually
# calling `arsgrammatica.aatgraph(...)` without it raises, with a message
# naming the missing package and how to get it.
try:
    from .aat_bridge import aatgraph
except ImportError as _exc:  # pragma: no cover -- exercised only when `aat` isn't installed
    # `except ... as name` implicitly deletes `name` once this block ends
    # (a Python gotcha, not specific to this code) -- reassign to a plain
    # variable first so aatgraph(), called later, can still reference it.
    _aat_import_error = _exc

    def aatgraph(*args, **kwargs):
        raise ImportError(
            "aatgraph() needs the separate 'aat' package "
            "(https://github.com/neelsmith/aat), which isn't installed. "
            "Install it with: pip install git+https://github.com/"
            "neelsmith/aat.git -- (if you've also `pip install`ed "
            "arsgrammatica itself, rather than just running it from a "
            "checkout, `pip install '.[dev]'` from its own directory "
            "does the same thing, along with the rest of this repo's dev "
            "tooling -- see notes/install.md)."
        ) from _aat_import_error

__all__ = [
    "Token",
    "CitedText",
    "Sentence",
    "VerbalExpression",
    "TokenAnalysis",
    "RelationLabel",
    "tokengraph_to_mermaid",
    "token_label",
    "save_mermaid",
    "tokengraph_to_dot",
    "compute_graph_depths",
    "max_graph_depth",
    "save_dot",
    "GraphMetrics",
    "tokengraph_to_networkx",
    "graph_metrics",
    "assign_verbal_units",
    "assign_verbal_unit_colors",
    "compute_aat_depths",
    "compute_subordination_depths",
    "filter_tokengraph_by_aat_depth",
    "find_governing_verbal_expression",
    "max_aat_depth",
    "max_subordination_depth",
    "find_unanchored_coordinated_verbs",
    "tokengraph_to_text",
    "tokengraph_to_html",
    "tokengraph_to_depth_html",
    "tokengraph_to_displacy_data",
    "tokengraph_to_displacy_svg",
    "save_displacy_html",
    "SentenceAnalysis",
    "analyze",
    "analyze_string",
    "validate",
    "print_analysis",
    "SegmentPassage",
    "segment_sources",
    "analyze_sources",
    "analyze_selected_passages",
    "analyze_ctsdata",
    "combined_tokengraph",
    "group_passages_by_sentence_boundary",
    "assign_passage_scoped_ids",
    "LMInfo",
    "serialize_analyses",
    "write_analyses",
    "read_analyses",
    "split_analysis_by_sentence",
    "read_ctsdata",
    "serialize_segmentation",
    "write_segmentation",
    "read_segmentation",
    "estimate_max_tokens",
    "analyze_with_retry",
    "get_calibration",
    "DEFAULT_CEILING",
    "LMCostSummary",
    "summarize_lm_cost",
    "format_lm_cost",
    "FailedPassage",
    "format_warnings_report",
    "write_warnings_report",
    "LewisShortEntry",
    "LewisShortMatch",
    "LewisShortLexicon",
    "LEWIS_SHORT_URL",
    "read_lewis_short",
    "read_lewis_short_from_url",
    "aatgraph",
]