"""
Command-line utility: run the second half of `analyze_w_diagrams.py`'s own
pipeline, plus diagrams, starting from one or more already-tokenized files
(`utilities/tokenize_ctsdata.py`'s own output) instead of a raw `#!ctsdata`
(CEX) source file -- the equivalent of running these two scripts by hand,
in order:

    python utilities/analyze_tokendata_to_files.py a.txt b.txt --output-dir out/
    python utilities/analyses_to_dot_pngs.py out/*.cex --output-dir out/dots/

...but as one script, one argparse invocation, one `.env` read, and one
combined LM-cost total (diagramming makes no LM calls at all).

Parallel to `analyze_w_diagrams.py` in every way except where it starts:
that script's own three stages are tokenize -> analyze -> diagram, starting
from a raw corpus file; this one is just the last two, starting from
already-tokenized files -- exactly the same relationship
`analyze_tokendata_to_files.py` itself has to `analyze_ctsdata_to_files.py`.
Use this one instead of `analyze_w_diagrams.py` to split tokenizing and
analyzing into separate runs (e.g. tokenize once, analyze -- and diagram --
several times, or review a tokenized file by hand before spending anything
on real analysis), or to analyze/diagram several already-tokenized files at
once (unlike `analyze_w_diagrams.py`, always exactly one source file, this
accepts one or more, matching `analyze_tokendata_to_files.py`'s own
multi-file convention).

Each stage's own function is reused directly rather than shelled out to or
reimplemented:

  1. `analyze_tokendata_to_files.analyze_tokendata_to_files()` -- runs
     every sentence one already-tokenized file contains through full
     syntax analysis, one `SentenceAnalysis` call per sentence
     (`token_budget.analyze_with_retry()`), writing one analysis file per
     sentence directly under `output_dir` (not a subdirectory). Run once
     per input file, same as `analyze_tokendata_to_files.py`'s own
     `__main__` loop.
  2. `analyze_w_diagrams._write_diagrams()` -- imported from that sibling
     script rather than duplicated a second time (it's already reused
     there instead of `analyses_to_dot_pngs.py`'s own `__main__`-only
     logic -- see that module's own docstring for why duplicating a
     helper this size didn't seem worth it twice over). Renders every one
     of stage 1's own analysis files (across every input file) as a PNG
     via `tokengraph_to_dot()` + `graphviz`, written to `<output_dir>/dots/`.

`analyze_tokendata_to_files.py`'s own `analyze_tokendata_to_files()` and
`_read_tokendata_file()` (the '#!'-block-tolerant reader -- see that
module's own docstring), and `analyze_w_diagrams.py`'s own
`_write_diagrams()`, are imported by module name rather than duplicated --
`utilities/` is already the first entry on `sys.path` when a script inside
it runs the normal way, the same way any script's own directory is, so
importing a sibling script here works exactly like importing any other
module.

Usage:
    python utilities/analyze_tokendata_w_diagrams.py tokenized.txt --output-dir out/
    python utilities/analyze_tokendata_w_diagrams.py a.txt b.txt --output-dir out/
    python utilities/analyze_tokendata_w_diagrams.py tokenized.txt --output-dir out/ --orientation LR
    python utilities/analyze_tokendata_w_diagrams.py tokenized.txt --output-dir out/ --no-color --no-rank

Needs the same `.env` as `syntaxer_main.py` (`API_BASE`/`MODEL`/`API_KEY`) --
stage 1's `SentenceAnalysis` calls are real LM calls (stage 2 makes none at
all). Also needs the `graphviz` PyPI package AND a separate Graphviz
installation (the `dot` command-line tool) for stage 2 -- see
`notes/graphviz_install.md` and `notes/install.md`. That's checked FIRST,
before any input file is even read, let alone any LM configured or called
-- there's no reason to pay for a whole stage of real LM work only to find
out at the very end that stage 2 can't run at all.

`--output-dir` ends up holding one `<input_file_stem>_<n>_<citation>.cex`
analysis file per sentence, across every input file (stage 1), and a
`dots/` subdirectory of one `<analysis_file_stem>_1_<citation>.png` per
sentence (stage 2) -- the doubled-up "_1_<citation>" in that last name
isn't new here, it's exactly what `analyses_to_dot_pngs.py` already does
(and what `analyze_w_diagrams.py`'s own stage 3 already does) when fed a
one-sentence-per-file input, which is all stage 1 ever produces. The
directory is created if it doesn't already exist.

Like `analyze_tokendata_to_files.py`'s own `__main__`, a tokenized-data
file that can't be read (even after tolerating any extra '#!'-labeled
block it might carry -- see `_read_tokendata_file()`'s own docstring) is
skipped, with a message on stderr, rather than aborting the whole run --
every other file's sentences still get analyzed and diagrammed. The
script exits non-zero if any input file was skipped, if any passage failed
to analyze (see below), or if nothing was written at all.

A SENTENCE'S own analysis can also fail outright, distinct from a whole
file being unreadable -- `analyze_tokendata_to_files()`'s own per-sentence
try/except (its `SentenceAnalysis` call exhausting `token_budget.
analyze_with_retry()`'s own retries, say) catches this at the same finer
grain analyze_tokendata_to_files.py itself now does: that one sentence
alone is skipped, every other sentence across every input file still gets
analyzed and diagrammed, and the failure is collected into
`arsgrammatica.FailedPassage`. Once every file has been processed, every
such failure is written to `<output_dir>/warnings.txt` alongside a
statement of the whole run's total LM cost
(`arsgrammatica.write_warnings_report()`) -- see that function's own
docstring for the exact contents. `warnings.txt` is always written, even
when nothing failed, and gets its own "Wrote ..." line on stdout like
every other output file here.

Progress messages for stage 1 (per-file, per-sentence analyzing) are that
stage's own -- this script only adds one line marking which of the two
stages is running now ("[1/2] ...", "[2/2] ..."), all to stderr, like
every diagnostic here. Stdout carries only "Wrote ..." lines, one per
file this script writes (every analysis file, every PNG), same convention
every other script in this directory uses. The final LM-cost line always
prints to stderr, with no flag to suppress it.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# utilities/ isn't the repo root -- add the root so this imports the same
# way it would from a script sitting at the repo root, same as every
# other script in this directory's own identical comment.
sys.path.insert(0, str(Path(__file__).parent.parent))
from syntaxer_main import _configure_lm  # noqa: E402

from arsgrammatica import FailedPassage, Sentence, format_lm_cost, summarize_lm_cost, write_warnings_report

# Sibling scripts, imported by module name -- see this module's own
# docstring for why this is safe and preferred over duplicating their
# logic: utilities/ is already on sys.path (it's this script's own
# directory) by the time these imports run.
from analyze_tokendata_to_files import (  # noqa: E402
    _read_tokendata_file,
    analyze_tokendata_to_files,
)
from analyze_w_diagrams import _write_diagrams, graphviz  # noqa: E402


def analyze_tokendata_w_diagrams(
    file_sentences: List[Tuple[str, List[Sentence]]],
    output_dir: str,
    *,
    model: Optional[str] = None,
    orientation: str = "BT",
    color_by_verbal_unit: bool = True,
    rank_by_depth: bool = True,
    show_root: bool = True,
) -> Tuple[List[Tuple[Path, List[str]]], List[Path], List[FailedPassage]]:
    """Run stage 1 (full syntax analysis) then stage 2 (PNG diagrams) on
    `file_sentences` -- a list of `(file_stem, sentences)` pairs, one per
    already-tokenized input file, exactly as `_read_tokendata_file()`
    reads them and `analyze_tokendata_to_files.py`'s own `__main__` builds
    them -- writing everything under `output_dir`, created if it doesn't
    already exist.

    `model` is recorded on every analysis file's own `#!lm` block, same as
    every other analysis entry point in this codebase; omit it (the
    default) to skip `#!lm` entirely. `orientation`/`color_by_verbal_unit`/
    `rank_by_depth`/`show_root` are passed straight through to stage 2's
    own `tokengraph_to_dot()` call, same meaning as
    `analyses_to_dot_pngs.py`'s and `analyze_w_diagrams.py`'s own
    identically-named options.

    Returns `(written_analyses, written_diagrams, failed)`:
    `written_analyses` and `failed` are exactly what
    `analyze_tokendata_to_files()` itself returns for stage 1, extended
    across every input file in `file_sentences`' own order (a list of
    `(path, warnings)` pairs for every sentence actually analyzed, and a
    list of `arsgrammatica.FailedPassage` for any that failed outright --
    see this module's own docstring for what "failed" means here);
    `written_diagrams` is a list of every PNG path stage 2 wrote
    (naturally just the ones stage 1 actually produced a file for -- a
    failed sentence has nothing for stage 2 to diagram at all).
    """
    written_analyses: List[Tuple[Path, List[str]]] = []
    failed: List[FailedPassage] = []
    for file_num, (file_stem, sentences) in enumerate(file_sentences, start=1):
        print(
            f"[1/2] ({file_num}/{len(file_sentences)}) Analyzing {file_stem!r}: "
            f"{len(sentences)} sentence(s)...",
            file=sys.stderr,
        )
        file_written, file_failed = analyze_tokendata_to_files(
            sentences, output_dir, file_stem, model=model
        )
        written_analyses.extend(file_written)
        failed.extend(file_failed)

    for out_path, warnings in written_analyses:
        for w in warnings:
            print(f"Warning ({out_path}): {w}", file=sys.stderr)
        print(f"Wrote {out_path}")

    print(f"[2/2] Rendering {len(written_analyses)} diagram(s)...", file=sys.stderr)
    analysis_paths = [path for path, _warnings in written_analyses]
    written_diagrams = _write_diagrams(
        analysis_paths,
        Path(output_dir) / "dots",
        orientation=orientation,
        color_by_verbal_unit=color_by_verbal_unit,
        rank_by_depth=rank_by_depth,
        show_root=show_root,
    )
    for png_path in written_diagrams:
        print(f"Wrote {png_path}")

    return written_analyses, written_diagrams, failed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Run one or more already-tokenized files (utilities/"
            "tokenize_ctsdata.py's own output) through full syntax "
            "analysis (analyze_tokendata_to_files.py) and render each "
            "resulting analysis as a PNG diagram (analyses_to_dot_pngs.py) "
            "-- writing everything under one output directory."
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
        help="Directory to write everything to -- one analysis file per "
             "sentence, and a 'dots/' subdirectory of PNG diagrams. "
             "Created if it doesn't already exist.",
    )
    parser.add_argument(
        "--orientation",
        choices=["BT", "TB", "LR", "RL"],
        default="BT",
        help="DOT rankdir for stage 2's diagrams -- tokengraph_to_dot()'s own "
             "orientation values (default: %(default)s).",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable verbal-unit coloring in stage 2's diagrams "
             "(tokengraph_to_dot()'s color_by_verbal_unit=False).",
    )
    parser.add_argument(
        "--no-rank",
        action="store_true",
        help="Disable forcing same-AAT-depth verbal expressions onto the same "
             "rank in stage 2's diagrams (tokengraph_to_dot()'s rank_by_depth=False).",
    )
    parser.add_argument(
        "--no-root",
        action="store_true",
        help="Omit the dedicated 'root' node every independent verb points to "
             "in stage 2's diagrams (tokengraph_to_dot()'s show_root=False).",
    )
    args = parser.parse_args()

    # Checked FIRST, before any input file is even read: a missing
    # graphviz install would otherwise only surface after a whole stage of
    # real, possibly costly LM work -- see this module's own docstring.
    if graphviz is None:
        print(
            "The `graphviz` package isn't installed, so stage 2's PNGs "
            "can't be rendered. Install it with `pip install graphviz` "
            "(already covered by `pip install -e \".[dev]\"`) -- see "
            "notes/install.md.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Read (and validate) every input file before configuring an LM or
    # spending any calls on it, matching analyze_tokendata_to_files.py's
    # own convention -- a bad path or malformed tokenized-data file is
    # caught fast and cheaply. A bad file is skipped (not fatal), same as
    # that script's own per-file error handling, so one malformed file
    # doesn't stop every other file's sentences from being analyzed and
    # diagrammed.
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
    written_analyses, written_diagrams, failed = analyze_tokendata_w_diagrams(
        file_sentences,
        args.output_dir,
        model=lm.model,
        orientation=args.orientation,
        color_by_verbal_unit=not args.no_color,
        rank_by_depth=not args.no_rank,
        show_root=not args.no_root,
    )

    # stdout carries nothing but the "Wrote ..." lines already printed
    # inside analyze_tokendata_w_diagrams() above -- same stdout/stderr
    # split every other script here uses -- so the total-cost line goes
    # to stderr instead. This totals every SentenceAnalysis call made
    # across every sentence in every input file -- stage 2 makes no LM
    # calls at all.
    cost_summary = summarize_lm_cost(lm.history)
    print(f"LM cost: {format_lm_cost(cost_summary)}", file=sys.stderr)

    # warnings.txt gets its own "Wrote ..." line on stdout, same as every
    # other output file above -- see this module's own docstring for what
    # it contains and why it's always written, even when `failed` is empty.
    warnings_path = write_warnings_report(Path(args.output_dir) / "warnings.txt", failed, lm.history)
    print(f"Wrote {warnings_path}")

    if not written_analyses:
        print("No analyses were written -- every input file was empty.", file=sys.stderr)
        sys.exit(1)
    if had_failure or failed:
        sys.exit(1)
