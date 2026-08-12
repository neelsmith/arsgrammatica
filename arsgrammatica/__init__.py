"""arsgrammatica: a DSPy program analyzing the syntax of Latin passages
according to the scheme documented in notes.md.
"""

from .models import Token, VerbalExpression, TokenAnalysis, RelationLabel
from .tokenizer import tokenize
from .mermaid import tokengraph_to_mermaid
from .latin_syntax_dspy import (
    SyntaxAnalysis,
    analyze,
    analyze_passage,
    validate,
    print_analysis,
)

__all__ = [
    "Token",
    "VerbalExpression",
    "TokenAnalysis",
    "RelationLabel",
    "tokenize",
    "tokengraph_to_mermaid",
    "SyntaxAnalysis",
    "analyze",
    "analyze_passage",
    "validate",
    "print_analysis",
]
