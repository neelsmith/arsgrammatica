"""arsgrammatica: a DSPy program analyzing the syntax of Latin passages
according to the scheme documented in syntax_model.md.
"""
 
from .models import Token, CitedText, Sentence, VerbalExpression, TokenAnalysis, RelationLabel
from .mermaid import tokengraph_to_mermaid, token_label
from .dot import tokengraph_to_dot, compute_graph_depths, max_graph_depth
from .graphs import GraphMetrics, tokengraph_to_networkx, graph_metrics
from .verbal_units import (
    assign_verbal_units,
    assign_verbal_unit_colors,
    compute_aat_depths,
    compute_subordination_depths,
    find_governing_verbal_expression,
    max_subordination_depth,
    find_unanchored_coordinated_verbs,
)
from .rendering import tokengraph_to_text, tokengraph_to_html, tokengraph_to_depth_html
from .latin_syntax_dspy import (
    SentenceAnalysis,
    analyze,
    validate,
    print_analysis,
)
from .segmentation_dspy import SegmentPassage, segment_sources
from .pipeline import analyze_string, analyze_sources, combined_tokengraph
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

# attgraph() depends on the separate `aat` package, which most callers of
# arsgrammatica have no need to install at all -- not on PyPI, so
# `pip install git+https://github.com/neelsmith/aat.git` (not a bare
# `pip install aat`) is what actually installs it; pyproject.toml's "aat"
# extra is only reachable if arsgrammatica itself is pip-installed
# (`pip install '.[aat]'` from a checkout, or an editable install) rather
# than just run from a checkout on sys.path, which is how this project is
# normally used. Importing it lazily/defensively here, rather than
# unconditionally like every other submodule above, means `import
# arsgrammatica` still succeeds without `aat` installed; only actually
# calling `arsgrammatica.attgraph(...)` without it raises, with a message
# naming the missing package and how to get it.
try:
    from .aat_bridge import attgraph
except ImportError as _exc:  # pragma: no cover -- exercised only when `aat` isn't installed
    # `except ... as name` implicitly deletes `name` once this block ends
    # (a Python gotcha, not specific to this code) -- reassign to a plain
    # variable first so attgraph(), called later, can still reference it.
    _aat_import_error = _exc

    def attgraph(*args, **kwargs):
        raise ImportError(
            "attgraph() needs the separate 'aat' package "
            "(https://github.com/neelsmith/aat), which isn't installed. "
            "Install it with: pip install git+https://github.com/"
            "neelsmith/aat.git -- (if you've also `pip install`ed "
            "arsgrammatica itself, rather than just running it from a "
            "checkout, `pip install '.[aat]'` from its own directory "
            "does the same thing via this package's 'aat' extra)."
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
    "tokengraph_to_dot",
    "compute_graph_depths",
    "max_graph_depth",
    "GraphMetrics",
    "tokengraph_to_networkx",
    "graph_metrics",
    "assign_verbal_units",
    "assign_verbal_unit_colors",
    "compute_aat_depths",
    "compute_subordination_depths",
    "find_governing_verbal_expression",
    "max_subordination_depth",
    "find_unanchored_coordinated_verbs",
    "tokengraph_to_text",
    "tokengraph_to_html",
    "tokengraph_to_depth_html",
    "SentenceAnalysis",
    "analyze",
    "analyze_string",
    "validate",
    "print_analysis",
    "SegmentPassage",
    "segment_sources",
    "analyze_sources",
    "combined_tokengraph",
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
    "attgraph",
]