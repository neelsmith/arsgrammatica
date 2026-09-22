"""
Command-line utility: read every passage out of a `#!ctsdata` (CEX) source
file (ctsdata.py's `read_ctsdata()`), tokenize and split it into sentences,
and write the result to standard output, serialized by
`arsgrammatica.segmentation_serialization.serialize_segmentation()` (see
that module's own docstring for the exact `#!sentences`/`#!tokens` file
shape). No syntax analysis happens here at all: there is no SentenceAnalysis
call, no TokenAnalysis/VerbalExpression, and nothing for `validate()` to
check -- this stops at "what are the sentences and tokens".

Unlike an earlier version of this script (still what
`pipeline.analyze_sources()`/the ctsdata notebook's own "Analyze every
selected passage, together" cell do), `read_ctsdata()`'s rows are no longer
handed to segmentation_dspy.py's `segment_sources()` in a single call
spanning the WHOLE file. Instead:

  1. `passage_grouping.group_passages_by_sentence_boundary()` first clusters
     the rows into the SMALLEST possible runs of consecutive rows that each
     begin and end at a sentence boundary, per that function's fast, LM-free
     text-ending heuristic -- no LM call at all for this step (see that
     module's own docstring). A file whose every row already ends its own
     sentence (the common case for e.g. one CTS URN per verse line with no
     enjambment) ends up with one row per group.
  2. `segment_sources()` then runs ONCE PER GROUP -- not once for the whole
     file -- so each individual LM call only ever has to segment however
     many rows one cluster needed to reach its own sentence boundary,
     rather than the whole file's text at once. A single sentence spanning
     several rows still gets segmented as one continuous passage (it's in
     one group together); it just no longer forces every OTHER, unrelated
     sentence in the file into that same call.

Token ids are still unique across the WHOLE output, but no longer by
renumbering everything into one globally sequential `t0, t1, t2, ...`
run: since each group's own `segment_sources()` call restarts its own bare
numbering at `t0` (see `SegmentPassage`'s own docstring -- ids are only
global WITHIN one call), this script instead rewrites every CTS-URN-cited
token's id to a PASSAGE-SCOPED composite id (`arsgrammatica.
assign_passage_scoped_ids()` -- e.g. citation `...:1.1` gives ids `1.1.t0`,
`1.1.t1`, ...) once all groups have been segmented, before writing anything
out. This is deliberately different from (and better than) a corpus-wide
renumbering: a given passage gets the exact same ids every time it's
tokenized, no matter what other passages it happened to be grouped with in
this particular run, which is what lets `analyze_tokendata_to_files.py`
analyzing THIS script's output and `analyze_ctsdata_to_files.py` analyzing
the same corpus directly actually share DSPy's LM response cache for a
passage they both segment the same way (assign_passage_scoped_ids()'s own
docstring has the full rationale). Safe to do purely by position: at this
stage (segmentation only, no syntax analysis yet) no token id is referenced
anywhere else the way `TokenAnalysis`'s `relatedtoken1`/`verbalunitid`
fields reference one another once analysis has run, so rewriting ids here
can never leave a dangling reference.

This trades a little accuracy for smaller, cheaper LM calls: the grouping
step's own heuristic -- "this row's own text ends in sentence-ending
punctuation (. ? !)" -- has no abbreviation handling, so a row ending in a
praenomen or other abbreviation (e.g. "M.", "cos.") is (wrongly) treated as
its own sentence boundary, closing a group one row too early (see
`passage_grouping.py`'s own module docstring for this exact, pre-existing
caveat). When that happens, the following row starts a NEW group instead of
continuing the same `segment_sources()` call the sentence actually belongs
to -- `segment_sources()` itself is still fully accurate for tokenization
and sentence-splitting WITHIN whatever text it's given; only the grouping
step ahead of it can misjudge where one group ends and the next begins.
Any warning `group_passages_by_sentence_boundary()` itself returns (only
ever: the file's last group not ending at a sentence boundary, e.g. because
`rows` is a truncated excerpt) is printed to stderr before the segmentation
is written, same as `group_ctsdata_by_sentence.py`'s own convention.

A large source file can take a while to fully tokenize -- every group is
its own real, possibly slow LM call -- so this also prints a one-line
progress message to STDERR before each `segment_sources()` call: one
summarizing how many groups the (instant, LM-free) clustering step found,
then one per group as its own call starts ("[i/N] Segmenting group of M
passage(s) starting '...'..."), so a long run doesn't look hung. Purely a
heartbeat, not a diagnostic, and like every other diagnostic here it never
touches stdout.

Read the resulting file back with `arsgrammatica.read_segmentation()` --
`marimo/latin_syntaxer_tokenized.py` does exactly that, letting you pick
one sentence out of it and run THAT one sentence through syntax analysis
on demand.

After writing the segmentation to stdout, this prints one line to STDERR
reporting the TOTAL LM cost of every `segment_sources()` call above -- one
per group, not necessarily just one for the whole file anymore -- via
`arsgrammatica.summarize_lm_cost()`/`format_lm_cost()` -- the same helpers
and the same "no calls" / "all cache hits" / "priced + cached mix" /
"every call priced" cases the marimo notebooks' own "See cost" checkbox
and `estimate_corpus_cost.py`'s report already cover (see `lm_cost.py`'s
module docstring). Kept off stdout deliberately, matching
`estimate_corpus_cost.py`'s own stdout/stderr split, so `... > out.txt`
still captures nothing but the serialized segmentation.

Usage:
    python utilities/tokenize_ctsdata.py path/to/source.cex > out.txt
    python utilities/tokenize_ctsdata.py --delimiter ';' path/to/source.cex

Needs the same `.env` as syntaxer_main.py (API_BASE/MODEL/API_KEY) --
segment_sources() is an LM call like any other stage in this codebase.
`--delimiter` controls the SOURCE `#!ctsdata` file's own column delimiter
(passed straight through to read_ctsdata()); the OUTPUT this script writes
always uses '|', matching every other serialized format here. The stderr
cost line above always prints, with no flag to suppress it -- it's a
single short line, not a verbosity knob.
"""

import argparse
import sys
from typing import List, Tuple

from pathlib import Path

# utilities/ isn't the repo root -- add the root to sys.path so both the
# installed-in-place `arsgrammatica` package and the root-level
# `syntaxer_main` module (for its .env-loading + LM-config helpers, reused
# rather than duplicated a third time -- see optimize_gepa.py's own
# identical comment) import the same way they would from a script sitting
# at the repo root.
sys.path.insert(0, str(Path(__file__).parent.parent))
from syntaxer_main import _configure_lm  # noqa: E402

from arsgrammatica import (
    CitedText,
    Sentence,
    assign_passage_scoped_ids,
    format_lm_cost,
    group_passages_by_sentence_boundary,
    read_ctsdata,
    segment_sources,
    serialize_segmentation,
    summarize_lm_cost,
)


def tokenize_ctsdata(rows: List[CitedText]) -> Tuple[str, List[str]]:
    """Cluster `rows` (as `read_ctsdata()` returns them -- each already a
    `CitedText`) into the smallest possible groups that each begin and end
    at a sentence boundary (`group_passages_by_sentence_boundary()`'s
    fast, LM-free heuristic -- no LM call for this step), run ONE
    `segment_sources()` call PER GROUP (rather than one call across the
    whole file), and combine every group's own resulting sentences, in
    group order, into a single `serialize_segmentation()` text -- with
    every CTS-URN-cited token's id rewritten to a passage-scoped composite
    id (`arsgrammatica.assign_passage_scoped_ids()`) so ids stay unique
    across the WHOLE combined output no matter how the rows were grouped
    (see this module's own docstring for the full rationale and its one
    accuracy tradeoff).

    Returns `(text, warnings)`: `warnings` is whatever
    `group_passages_by_sentence_boundary()` itself returned (only ever: the
    final group not ending at a sentence boundary, e.g. because `rows`
    itself is a truncated excerpt) -- surfaced to the caller rather than
    printed here, same as `write_analyses()`'s own warnings-return
    convention elsewhere in this codebase.

    Propagates whatever `segment_sources()`/`serialize_segmentation()`
    themselves raise (e.g. a malformed LM response for one group, or a
    field value containing '|' or a newline) as-is; a bad LM response for
    one group aborts the whole run rather than skipping just that group,
    since a partial `#!sentences`/`#!tokens` file would silently gap the
    id sequence `read_segmentation()` requires to be contiguous.

    Prints a one-line progress message to stderr before each group's own
    `segment_sources()` call -- see this module's own docstring for why.
    Never touches stdout.
    """
    groups, warnings = group_passages_by_sentence_boundary(rows)
    print(
        f"Grouped {len(rows)} passage(s) into {len(groups)} "
        "sentence-boundary group(s) (no LM call for this step).",
        file=sys.stderr,
    )

    all_sentences: List[Sentence] = []
    remaining = iter(rows)
    for group_num, group_ids in enumerate(groups, start=1):
        group_rows = [next(remaining) for _ in group_ids]
        print(
            f"[{group_num}/{len(groups)}] Segmenting group of "
            f"{len(group_rows)} passage(s) starting {group_rows[0].citation!r}...",
            file=sys.stderr,
        )
        all_sentences.extend(segment_sources(group_rows))

    return serialize_segmentation(assign_passage_scoped_ids(all_sentences)), warnings


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Tokenize and sentence-split a #!ctsdata (CEX) source file "
            "(no syntax analysis), clustering its rows into the smallest "
            "sentence-boundary-respecting groups first (no LM call) and "
            "running one segmentation call per group, writing the "
            "combined result to stdout."
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

    lm = _configure_lm()
    text, warnings = tokenize_ctsdata(rows)

    # Grouping warnings (only ever: the file's last group not ending at a
    # sentence boundary) go to stderr before the segmentation itself is
    # written -- same convention group_ctsdata_by_sentence.py's own
    # warnings-before-output ordering uses.
    for w in warnings:
        print(f"Warning: {w}", file=sys.stderr)

    sys.stdout.write(text)

    # stdout carries nothing but the serialized segmentation above -- same
    # stdout/stderr split as estimate_corpus_cost.py's own diagnostics and
    # analysis_to_dot.py's "Wrote ..." lines -- so the cost line (and every
    # case arsgrammatica.format_lm_cost() itself covers: no calls, an
    # all-cache-hit history, a priced/cached mix) goes to stderr instead.
    # This totals every segment_sources() call tokenize_ctsdata() made --
    # one per group, not necessarily just one for the whole file anymore.
    cost_summary = summarize_lm_cost(lm.history)
    print(f"LM cost: {format_lm_cost(cost_summary)}", file=sys.stderr)
