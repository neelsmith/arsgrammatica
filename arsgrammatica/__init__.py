"""arsgrammatica: a DSPy program analyzing the syntax of Latin passages
according to the scheme documented in syntax_model.md.
"""
 
from .models import Token, CitedText, Sentence, VerbalExpression, TokenAnalysis, RelationLabel
from .mermaid import tokengraph_to_mermaid
from .verbal_units import assign_verbal_units
from .rendering import tokengraph_to_text
from .latin_syntax_dspy import (
    SyntaxAnalysis,
    analyze,
    validate,
    print_analysis,
)
from .segmentation_dspy import SegmentPassage, segment_sources
from .pipeline import analyze_passage, analyze_sources, combined_tokengraph
 
__all__ = [
    "Token",
    "CitedText",
    "Sentence",
    "VerbalExpression",
    "TokenAnalysis",
    "RelationLabel",
    "tokengraph_to_mermaid",
    "assign_verbal_units",
    "tokengraph_to_text",
    "SyntaxAnalysis",
    "analyze",
    "analyze_passage",
    "validate",
    "print_analysis",
    "SegmentPassage",
    "segment_sources",
    "analyze_sources",
    "combined_tokengraph",
]