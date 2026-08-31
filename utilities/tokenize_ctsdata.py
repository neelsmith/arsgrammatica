"""
Command-line utility: read every passage out of a `#!ctsdata` (CEX) source
file (ctsdata.py's `read_ctsdata()`), tokenize and split the WHOLE collected
text into sentences in one shot via segmentation_dspy.py's
`segment_sources()` -- the same LLM-driven tokenization/sentence-splitting
stage pipeline.py's `analyze_sources()` runs before syntax analysis, and
the same way marimo/latin_syntaxer_ctsdata.py segments its own selected
passages -- and write the result to standard output, serialized by
`arsgrammatica.segmentation_serialization.serialize_segmentation()` (see
that module's own docstring for the exact `#!sentences`/`#!tokens` file
shape). No syntax analysis happens here at all: there is no SyntaxAnalysis
call, no TokenAnalysis/VerbalExpression, and nothing for `validate()` to
check -- this stops at "what are the sentences and tokens", one LM call for
the whole file.

Every row `read_ctsdata()` returns is handed to a single `segment_sources()`
call together, in file order -- not segmented one row at a time -- so a
sentence is free to run from the end of one row's text into the start of
the next, exactly like `analyze_sources()`/the ctsdata notebook's own
"Analyze every selected passage, together" behavior. Token ids (`t0`, `t1`,
...) are therefore globally unique across the whole output.

Read the resulting file back with `arsgrammatica.read_segmentation()` --
`marimo/latin_syntaxer_tokenized.py` does exactly that, letting you pick
one sentence out of it and run THAT one sentence through syntax analysis
on demand.

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

from arsgrammatica import CitedText, read_ctsdata, segment_sources, serialize_segmentation


def tokenize_ctsdata(rows: List[CitedText]) -> str:
    """Segment `rows` (as `read_ctsdata()` returns them -- each already a
    `CitedText`) into sentences with a single `segment_sources()` call over
    all of them together, in file order, and return
    `serialize_segmentation()`'s own `#!sentences`/`#!tokens` text for the
    result (see `arsgrammatica.segmentation_serialization`'s module
    docstring for the exact file shape).

    Propagates whatever `segment_sources()`/`serialize_segmentation()`
    themselves raise (e.g. a malformed LM response, or a field value
    containing '|' or a newline) as-is -- there is only one LM call for
    the whole file, so there is no notion of "one bad passage" to isolate
    from the rest.
    """
    sentences = segment_sources(rows)
    return serialize_segmentation(sentences)


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
