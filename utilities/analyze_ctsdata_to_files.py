"""
Command-line utility: read a `#!ctsdata` (CEX) corpus from an input file
(`ctsdata.py`'s `read_ctsdata()`), segment its whole collected text into
citation-aware sentences and run each one through full syntax analysis --
exactly what `analyze_sources()` already does in one call -- then write
EACH sentence's own analysis to its own file in an output directory, using
`serialization.py`'s `write_analyses()` format (the same
`#!sentences`/`#!verbal_units`/`#!tokens`[/optional `#!LM`] format
`read_analyses()`, `analysis_to_dot.py`, and `analyses_to_dot_pngs.py`
already read).

Unlike `utilities/tokenize_ctsdata.py` (segmentation only, no syntax
analysis at all), this script runs the FULL pipeline for the whole corpus:
one `segment_sources()` call across every passage together (so a sentence
is free to run from the end of one passage's text into the start of the
next, same as `analyze_sources()` always does), then one `SentenceAnalysis`
call per sentence (via `token_budget.analyze_with_retry()`, the same
retry-on-truncation behavior every other analysis entry point in this
codebase gets). It's essentially `syntaxer_main.py` generalized from one
hand-typed passage to a whole CEX corpus file, writing one output file per
sentence instead of one combined stream to stdout.

Usage:
    python utilities/analyze_ctsdata_to_files.py corpus.cex --output-dir analyses/
    python utilities/analyze_ctsdata_to_files.py corpus.cex --output-dir analyses/ --delimiter ';'

Needs the same `.env` as `syntaxer_main.py` (`API_BASE`/`MODEL`/`API_KEY`) --
`analyze_sources()` makes real LM calls, for segmentation and for every
sentence's own `SentenceAnalysis`.

Each output file is named `<input_file_stem>_<sentence_number>_<citation>.cex`
(alphanumeric-sanitized), the same naming convention
`analyses_to_dot_pngs.py`'s own `sentence_filename_stem()` uses for its
PNGs -- prefixed with the source file's own stem so analyzing a second
corpus into the same output directory doesn't collide with the first. The
output directory is created if it doesn't already exist.

Each file also records a `#!LM` block (the configured model, plus that
sentence's own reasoning), matching `syntaxer_main.py`'s own convention --
see `serialization.py`'s module docstring for the `#!LM` block's exact
shape. Any validation problem `analyze_sources()` finds for a sentence is
printed by `analyze_sources()` itself (its own existing behavior, unchanged
here) rather than duplicated by this script; any warning
`write_analyses()` itself returns (e.g. a boundary-token mismatch) is
printed per file, to stderr, alongside a "Wrote ..." line per file on
stdout -- same stdout/stderr split `analyses_to_dot_pngs.py` uses. The
script exits non-zero if nothing was written at all (an empty corpus).
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# utilities/ isn't the repo root -- add the root so this imports the same
# way it would from a script sitting at the repo root, same as
# utilities/tokenize_ctsdata.py's own identical comment.
sys.path.insert(0, str(Path(__file__).parent.parent))
from syntaxer_main import _configure_lm  # noqa: E402

from arsgrammatica import CitedText, analyze_sources, read_ctsdata, write_analyses


def sentence_filename_stem(file_stem: str, index: int, citation: Optional[str]) -> str:
    """"<file_stem>_<n>_<citation>", alphanumeric-sanitized -- the exact
    same convention analyses_to_dot_pngs.py's own helper of the same name
    uses (duplicated here rather than imported, since that module is a
    script, not a library import target)."""
    raw = f"{file_stem}_{index + 1}_{citation or ''}"
    sanitized = "".join(c if c.isalnum() else "_" for c in raw).strip("_")
    return sanitized or f"{file_stem}_sentence_{index + 1}"


def analyze_ctsdata_to_files(
    cited_texts: List[CitedText],
    output_dir: str,
    file_stem: str,
    model: Optional[str] = None,
) -> List[Tuple[Path, List[str]]]:
    """Run `cited_texts` through `analyze_sources()` (segmentation, then
    full syntax analysis, one sentence at a time) and write each resulting
    sentence's own analysis to its own file under `output_dir` -- created
    if it doesn't already exist -- named via `sentence_filename_stem()`.

    `model` is recorded on every file's own `#!LM` block (see
    `serialization.py`'s module docstring), alongside that sentence's own
    `reasoning` -- typically the configured LM's own `.model` (e.g.
    `_configure_lm()`'s return value's `.model`), matching
    `syntaxer_main.py`'s own convention; omit it (the default) to skip
    `#!LM` entirely, same as `write_analyses()` itself does when `model`
    isn't given.

    Returns a list of `(path, warnings)` pairs, one per sentence written,
    in the same order `analyze_sources()` returned them -- `warnings` is
    whatever `write_analyses()` itself returned for that one file (empty
    if nothing looks wrong; see `serialize_analyses()`'s docstring for what
    each warning means). Any validation problem `analyze_sources()` itself
    finds for a sentence is printed by `analyze_sources()` directly (its
    own existing, unchanged behavior) before this function ever gets to
    write anything.
    """
    sentences, results = analyze_sources(cited_texts)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    written: List[Tuple[Path, List[str]]] = []
    for index, (sentence, result) in enumerate(zip(sentences, results)):
        citation = sentence.tokens[0].citation if sentence.tokens else None
        stem = sentence_filename_stem(file_stem, index, citation)
        out_path = out_dir / f"{stem}.cex"

        warnings = write_analyses(
            [sentence],
            result.verbalunits,
            result.tokengraph,
            str(out_path),
            model=model,
            reasoning=[result.reasoning],
        )
        written.append((out_path, warnings))

    return written


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Segment a #!ctsdata (CEX) corpus into sentences, run full "
            "syntax analysis on each, and write one analysis file per "
            "sentence to an output directory."
        )
    )
    parser.add_argument("ctsdata_path", help="Path to a #!ctsdata (CEX) source file.")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to write one analysis file per sentence to -- "
             "created if it doesn't already exist.",
    )
    parser.add_argument(
        "--delimiter",
        default="|",
        help="Column delimiter used by the SOURCE #!ctsdata file (default '|'). "
             "Does not affect the '|'-delimited format each output analysis "
             "file uses.",
    )
    args = parser.parse_args()

    # Read (and validate) the source file before configuring an LM or
    # spending any calls on it, matching utilities/tokenize_ctsdata.py's
    # own convention -- a bad path or malformed #!ctsdata file fails fast
    # and cheaply.
    cited_texts = read_ctsdata(args.ctsdata_path, delimiter=args.delimiter)

    lm = _configure_lm()
    written = analyze_ctsdata_to_files(
        cited_texts,
        args.output_dir,
        Path(args.ctsdata_path).stem,
        model=lm.model,
    )

    for out_path, warnings in written:
        for w in warnings:
            print(f"Warning ({out_path}): {w}", file=sys.stderr)
        print(f"Wrote {out_path}")

    if not written:
        print("No analyses were written -- the corpus had no sentences.", file=sys.stderr)
        sys.exit(1)
