"""arsgrammatica: a DSPy program analyzing the syntax of Latin passages
according to the scheme documented in syntax_model.md.
"""
 
from .models import Token, CitedText, Sentence, VerbalExpression, TokenAnalysis, RelationLabel
from .mermaid import tokengraph_to_mermaid
from .verbal_units import (
    assign_verbal_units,
    assign_verbal_unit_colors,
    compute_subordination_depths,
    max_subordination_depth,
    find_unanchored_coordinated_verbs,
)
from .rendering import tokengraph_to_text, tokengraph_to_html, tokengraph_to_depth_html
from .latin_syntax_dspy import (
    SyntaxAnalysis,
    analyze,
    validate,
    print_analysis,
)
from .segmentation_dspy import SegmentPassage, segment_sources
from .pipeline import analyze_passage, analyze_sources, combined_tokengraph
from .serialization import serialize_analyses, write_analyses, read_analyses
from .ctsdata import CtsDataRow, read_ctsdata
from .token_budget import estimate_max_tokens, analyze_with_retry, get_calibration

__all__ = [
    "Token",
    "CitedText",
    "Sentence",
    "VerbalExpression",
    "TokenAnalysis",
    "RelationLabel",
    "tokengraph_to_mermaid",
    "assign_verbal_units",
    "assign_verbal_unit_colors",
    "compute_subordination_depths",
    "max_subordination_depth",
    "find_unanchored_coordinated_verbs",
    "tokengraph_to_text",
    "tokengraph_to_html",
    "tokengraph_to_depth_html",
    "SyntaxAnalysis",
    "analyze",
    "analyze_passage",
    "validate",
    "print_analysis",
    "SegmentPassage",
    "segment_sources",
    "analyze_sources",
    "combined_tokengraph",
    "serialize_analyses",
    "write_analyses",
    "read_analyses",
    "CtsDataRow",
    "read_ctsdata",
    "estimate_max_tokens",
    "analyze_with_retry",
    "get_calibration",
]