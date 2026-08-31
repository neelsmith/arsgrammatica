"""
Command-line utility: read every passage out of a `#!ctsdata` (CEX) source
file (ctsdata.py's `read_ctsdata()`), tokenize and split the WHOLE collected
text into sentences in one shot via segmentation_dspy.py's
`segment_sources()` -- the same LLM-driven tokenization/sentence-splitting
stage pipeline.py's `analyze_sources()` runs before syntax analysis, and
the same way marimo/latin_syntaxer_ctsdata.py segments its own selected
passages -- and write the result to standard output as one serialized
string. No syntax analysis happens here at all: there is no SyntaxAnalysis
call, no TokenAnalysis/VerbalExpression, and nothing for `validate()` to
check -- this stops at "what are the sentences and tokens", one LM call for
the whole file.

Every row `read_ctsdata()` returns is handed to a single `segment_sources()`
call together, in file order -- not segmented one row at a time -- so a
sentence is free to run from the end of one row's text into the start of
the next, exactly like `analyze_sources()`/the ctsdata notebook's own
"Analyze every selected passage, together" behavior. Token ids (`t0`, `t1`,
...) are therefore globally unique across the whole output, the same
`segment_sources()` guarantee `arsgrammatica.serialization`'s own format
relies on -- not scoped to one row the way an earlier version of this
script had it.

Output format: two `#!`-labeled, pipe-delimited blocks. The first,
`#!sentences`, is in EXACTLY the same shape `arsgrammatica.serialization`
writes for its own `#!sentences` block (same label, same
`context_begin|first_token|context_end|last_token` header and row shape --
this script imports those constants directly from `arsgrammatica.serialization`
rather than re-typing them, so the two can never quietly drift apart). The
second, `#!tokens`, lists every token in every sentence; despite sharing
`arsgrammatica.serialization`'s block NAME, its columns are its own,
lighter shape (`context|sentence_index|id|text`), not that module's
10-column tokengraph row -- there is no `tokentype`/`lemma`/relation data
to write, since nothing here ever runs syntax analysis. Because of that
column mismatch, `read_analyses()` still cannot parse this file as a whole,
even though its `#!sentences` half alone is byte-for-byte what that
function expects:

    #!sentences
    context_begin|first_token|context_end|last_token
    urn:cts:compnov:bible.genesis.vulgate:45.1|t0|urn:cts:compnov:bible.genesis.vulgate:45.1|t4

    #!tokens
    context|sentence_index|id|text
    urn:cts:compnov:bible.genesis.vulgate:45.1|0|t0|Non
    urn:cts:compnov:bible.genesis.vulgate:45.1|0|t1|se
    ...

`#!sentences` has one row per sentence: `context_begin`/`first_token` are
that sentence's own first token's citation/id, `context_end`/`last_token`
its own last token's citation/id -- same fields, same meaning, as
`arsgrammatica.serialization.serialize_analyses()`'s own `#!sentences` rows.
`#!tokens` has one row per token: `context` is that token's own
`Token.citation` (named `context` rather than `citation` to match
serialization.py's own column-naming convention for this field),
`sentence_index` is that token's own sentence's 0-based position in the
WHOLE file (not reset per source row, since segmentation runs once across
every row together), `id`/`text` are the token's own `Token.id`/`Token.text`.

As with every other pipe-delimited format in this codebase, no column may
contain a literal `|` or newline -- there is no escaping mechanism. This
script raises ValueError immediately, naming the offending row, rather
than silently producing an unreadable file, if a `#!ctsdata` row's own
citation/text (unlikely, since read_ctsdata() already rejects a blank urn/
text and a `|` in the URN would already have broken its own 5-part split)
or a segmented token's text contains either.

Usage:
    python utilities/tokenize_ctsdata.py path/to/source.cex > out.txt
    python utilities/tokenize_ctsdata.py --delimiter ';' path/to/source.cex

Needs the same `.env` as syntaxer_main.py (API_BASE/MODEL/API_KEY) --
segment_sources() is an LM call like any other stage in this codebase.
`--delimiter` controls the SOURCE `#!ctsdata` file's own column delimiter
(passed straight through to read_ctsdata()); the OUTPUT this script writes
always uses '|', matching every other serialized format here.
"""

import argparse
import sys
from typing import List

from pathlib import Path

# utilities/ isn't the repo root -- add the root to sys.path so both the
# installed-in-place `arsgrammatica` package and the root-level
# `syntaxer_main` module (for its .env-loading + LM-config helpers, reused
# rather than duplicated a third time -- see optimize_gepa.py's own
# identical comment) import the same way they would from a script sitting
# at the repo root.
sys.path.insert(0, str(Path(__file__).parent.parent))
from syntaxer_main import _configure_lm  # noqa: E402

from arsgrammatica import CitedText, read_ctsdata, segment_sources
from arsgrammatica.serialization import SENTENCES_LABEL, SENTENCES_HEADER


TOKENS_LABEL = "#!tokens"
TOKENS_HEADER = "context|sentence_index|id|text"


def _field(value, *, where: str) -> str:
    """Render one column value: same convention as serialization.py's own
    `_field()` -- `None` becomes `''` (used here for a token with no
    citation), any other string is returned verbatim after checking it
    contains none of `|`/`\\n`/`\\r`, none of which this pipe-delimited
    format has any way to escape. Raises ValueError immediately, naming
    `where`, rather than write a row a reader couldn't parse back apart."""
    if value is None:
        return ""
    if "|" in value or "\n" in value or "\r" in value:
        raise ValueError(
            f"{where}: value {value!r} contains a '|' or a newline, which "
            "this pipe-delimited format has no way to escape"
        )
    return value


def tokenize_ctsdata(rows: List[CitedText]) -> str:
    """Segment `rows` (as `read_ctsdata()` returns them -- each already a
    `CitedText`) into sentences with a single `segment_sources()` call over
    all of them together, in file order (see this module's own docstring
    for why they're combined rather than segmented one at a time), and
    return the complete `#!sentences`/`#!tokens` file body described there
    as a single string, including its trailing newline.

    Raises ValueError, naming the offending row, if any field value
    contains '|' or a newline (see `_field()`), or if a sentence somehow
    has no tokens at all (nothing to derive `#!sentences`' own
    first_token/last_token from -- mirrors serialize_analyses()'s own
    guard for the same case); propagates whatever `segment_sources()`
    itself raises (e.g. a malformed LM response) as-is -- there is only
    one LM call for the whole file, so there is no notion of "one bad
    passage" to isolate from the rest.
    """
    sentences = segment_sources(rows)

    sentence_lines: List[str] = [SENTENCES_LABEL, SENTENCES_HEADER]
    token_lines: List[str] = [TOKENS_LABEL, TOKENS_HEADER]

    for s_idx, sentence in enumerate(sentences):
        if not sentence.tokens:
            raise ValueError(f"sentence at index {s_idx} has no tokens -- cannot derive first_token/last_token for an empty sentence")

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

    lines = sentence_lines + [""] + token_lines
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Tokenize and sentence-split the whole collected text of a "
            "#!ctsdata (CEX) source file (no syntax analysis), writing the "
            "result to stdout."
        )
    )
    parser.add_argument("ctsdata_path", help="Path to a #!ctsdata (CEX) source file.")
    parser.add_argument(
        "--delimiter",
        default="|",
        help="Column delimiter used by the SOURCE #!ctsdata file (default '|'). "
             "Does not affect this script's own '|'-delimited output.",
    )
    args = parser.parse_args()

    # Read (and validate) the source file before configuring an LM or
    # spending any calls on it, so a bad path or malformed #!ctsdata file
    # fails fast and cheaply.
    rows = read_ctsdata(args.ctsdata_path, delimiter=args.delimiter)

    _configure_lm()
    sys.stdout.write(tokenize_ctsdata(rows))
