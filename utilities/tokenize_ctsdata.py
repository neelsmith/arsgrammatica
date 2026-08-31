"""
Command-line utility: read every passage out of a `#!ctsdata` (CEX) source
file (ctsdata.py's `read_ctsdata()`), tokenize and split each one into
sentences via segmentation_dspy.py's `segment_sources()` -- the same LLM-
driven tokenization/sentence-splitting stage pipeline.py's `analyze_sources()`
runs before syntax analysis -- and write the result to standard output as
one serialized string. No syntax analysis happens here at all: there is no
SyntaxAnalysis call, no TokenAnalysis/VerbalExpression, and nothing for
`validate()` to check -- this stops at "what are the sentences and tokens",
one LM call per passage.

Each passage is segmented ON ITS OWN, not combined with its neighbors into
one continuous `segment_sources()` call the way the ctsdata marimo notebook
combines several *selected* passages together (see
marimo/latin_syntaxer_ctsdata.py) -- a `#!ctsdata` file's rows are an
arbitrary catalog of passages (e.g. gathered from unrelated places in a
text, or from different texts entirely), not necessarily one continuous
stretch of reading, so a sentence is never allowed to run from the end of
one row's text into the start of the next. One consequence: token ids
(`t0`, `t1`, ...) restart at `t0` for every passage, since
`segment_sources()` numbers ids sequentially within whatever `sources` it's
given (see its own docstring) and each call here is given exactly one
passage. Ids are therefore only unique WITHIN a passage (i.e. within one
`context` value below), not across the whole file -- unlike
arsgrammatica.serialization's format, which assumes globally-unique ids
because it serializes one continuous, jointly-segmented passage.

Output format: this is a NEW, lightweight format, deliberately not
arsgrammatica.serialization's `#!sentences`/`#!verbal_units`/`#!tokens`
blocks -- that format is built around TokenAnalysis/VerbalExpression (the
*syntax analysis* stage's output), which nothing here ever produces, and
`read_analyses()` cannot parse this file. Two pipe-delimited blocks, each
introduced by a `#!`-prefixed label line and a fixed header line, mirroring
that module's own style:

    #!passages
    citation|text
    urn:cts:compnov:bible.genesis.vulgate:45.1|Non se poterat ultra tenere.

    #!sentences
    context|sentence_index|id|text
    urn:cts:compnov:bible.genesis.vulgate:45.1|0|t0|Non
    urn:cts:compnov:bible.genesis.vulgate:45.1|0|t1|se
    urn:cts:compnov:bible.genesis.vulgate:45.1|0|t2|poterat
    ...

`#!passages` is simply every row `read_ctsdata()` returned (each a
`CitedText` -- `citation` is that row's own whole urn, `text` its surface
text verbatim), in file order -- a record of exactly what was segmented
and with what citation, kept alongside the tokens themselves rather than
requiring a reader to go back to the original `#!ctsdata` file to know it.
`#!sentences` has one row per token: `context` is that token's own
`Token.citation` (always the owning passage's `citation` here, since every
token in a passage's sentences carries that same citation -- named
`context` rather than `citation` to match serialization.py's own column-
naming convention for this field), `sentence_index` is that sentence's
0-based position within its OWN passage (not across the whole file --
resets to 0 for every passage, same reasoning as the id reset above),
`id`/`text` are the token's own `Token.id`/`Token.text`.

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


PASSAGES_LABEL = "#!passages"
PASSAGES_HEADER = "citation|text"
SENTENCES_LABEL = "#!sentences"
SENTENCES_HEADER = "context|sentence_index|id|text"


def _field(value: str, *, where: str) -> str:
    """Validate one column value for this format's pipe-delimited rows --
    same convention as serialization.py's own `_field()`: a literal
    newline or '|' can't be represented (no escaping mechanism), so raise
    ValueError immediately, naming `where`, rather than write a row a
    reader couldn't parse back apart."""
    if "\n" in value:
        raise ValueError(f"{where}: value {value!r} contains a newline, which this pipe-delimited format cannot represent")
    if "|" in value:
        raise ValueError(f"{where}: value {value!r} contains '|', this format's own column delimiter, which it cannot represent")
    return value


def tokenize_ctsdata(rows: List[CitedText]) -> str:
    """Segment every row in `rows` (as `read_ctsdata()` returns them --
    each already a `CitedText`) into sentences, one `segment_sources()`
    call per row (see this module's own docstring for why passages are
    never combined), and return the complete `#!passages`/`#!sentences`
    file body described there as a single string, including its trailing
    newline.

    Raises ValueError, naming the offending row, if any field value
    contains '|' or a newline (see `_field()`); propagates whatever
    `segment_sources()` itself raises (e.g. a malformed LM response) for a
    given passage as-is, taking down the whole run rather than silently
    skipping that passage -- this is a small enough tool that "one bad
    passage aborts the batch, rerun once it's fixed" is preferable to
    guessing which passages are safe to keep.
    """
    lines: List[str] = [PASSAGES_LABEL, PASSAGES_HEADER]
    for row in rows:
        where = f"#!passages row for citation {row.citation!r}"
        lines.append(
            "|".join(
                [
                    _field(row.citation, where=where),
                    _field(row.text, where=where),
                ]
            )
        )

    lines.append("")
    lines.append(SENTENCES_LABEL)
    lines.append(SENTENCES_HEADER)
    for row in rows:
        sentences = segment_sources([row])
        for s_idx, sentence in enumerate(sentences):
            for tok in sentence.tokens:
                where = f"#!sentences row for citation {row.citation!r} sentence {s_idx} token {tok.id!r}"
                lines.append(
                    "|".join(
                        [
                            _field(row.citation, where=where),
                            str(s_idx),
                            _field(tok.id, where=where),
                            _field(tok.text, where=where),
                        ]
                    )
                )

    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Tokenize and sentence-split every passage in a #!ctsdata (CEX) "
            "source file (no syntax analysis), writing the result to stdout."
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
