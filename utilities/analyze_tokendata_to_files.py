"""
Command-line utility: read one or more files written by
`utilities/tokenize_ctsdata.py` (`arsgrammatica.read_segmentation()`'s own
`#!sentences`/`#!tokens` format -- see `segmentation_serialization.py`'s
module docstring), run EACH sentence they contain through full syntax
analysis, and write each sentence's own analysis to its own file in an
output directory, using `serialization.py`'s `write_analyses()` format --
the same `#!sentences`/`#!verbal_units`/`#!tokens`[/optional `#!lm`] format
`read_analyses()`, `analysis_to_dot.py`, and `analyses_to_dot_pngs.py`
already read.

An input file may ALSO carry other '#!'-labeled blocks besides
`#!sentences`/`#!tokens` -- an `#!lm` block, say, or anything else some
other producer might have added -- and this script tolerates them rather
than failing to read the file at all: see `_strip_unrecognized_blocks()`
below. `read_segmentation()` itself is left exactly as strict as it always
was for the two blocks it actually needs (it's still what does the real
parsing here, and other callers, e.g.
`marimo/latin_syntaxer_tokenized.py`, may want to keep relying on that
strictness); this script just removes whatever it doesn't need from its
own COPY of the file's text before handing it to `read_segmentation()`.

Parallel to `utilities/analyze_ctsdata_to_files.py`, but one stage later:
that script starts from a raw `#!ctsdata` (CEX) source file and runs BOTH
stages -- segmentation, then per-sentence syntax analysis -- via
`analyze_sources()`. This script instead starts from a file that has
ALREADY been segmented (`tokenize_ctsdata.py`'s own output), so there is no
segmentation call here at all -- just one `SentenceAnalysis` call per
sentence, via `token_budget.analyze_with_retry()` (the same
retry-on-truncation behavior every other analysis entry point in this
codebase gets), the same way `marimo/latin_syntaxer_tokenized.py`'s own
*Analyze* button runs a single selected sentence on demand -- generalized
here to every sentence in one or more files, unattended.

Unlike `analyze_ctsdata_to_files.py` (always exactly one source file), this
accepts one or more tokenized-data files, matching
`analyses_to_dot_pngs.py`'s own multi-file convention: a file that still
can't be read back as `read_segmentation()`'s own format -- even after any
block this script doesn't need has been stripped out of it -- is skipped
(a message on stderr), rather than aborting the whole run -- every other
file's sentences still get analyzed and written. The script exits non-zero
if any file was skipped, or if nothing was written at all.

Usage:
    python utilities/analyze_tokendata_to_files.py tokenized.txt --output-dir analyses/
    python utilities/analyze_tokendata_to_files.py a.txt b.txt --output-dir analyses/

Needs the same `.env` as `syntaxer_main.py` (`API_BASE`/`MODEL`/`API_KEY`) --
every sentence's own `SentenceAnalysis` is a real LM call.

Each output file is named `<input_file_stem>_<sentence_number>_<citation>.cex`
(alphanumeric-sanitized), the same naming convention
`analyze_ctsdata_to_files.py`'s and `analyses_to_dot_pngs.py`'s own
`sentence_filename_stem()` helpers use -- prefixed with the source file's
own stem so sentences from different input files never collide in the same
output directory. Sentence numbering restarts at 1 within each input file
(matching that file's own token ids, which are only unique within one
`tokenize_ctsdata.py` run -- see `notes/tokenizing.md`), not across the
whole invocation. The output directory is created if it doesn't already
exist.

Each file also records a `#!lm` block (the configured model, plus that
sentence's own reasoning), matching `syntaxer_main.py`'s and
`analyze_ctsdata_to_files.py`'s own convention -- see `serialization.py`'s
module docstring for the `#!lm` block's exact shape. Any validation problem
`validate()` finds for a sentence is printed directly (the same way
`pipeline.analyze_sources()` and `latin_syntaxer_tokenized.py`'s own
Analysis cell print it) rather than duplicated as a separate warning; any
warning `write_analyses()` itself returns (e.g. a boundary-token mismatch)
is printed per file, to stderr, alongside a "Wrote ..." line per file on
stdout -- same stdout/stderr split `analyze_ctsdata_to_files.py` and
`analyses_to_dot_pngs.py` use.

After every file is written, one more line goes to stderr reporting the
TOTAL LM cost of the whole run -- every `SentenceAnalysis` call made across
every sentence in every input file (there is no segmentation call to add
in, unlike `analyze_ctsdata_to_files.py`) -- via
`arsgrammatica.summarize_lm_cost()`/`format_lm_cost()`, the same helpers
`utilities/tokenize_ctsdata.py`, `utilities/analyze_ctsdata_to_files.py`,
and every marimo notebook's own "See cost" display already use, so the
wording (no calls, an all-cache-hit history, a priced/cached mix, every
call priced) is consistent with the rest of the codebase. Always prints,
with no flag to suppress it.

A run spanning many files/sentences can take a while -- every sentence is
its own real, possibly slow LM call -- so this also prints a one-line
progress message to STDERR before each one starts: one per input file
("[i/N] Analyzing 'file': M sentence(s)...") as that file's own sentences
begin, and one per sentence within it ("  [j/M] Analyzing sentence
starting at '...'..."), so a long run doesn't look hung. Purely a
heartbeat, not a diagnostic -- it carries no information `written`'s own
return value doesn't already have -- and, like every other diagnostic
here, never touches stdout.
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

# utilities/ isn't the repo root -- add the root so this imports the same
# way it would from a script sitting at the repo root, same as
# utilities/tokenize_ctsdata.py's and analyze_ctsdata_to_files.py's own
# identical comment.
sys.path.insert(0, str(Path(__file__).parent.parent))
from syntaxer_main import _configure_lm  # noqa: E402

from arsgrammatica import (
    Sentence,
    analyze_with_retry,
    format_lm_cost,
    read_segmentation,
    summarize_lm_cost,
    validate,
    write_analyses,
)
# SENTENCES_LABEL/TOKENS_LABEL aren't re-exported at package level (only
# the functions built on them are) -- imported directly from their own
# submodule, same as segmentation_serialization.py's own "import the
# constant rather than re-type it" convention, so this script's notion of
# which two blocks to keep can never quietly drift from
# read_segmentation()'s own.
from arsgrammatica.segmentation_serialization import SENTENCES_LABEL, TOKENS_LABEL


def sentence_filename_stem(file_stem: str, index: int, citation: Optional[str]) -> str:
    """"<file_stem>_<n>_<citation>", alphanumeric-sanitized -- the exact
    same convention `analyze_ctsdata_to_files.py`'s and
    `analyses_to_dot_pngs.py`'s own helpers of the same name use
    (duplicated here rather than imported, since those are scripts, not
    library import targets)."""
    raw = f"{file_stem}_{index + 1}_{citation or ''}"
    sanitized = "".join(c if c.isalnum() else "_" for c in raw).strip("_")
    return sanitized or f"{file_stem}_sentence_{index + 1}"


def _strip_unrecognized_blocks(text: str) -> str:
    """Return `text` with every '#!'-labeled block whose label ISN'T
    `SENTENCES_LABEL`/`TOKENS_LABEL` removed entirely -- that block's own
    label line and every line after it up to (not including) the next
    '#!'-labeled line, or the end of the file.

    Every pipe-delimited format in this codebase (see
    `segmentation_serialization.py`'s and `serialization.py`'s own module
    docstrings) is built the same way: a line starting a block belongs to
    it, and so does every line after it until the NEXT such line -- so
    recognizing a block's full extent needs nothing more than scanning for
    the next '#!'-prefixed line, without knowing anything about that
    block's own header/row shape (e.g. `#!lm` has no header line at all;
    an unrecognized block might not either, and this doesn't need to know
    either way). A blank line is dropped either way, matching
    `read_segmentation()`'s own indifference to them.

    This only ever REMOVES content `read_segmentation()` wouldn't have
    understood anyway -- it can't turn a malformed `#!sentences`/`#!tokens`
    block into a valid one, and a file with neither block at all still
    reads back as `read_segmentation()`'s own "missing required block(s)"
    error, exactly as before.
    """
    kept_lines: List[str] = []
    keep_current = False
    for line in text.splitlines():
        if line.startswith("#!"):
            keep_current = line in (SENTENCES_LABEL, TOKENS_LABEL)
        if keep_current:
            kept_lines.append(line)
    return "\n".join(kept_lines) + ("\n" if kept_lines else "")


def _read_tokendata_file(path: str) -> List[Sentence]:
    """Read `path` as a tokenized-data file, tolerating any '#!'-labeled
    block besides `#!sentences`/`#!tokens` it might also carry (see
    `_strip_unrecognized_blocks()`) -- `read_segmentation()` itself is left
    exactly as strict as it always was for the two blocks it actually
    needs; this only ever hands it a trimmed COPY of `path`'s own text.

    Opens `path` directly first, so a missing file still raises the same
    `FileNotFoundError` (an `OSError`) a bare `read_segmentation(path)`
    call would, before anything is written anywhere. The filtered text
    then goes to a throwaway temporary file -- `read_segmentation()` only
    ever reads from a path, not a string -- which is always removed again,
    whether this returns normally or `read_segmentation()` raises on what's
    left after filtering (e.g. a still-malformed `#!sentences`/`#!tokens`
    block, or neither block present at all).
    """
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    filtered = _strip_unrecognized_blocks(text)

    fd, tmp_path = tempfile.mkstemp(suffix=".txt")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            tmp_file.write(filtered)
        return read_segmentation(tmp_path)
    finally:
        os.remove(tmp_path)


def analyze_tokendata_to_files(
    sentences: List[Sentence],
    output_dir: str,
    file_stem: str,
    model: Optional[str] = None,
) -> List[Tuple[Path, List[str]]]:
    """Run each of `sentences` (already segmented -- e.g.
    `read_segmentation()`'s own output, one input file's worth) through
    full syntax analysis, one sentence at a time, and write each result to
    its own file under `output_dir` -- created if it doesn't already exist
    -- named via `sentence_filename_stem()`.

    Each sentence's own `SentenceAnalysis` call goes through
    `token_budget.analyze_with_retry()`, the same calibrated-budget,
    retry-on-truncation behavior `pipeline.analyze_sources()` itself uses
    for every sentence (see `token_budget.py`'s module docstring) -- with
    the same naive space-joined token text `pipeline.py`'s own
    `_render_sentence_text()` approximation and
    `latin_syntaxer_tokenized.py`'s own Analysis cell use as the `passage`
    field, since these are already-tokenized sentences with no other
    surface text recorded anywhere.

    `model` is recorded on every file's own `#!lm` block (see
    `serialization.py`'s module docstring), alongside that sentence's own
    `reasoning` -- typically the configured LM's own `.model` (e.g.
    `_configure_lm()`'s return value's `.model`), matching
    `syntaxer_main.py`'s and `analyze_ctsdata_to_files.py`'s own
    convention; omit it (the default) to skip `#!lm` entirely, same as
    `write_analyses()` itself does when `model` isn't given.

    Returns a list of `(path, warnings)` pairs, one per sentence written,
    in the same order as `sentences` -- `warnings` is whatever
    `write_analyses()` itself returned for that one file (empty if nothing
    looks wrong; see `serialize_analyses()`'s docstring for what each
    warning means). Any validation problem `validate()` finds for a
    sentence is printed directly to stderr (this function's own behavior,
    since there is no `analyze_sources()` call here to print it for us)
    before this function writes that sentence's file.

    Also prints a one-line progress message to stderr before each
    sentence's own `SentenceAnalysis` call -- see this module's own
    docstring for why. Never touches stdout.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    written: List[Tuple[Path, List[str]]] = []
    for index, sentence in enumerate(sentences):
        citation = sentence.tokens[0].citation if sentence.tokens else None
        print(
            f"  [{index + 1}/{len(sentences)}] Analyzing sentence starting "
            f"at {citation or '(no citation)'!r}...",
            file=sys.stderr,
        )

        # Same "join every token's text with a space" approximation
        # pipeline.py's own _render_sentence_text() and
        # latin_syntaxer_tokenized.py's own Analysis cell use -- not a
        # faithful re-rendering (punctuation/enclitics get their own
        # spaces too), but SentenceAnalysis only uses `passage` for
        # readability alongside the authoritative `tokens` list.
        passage_text = " ".join(tok.text for tok in sentence.tokens)
        result = analyze_with_retry(passage=passage_text, tokens=sentence.tokens)

        problems = validate(sentence.tokens, result)
        if problems:
            first_id = sentence.tokens[0].id if sentence.tokens else "?"
            print(f"Validation warnings (sentence starting at {first_id}):", file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)

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
            "Run every sentence in one or more tokenized-data files "
            "(utilities/tokenize_ctsdata.py's own output) through full "
            "syntax analysis, and write one analysis file per sentence to "
            "an output directory."
        )
    )
    parser.add_argument(
        "tokendata_files",
        nargs="+",
        help="Path(s) to file(s) written by utilities/tokenize_ctsdata.py "
             "(read via arsgrammatica.read_segmentation()) -- any other "
             "'#!'-labeled block the file also carries (e.g. '#!lm') is "
             "ignored.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to write one analysis file per sentence to -- "
             "created if it doesn't already exist.",
    )
    args = parser.parse_args()

    # Read (and validate) every input file before configuring an LM or
    # spending any calls on it, matching analyze_ctsdata_to_files.py's own
    # convention -- a bad path or malformed tokenized-data file is caught
    # fast and cheaply, before this script has spent anything analyzing
    # any OTHER file's sentences. A bad file is skipped (not fatal), same
    # as analyses_to_dot_pngs.py's own per-file error handling, so one
    # malformed file doesn't stop every other file's sentences from being
    # analyzed and written. _read_tokendata_file() (not a bare
    # read_segmentation() call) so a file carrying some OTHER '#!'-labeled
    # block alongside #!sentences/#!tokens reads back fine instead of
    # being skipped over that alone.
    file_sentences: List[Tuple[str, List[Sentence]]] = []
    had_failure = False
    for tokendata_file in args.tokendata_files:
        try:
            sentences = _read_tokendata_file(tokendata_file)
        except (ValueError, OSError) as e:
            print(
                f"Skipping {tokendata_file!r}: could not read it as tokenized "
                f"data: {e}",
                file=sys.stderr,
            )
            had_failure = True
            continue
        file_sentences.append((Path(tokendata_file).stem, sentences))

    if not file_sentences:
        print("No input file could be read -- nothing to analyze.", file=sys.stderr)
        sys.exit(1)

    lm = _configure_lm()

    written: List[Tuple[Path, List[str]]] = []
    for file_num, (file_stem, sentences) in enumerate(file_sentences, start=1):
        print(
            f"[{file_num}/{len(file_sentences)}] Analyzing {file_stem!r}: "
            f"{len(sentences)} sentence(s)...",
            file=sys.stderr,
        )
        written.extend(
            analyze_tokendata_to_files(sentences, args.output_dir, file_stem, model=lm.model)
        )

    for out_path, warnings in written:
        for w in warnings:
            print(f"Warning ({out_path}): {w}", file=sys.stderr)
        print(f"Wrote {out_path}")

    # stdout carries nothing but the per-file "Wrote ..." lines above --
    # same stdout/stderr split analyze_ctsdata_to_files.py's and
    # analyses_to_dot_pngs.py's own diagnostics use -- so the total-cost
    # line (via the same arsgrammatica.lm_cost helpers used everywhere
    # else in this codebase) goes to stderr instead, covering every case
    # format_lm_cost() itself handles: no calls, an all-cache-hit history,
    # a priced/cached mix, or every call priced. This totals every
    # SentenceAnalysis call made across every sentence in every input
    # file -- there is no segmentation call to add in here, unlike
    # analyze_ctsdata_to_files.py, since the input was already segmented
    # by a prior tokenize_ctsdata.py run.
    cost_summary = summarize_lm_cost(lm.history)
    print(f"LM cost: {format_lm_cost(cost_summary)}", file=sys.stderr)

    if not written:
        print("No analyses were written -- every input file was empty.", file=sys.stderr)
        sys.exit(1)
    if had_failure:
        sys.exit(1)
