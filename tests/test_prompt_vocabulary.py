"""
Guards against the hand-written SentenceAnalysis prompt drifting from the
vocabulary in models.py (which follows quarto/concepts/). Every relation
label, syntactic type and token type the models allow must be named, in
quotes, in SentenceAnalysis's docstring, so the LM is told about it.
"""

import typing

import pytest

from arsgrammatica.latin_syntax_dspy import SentenceAnalysis
from arsgrammatica.models import RelationLabel, SyntacticType, TokenType

_PROMPT = SentenceAnalysis.__doc__


@pytest.mark.parametrize(
    "value",
    sorted(set(typing.get_args(RelationLabel)) | set(typing.get_args(SyntacticType)) | set(typing.get_args(TokenType))),
)
def test_prompt_names_every_documented_value(value):
    assert f"'{value}'" in _PROMPT, f"SentenceAnalysis's docstring never mentions '{value}'"


@pytest.mark.parametrize(
    "retired",
    ["'coordinating conjunction'", "'subordinating conjunction'", "'attributive'",
     "'agent'", "'continued discourse'", "'implied subject'", "semantic type",
     "relatedtoken"],
)
def test_prompt_does_not_use_retired_vocabulary(retired):
    """Retired labels may still appear as ordinary grammatical English
    (e.g. "a subordinating conjunction", "purely attributive"), but never
    quoted as a value."""
    assert retired not in _PROMPT
