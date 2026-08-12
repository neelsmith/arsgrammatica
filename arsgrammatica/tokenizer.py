"""Deterministic tokenization for arsgrammatica.

The tokenizer keeps the LM away from raw text segmentation. It assigns stable
ids in order, splits off common Latin enclitics, and preserves praenomen
abbreviations such as ``M.`` as single tokens.
"""

from __future__ import annotations

import re
from typing import Iterable, List

from .models import Token


_RAW_TOKEN_RE = re.compile(r"[A-Z]\.|[A-Za-z]+(?:'[A-Za-z]+)?|\d+|[^\w\s]", re.UNICODE)
_PRAENOMEN_RE = re.compile(r"^[A-Z]\.$")
_PUNCTUATION_RE = re.compile(r"^[^\w\s]+$")
_ENCLITICS = ("que", "ve", "ne")


def _split_enclitic(token_text: str) -> tuple[str, str] | None:
    lower_text = token_text.lower()
    for enclitic in _ENCLITICS:
        if lower_text.endswith(enclitic):
            base_text = token_text[: -len(enclitic)]
            if base_text:
                return base_text, token_text[-len(enclitic) :]
    return None


def _classify_token(token_text: str) -> str:
    if _PRAENOMEN_RE.match(token_text):
        return "praenomen"
    if token_text.isdigit():
        return "numeral"
    if _PUNCTUATION_RE.match(token_text):
        return "punctuation"
    if token_text.isalpha() and token_text.islower():
        return "lexical"
    return "lexical"


def _expand_raw_token(token_text: str) -> Iterable[tuple[str, str]]:
    if _PRAENOMEN_RE.match(token_text):
        yield token_text, "praenomen"
        return

    if token_text.isdigit():
        yield token_text, "numeral"
        return

    if _PUNCTUATION_RE.match(token_text):
        yield token_text, "punctuation"
        return

    split = _split_enclitic(token_text)
    if split is not None:
        base_text, enclitic_text = split
        yield base_text, _classify_token(base_text)
        yield enclitic_text, "enclitic"
        return

    yield token_text, _classify_token(token_text)


def tokenize(passage: str) -> List[Token]:
    """Segment ``passage`` into stable ``Token`` objects.

    Tokens are emitted in reading order with ids ``t0``, ``t1``, ...
    """

    tokens: List[Token] = []
    for raw_token in _RAW_TOKEN_RE.findall(passage):
        for token_text, _ in _expand_raw_token(raw_token):
            tokens.append(Token(id=f"t{len(tokens)}", text=token_text))
    return tokens