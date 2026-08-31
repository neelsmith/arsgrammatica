"""
Deterministic plain-text serialization for segment_sources()'s own output
-- a `List[Sentence]` with NO syntax analysis run over it at all -- as a
lighter counterpart to serialization.py's own `#!sentences`/`#!verbal_units`/
`#!tokens` format, which is built around `TokenAnalysis`/`VerbalExpression`
(the *syntax analysis* stage's output). Use this module when you want to
save or reload just the segmentation stage's result -- what are the
sentences, what are their tokens -- without ever having run (or paid for)
syntax analysis; use `serialization.py` once you actually have a
`TokenAnalysis`/`VerbalExpression` result to save.

`utilities/tokenize_ctsdata.py` is this module's main caller: it reads a
`#!ctsdata` source file, segments the whole thing with `segment_sources()`,
and writes the result here for later review or analysis (see
`marimo/latin_syntaxer_tokenized.py`, which reads a file this module wrote,
lets you pick one sentence, and runs THAT one sentence through syntax
analysis on demand).

File shape: two line-oriented, pipe-delimited blocks, each introduced by a
label line alone on its own line, immediately followed by a fixed header
line naming that block's columns, then one data line per record:

    #!sentences
    context_begin|first_token|context_end|last_token
    Aeneid 1.1|t0|Aeneid 1.1|t4

    #!tokens
    context|sentence_index|id|text
    Aeneid 1.1|0|t0|Arma
    Aeneid 1.1|0|t1|virumque
    ...

`#!sentences` is EXACTLY `serialization.py`'s own `#!sentences` block --
same label, same header, same meaning (`context_begin`/`first_token` are a
sentence's own first token's citation/id; `context_end`/`last_token` its
own last token's citation/id) -- this module imports those two constants
directly from `serialization.py` rather than re-typing them, so the two
formats' shared block can never quietly drift apart. `#!tokens` shares its
NAME with `serialization.py`'s own `#!tokens` block, but not its columns:
there is no `tokentype`/`lemma`/relation data to write here, since nothing
in this module ever runs syntax analysis. Because of that column mismatch,
`serialization.read_analyses()` still cannot parse a file this module
writes as a whole, even though its `#!sentences` half alone is exactly
what that function expects.

`#!tokens` has one row per token, in sentence-then-token order: `context`
is that token's own `Token.citation` (named `context`, not `citation`, to
match `serialization.py`'s own column-naming convention for this field),
`sentence_index` is that token's own sentence's 0-based position across
the WHOLE file, `id`/`text` are the token's own `Token.id`/`Token.text`.
Unlike `serialization.py`'s own `#!tokens` block, sentence boundaries don't
need to be inferred from row position at all -- `sentence_index` names them
directly -- so `read_segmentation()` groups tokens by that column first,
then cross-checks the result against `#!sentences`' own first_token/
last_token/citations, raising `ValueError` immediately if they disagree
(e.g. a hand-edited file), rather than silently trusting one block over
the other.

As with every other pipe-delimited format in this codebase, no column may
contain a literal '|' or newline -- there is no escaping mechanism.
`serialize_segmentation()`/`write_segmentation()` raise `ValueError`
immediately, naming the offending row, for either. `read_segmentation()`
is deliberately strict, matching `serialization.read_analyses()`: a
missing block, a header line that doesn't match exactly, a row with the
wrong column count, a `sentence_index` that isn't a non-negative integer
or that skips a value, a duplicate token id, or a `#!sentences` row that
disagrees with the `#!tokens` block's own grouping, all raise `ValueError`
immediately, naming the offending line, rather than silently skipping or
guessing. Unlike `serialization.py`'s three required blocks, a label here
may NOT repeat -- this format is always written whole by one
`serialize_segmentation()` call, so there is no concatenated-file case to
support.
"""

from typing import Dict, List, Optional, Tuple

from .models import Sentence, Token
from .serialization import SENTENCES_LABEL, SENTENCES_HEADER

TOKENS_LABEL = "#!tokens"
TOKENS_HEADER = "context|sentence_index|id|text"

_EXPECTED_HEADERS = {
    SENTENCES_LABEL: SENTENCES_HEADER,
    TOKENS_LABEL: TOKENS_HEADER,
}


def _field(value: Optional[str], *, where: str) -> str:
    """Render one column value: `None` -> `''`, any other string verbatim
    -- after checking it contains none of '|'/newline/carriage-return,
    none of which this pipe-delimited format has any way to escape. Same
    convention as `serialization._field()`."""
    if value is None:
        return ""
    if "|" in value or "\n" in value or "\r" in value:
        raise ValueError(
            f"{where}: value {value!r} contains a '|' or a newline, which "
            "this pipe-delimited format has no way to escape"
        )
    return value


def _parse_optional(value: str) -> Optional[str]:
    """Inverse of `_field` for an optional column: '' -> None, anything
    else verbatim. Same convention as `serialization._parse_optional()`."""
    return value if value != "" else None


def serialize_segmentation(sentences: List[Sentence]) -> str:
    """Build the `#!sentences`/`#!tokens` text described in this module's
    own docstring for `sentences` -- `segment_sources()`'s own output, with
    no syntax analysis run over it -- and return it as a single string,
    including its trailing newline.

    Raises ValueError, naming the offending sentence/row, if any sentence
    has no tokens at all (nothing to derive `#!sentences`' own
    first_token/last_token from), or if any field value contains '|' or a
    newline (see `_field()`).
    """
    sentence_lines: List[str] = [SENTENCES_LABEL, SENTENCES_HEADER]
    token_lines: List[str] = [TOKENS_LABEL, TOKENS_HEADER]

    for s_idx, sentence in enumerate(sentences):
        if not sentence.tokens:
            raise ValueError(
                f"sentence at index {s_idx} has no tokens -- cannot derive "
                "#!sentences' own first_token/last_token for an empty sentence"
            )

        first_tok = sentence.tokens[0]
        last_tok = sentence.tokens[-1]
        where = f"#!sentences row for sentence {s_idx}"
        sentence_lines.append(
            "|".join(
                [
                    _field(first_tok.citation, where=where),
                    _field(first_tok.id, where=where),
                    _field(last_tok.citation, where=where),
                    _field(last_tok.id, where=where),
                ]
            )
        )

        for tok in sentence.tokens:
            where = f"#!tokens row for sentence {s_idx} token {tok.id!r}"
            token_lines.append(
                "|".join(
                    [
                        _field(tok.citation, where=where),
                        str(s_idx),
                        _field(tok.id, where=where),
                        _field(tok.text, where=where),
                    ]
                )
            )

    return "\n".join(sentence_lines + [""] + token_lines) + "\n"


def write_segmentation(sentences: List[Sentence], path: str) -> None:
    """Write `serialize_segmentation(sentences)`'s output straight to
    `path` (UTF-8), overwriting any existing file. Thin wrapper, same
    relationship `write_analyses()` has to `serialize_analyses()`."""
    content = serialize_segmentation(sentences)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def read_segmentation(path: str) -> List[Sentence]:
    """Read `path` (as written by `serialize_segmentation()`/
    `write_segmentation()`) and reconstruct the `List[Sentence]` it was
    built from -- see this module's own docstring for the file shape and
    what counts as malformed.

    Raises ValueError, naming the offending line, for: a missing
    `#!sentences` or `#!tokens` block; a label line with no header line
    before the next block or before the file ends; a header line that
    doesn't match exactly; a data row with the wrong column count; a
    `#!tokens` row with a blank id, a duplicate id, or a `sentence_index`
    that isn't a non-negative integer; `#!tokens`' own `sentence_index`
    values not forming a contiguous `0..N-1` range with no gaps; a mismatch
    in how many sentences `#!sentences` and `#!tokens` each imply; or a
    `#!sentences` row whose own first_token/last_token/citations disagree
    with the `#!tokens` block's own grouping for that sentence.
    """
    with open(path, "r", encoding="utf-8") as f:
        raw_lines = f.read().splitlines()

    blocks: Dict[str, List[Tuple[int, str]]] = {label: [] for label in _EXPECTED_HEADERS}
    seen_labels = set()
    current_label: Optional[str] = None
    awaiting_header = False

    for line_no, line in enumerate(raw_lines, start=1):
        if line.strip() == "":
            continue

        if line in _EXPECTED_HEADERS:
            if awaiting_header:
                raise ValueError(
                    f"line {line_no}: block {current_label!r} has a label "
                    "line but no header line before the next block starts"
                )
            if line in seen_labels:
                raise ValueError(
                    f"line {line_no}: block {line!r} appears more than "
                    "once -- this format doesn't support repeated blocks "
                    "(see module docstring)"
                )
            current_label = line
            seen_labels.add(line)
            awaiting_header = True
            continue

        if current_label is None:
            raise ValueError(
                f"line {line_no}: data line {line!r} appears before any "
                "'#!' block label"
            )

        if awaiting_header:
            expected = _EXPECTED_HEADERS[current_label]
            if line != expected:
                raise ValueError(
                    f"line {line_no}: expected header {expected!r} for "
                    f"block {current_label!r}, got {line!r}"
                )
            awaiting_header = False
            continue

        blocks[current_label].append((line_no, line))

    missing = sorted(set(_EXPECTED_HEADERS) - seen_labels)
    if missing:
        raise ValueError(f"file is missing required block(s): {missing}")
    if awaiting_header:
        raise ValueError(
            f"block {current_label!r} has a label line but no header line "
            "(and no data) -- the file ends too early"
        )

    # --- #!tokens: parse rows, then group into per-sentence lists by
    # sentence_index, preserving each row's own file order within a group. ---
    seen_ids = set()
    parsed_rows: List[Tuple[int, int, str, Optional[str], str]] = []
    for line_no, line in blocks[TOKENS_LABEL]:
        parts = line.split("|")
        if len(parts) != 4:
            raise ValueError(
                f"line {line_no}: #!tokens row has {len(parts)} column(s), "
                f"expected 4: {line!r}"
            )
        context, sentence_index_raw, tok_id, text = parts
        if tok_id == "":
            raise ValueError(f"line {line_no}: #!tokens row has an empty id")
        if tok_id in seen_ids:
            raise ValueError(f"line {line_no}: duplicate token id {tok_id!r} in #!tokens")
        seen_ids.add(tok_id)

        try:
            sentence_index = int(sentence_index_raw)
        except ValueError:
            raise ValueError(
                f"line {line_no}: #!tokens row's sentence_index "
                f"{sentence_index_raw!r} is not an integer"
            ) from None
        if sentence_index < 0:
            raise ValueError(
                f"line {line_no}: #!tokens row's sentence_index "
                f"{sentence_index} is negative"
            )

        parsed_rows.append((line_no, sentence_index, tok_id, _parse_optional(context), text))

    groups: Dict[int, List[Tuple[str, Optional[str], str]]] = {}
    for _line_no, sentence_index, tok_id, citation, text in parsed_rows:
        groups.setdefault(sentence_index, []).append((tok_id, citation, text))

    num_sentences = len(groups)
    if sorted(groups) != list(range(num_sentences)):
        raise ValueError(
            f"#!tokens block's sentence_index values are {sorted(groups)}, "
            f"expected a contiguous 0..{max(num_sentences - 1, 0)} range "
            "with no gaps and no negative values"
        )

    sentences: List[Sentence] = [
        Sentence(
            tokens=[
                Token(id=tok_id, text=text, citation=citation)
                for tok_id, citation, text in groups[s_idx]
            ]
        )
        for s_idx in range(num_sentences)
    ]

    # --- #!sentences: cross-check against the #!tokens block's own grouping. ---
    if len(blocks[SENTENCES_LABEL]) != num_sentences:
        raise ValueError(
            f"#!sentences has {len(blocks[SENTENCES_LABEL])} row(s) but "
            f"#!tokens implies {num_sentences} sentence(s) -- these must match"
        )

    for s_idx, (line_no, line) in enumerate(blocks[SENTENCES_LABEL]):
        parts = line.split("|")
        if len(parts) != 4:
            raise ValueError(
                f"line {line_no}: #!sentences row has {len(parts)} "
                f"column(s), expected 4: {line!r}"
            )
        context_begin, first_id, context_end, last_id = parts
        if first_id == "" or last_id == "":
            raise ValueError(
                f"line {line_no}: #!sentences row is missing first_token "
                f"or last_token: {line!r}"
            )

        sentence = sentences[s_idx]
        if not sentence.tokens:
            raise ValueError(f"line {line_no}: sentence {s_idx} has no tokens in the #!tokens block")
        actual_first, actual_last = sentence.tokens[0], sentence.tokens[-1]

        if first_id != actual_first.id or last_id != actual_last.id:
            raise ValueError(
                f"line {line_no}: #!sentences row for sentence {s_idx} "
                f"names first_token/last_token {first_id!r}/{last_id!r}, "
                f"but the #!tokens block's own sentence {s_idx} group runs "
                f"from {actual_first.id!r} to {actual_last.id!r}"
            )

        parsed_begin = _parse_optional(context_begin)
        parsed_end = _parse_optional(context_end)
        if parsed_begin != actual_first.citation:
            raise ValueError(
                f"line {line_no}: #!sentences row's context_begin "
                f"{parsed_begin!r} does not match the #!tokens block's "
                f"recorded citation {actual_first.citation!r} for token "
                f"{first_id!r}"
            )
        if parsed_end != actual_last.citation:
            raise ValueError(
                f"line {line_no}: #!sentences row's context_end "
                f"{parsed_end!r} does not match the #!tokens block's "
                f"recorded citation {actual_last.citation!r} for token "
                f"{last_id!r}"
            )

    return sentences
