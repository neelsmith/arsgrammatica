"""
Command-line utility: run the full ctsdata -> diagrams pipeline on one
`#!ctsdata` (CEX) source file, end to end, in one invocation -- the
equivalent of running these three scripts by hand, in order:

    python utilities/tokenize_ctsdata.py corpus.cex > tokenized.txt
    python utilities/analyze_tokendata_to_files.py tokenized.txt --output-dir out/
    python utilities/analyses_to_dot_pngs.py out/*.cex --output-dir out/dots/

...but as one script, one argparse invocation, one `.env` read
(`_configure_lm()` is called exactly once, and its LM is reused for BOTH
stages that make LM calls), and one combined LM-cost total covering every
call either stage made (diagramming makes no LM calls at all).

Each stage's own function is reused directly rather than shelled out to or
reimplemented:

  1. `tokenize_ctsdata.tokenize_ctsdata()` -- clusters the corpus's
     passages into the smallest sentence-boundary-respecting groups (no LM
     call), segments each group with its own `segment_sources()` call, and
     combines the result into one `#!sentences`/`#!tokens` text with every
     CTS-URN-cited token's id rewritten to a passage-scoped composite id
     (see that module's own docstring). Unlike running it by hand, this
     script doesn't throw the result away after use: it's written to
     `<output_dir>/<corpus_stem>_tokenized.txt`, worth keeping on disk to
     inspect how the corpus segmented, or to feed straight into
     `analyze_tokendata_to_files.py` again by hand later (e.g. to try a
     different model on the exact same segmentation) without paying for
     another round of segmentation calls.
  2. `analyze_tokendata_to_files.analyze_tokendata_to_files()` -- runs
     every sentence stage 1 found through full syntax analysis, one
     `SentenceAnalysis` call per sentence (`token_budget.analyze_with_retry()`),
     writing one analysis file per sentence directly under `output_dir`
     (not a subdirectory -- matching `--output-dir out/` in the by-hand
     version above).
  3. This module's own `_write_diagrams()` -- the one stage with no
     importable function of its own (`analyses_to_dot_pngs.py`'s own logic
     lives entirely inside its `__main__` block), reproduced here rather
     than imported. This is the same, small amount of duplication
     `sentence_filename_stem()`/`_diagram_filename_stem()` already
     tolerates identically across every script in this codebase, rather
     than importing between CLI scripts for one helper's worth of code.
     Renders every one of stage 2's own analysis files as a PNG via
     `tokengraph_to_dot()` + `graphviz`, written to `<output_dir>/dots/`
     (matching `--output-dir out/dots/` above).

`tokenize_ctsdata.py`'s and `analyze_tokendata_to_files.py`'s own functions
are imported by their module names (`import tokenize_ctsdata`, `from
analyze_tokendata_to_files import analyze_tokendata_to_files`) rather than
duplicated -- `utilities/` is already the first entry on `sys.path` when a
script inside it runs the normal way (`python
utilities/analyze_w_diagrams.py ...`), the same way any script's own
directory is, so importing a sibling script here works exactly like
importing any other module; no special path setup needed beyond what
every script in this directory already does to reach the repo root for
`syntaxer_main`.

Usage:
    python utilities/analyze_w_diagrams.py corpus.cex --output-dir out/
    python utilities/analyze_w_diagrams.py corpus.cex --output-dir out/ --delimiter ';'
    python utilities/analyze_w_diagrams.py corpus.cex --output-dir out/ --orientation LR
    python utilities/analyze_w_diagrams.py corpus.cex --output-dir out/ --no-color --no-rank

Needs the same `.env` as `syntaxer_main.py` (`API_BASE`/`MODEL`/`API_KEY`) --
stage 1's segmentation calls and stage 2's `SentenceAnalysis` calls are
both real LM calls. Also needs the `graphviz` PyPI package AND a separate
Graphviz installation (the `dot` command-line tool) for stage 3 -- see
`notes/graphviz_install.md` and `notes/install.md`. That's checked FIRST,
before the source file is even read, let alone any LM configured or
called -- there's no reason to pay for two whole stages of real LM work
only to find out at the very end that stage 3 can't run at all.

`--output-dir` ends up holding: `<corpus_stem>_tokenized.txt` (stage 1),
one `<corpus_stem>_<n>_<citation>.cex` analysis file per sentence (stage
2), and a `dots/` subdirectory of one `<analysis_file_stem>_1_<citation>.png`
per sentence (stage 3) -- the doubled-up "_1_<citation>" in that last name
isn't new here, it's exactly what `analyses_to_dot_pngs.py` already does
when fed a one-sentence-per-file input, which is all stage 2 ever
produces. The directory is created if it doesn't already exist.

Progress messages for stages 1 and 2 (grouping, per-group segmenting,
per-sentence analyzing) are each stage's own -- this script only adds one
line marking which of the three stages is running now ("[1/3] ...", "[2/3]
...", "[3/3] ..."), all to stderr, like every diagnostic here. Stdout
carries only "Wrote ..." lines, one per file this script writes (the
tokenized-data file, every analysis file, every PNG), same convention
every other script in this directory uses. The final LM-cost line (via
`arsgrammatica.summarize_lm_cost()`/`format_lm_cost()`, covering every call
either LM-calling stage made) always prints to stderr, with no flag to
suppress it.

Any validation problem `analyze_tokendata_to_files()` finds for a sentence
is printed by that function itself, to stderr; any warning
`tokenize_ctsdata()`'s own clustering step returns (only ever: the
corpus's last group not ending at a sentence boundary) or
`write_analyses()`/`tokengraph_to_dot()` themselves return is printed here,
also to stderr. Stage 1 (tokenizing) is still fail-fast, same as
`tokenize_ctsdata.py`'s own documented, deliberate handling of the exact
same `segment_sources()` call it makes internally: a failed group there
would gap the id sequence its own combined `#!sentences`/`#!tokens` output
requires to be contiguous, so a bad LM response for one group still aborts
the whole run rather than skipping just that group. Stage 2, however, is
NOT fail-fast the way it used to be: one SENTENCE's own `SentenceAnalysis`
call failing outright (`analyze_tokendata_to_files()`'s own per-sentence
try/except -- exhausting `token_budget.analyze_with_retry()`'s own retries,
say) no longer aborts the run either -- that one sentence is skipped, every
other sentence (and stage 3's diagrams for them) still gets produced, and
the failure is collected into `<output_dir>/warnings.txt` alongside a
statement of the whole run's total LM cost
(`arsgrammatica.write_warnings_report()`) -- see that function's own
docstring for the exact contents. `warnings.txt` is always written, even
when nothing failed, and gets its own "Wrote ..." line on stdout like
every other output file here.
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

from arsgrammatica import (
    CitedText,
    FailedPassage,
    format_lm_cost,
    read_analyses,
    read_ctsdata,
    read_segmentation,
    split_analysis_by_sentence,
    summarize_lm_cost,
    tokengraph_to_dot,
    write_warnings_report,
)

# Sibling scripts, imported by module name -- see this module's own
# docstring for why this is safe and preferred over duplicating their
# logic: utilities/ is already on sys.path (it's this script's own
# directory) by the time these imports run.
from tokenize_ctsdata import tokenize_ctsdata  # noqa: E402
from analyze_tokendata_to_files import analyze_tokendata_to_files  # noqa: E402

try:
    import graphviz
except ImportError:
    graphviz = None


def _diagram_filename_stem(file_stem: str, index: int, citation: Optional[str]) -> str:
    """Identical to `analyses_to_dot_pngs.py`'s own `sentence_filename_stem()`
    (duplicated, not imported -- see this module's own docstring)."""
    raw = f"{file_stem}_{index + 1}_{citation or ''}"
    sanitized = "".join(c if c.isalnum() else "_" for c in raw).strip("_")
    return sanitized or f"{file_stem}_sentence_{index + 1}"


def _write_diagrams(
    analysis_paths: List[Path],
    output_dir: Path,
    *,
    orientation: str = "BT",
    color_by_verbal_unit: bool = True,
    rank_by_depth: bool = True,
    show_root: bool = True,
) -> List[Path]:
    """Render every sentence in `analysis_paths` (stage 2's own written
    analysis files) as a PNG diagram under `output_dir` -- created if it
    doesn't already exist. Mirrors `analyses_to_dot_pngs.py`'s own
    `__main__` logic exactly (same helper, same `tokengraph_to_dot()`
    call, same naming), minus that script's own per-file skip-on-error
    handling: these files were just written by THIS SAME pipeline run, so
    a read failure here is this codebase's own bug, not bad user input,
    and should abort loudly rather than be silently skipped.

    Returns every PNG path written, in `analysis_paths`' own order and
    then each file's own sentence order (always exactly one sentence per
    file here, since that's all stage 2 ever produces, but this doesn't
    assume that -- same as `analyses_to_dot_pngs.py` itself doesn't).
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    written: List[Path] = []
    for analysis_path in analysis_paths:
        file_stem = Path(analysis_path).stem
        tokengraph, verbalunits, sentences, _lm_infos = read_analyses(str(analysis_path))
        sentence_slices = split_analysis_by_sentence(tokengraph, verbalunits, sentences)

        for index, (sentence, (sentence_tokengraph, _sentence_verbalunits)) in enumerate(
            zip(sentences, sentence_slices)
        ):
            citation = sentence.tokens[0].citation if sentence.tokens else None
            dot_source, warnings = tokengraph_to_dot(
                sentence_tokengraph,
                orientation=orientation,
                color_by_verbal_unit=color_by_verbal_unit,
                rank_by_depth=rank_by_depth,
                show_root=show_root,
            )
            for w in warnings:
                print(f"Warning ({analysis_path}, sentence {index + 1}): {w}", file=sys.stderr)

            png_bytes = graphviz.Source(dot_source).pipe(format="png")

            stem = _diagram_filename_stem(file_stem, index, citation)
            png_path = output_dir / f"{stem}.png"
            png_path.write_bytes(png_bytes)
            written.append(png_path)

    return written


def analyze_w_diagrams(
    rows: List[CitedText],
    output_dir: str,
    file_stem: str,
    *,
    model: Optional[str] = None,
    orientation: str = "BT",
    color_by_verbal_unit: bool = True,
    rank_by_depth: bool = True,
    show_root: bool = True,
) -> Tuple[Path, List[Tuple[Path, List[str]]], List[Path], List[FailedPassage]]:
    """Run the full pipeline on `rows` (as `read_ctsdata()` returns them),
    writing everything under `output_dir` -- created if it doesn't already
    exist -- via the three stages described in this module's own
    docstring.

    `model` is recorded on every analysis file's own `#!lm` block, same as
    every other analysis entry point in this codebase; omit it (the
    default) to skip `#!lm` entirely.

    Returns `(tokenized_path, written_analyses, written_diagrams, failed)`:
    `tokenized_path` is stage 1's own output file; `written_analyses` and
    `failed` are exactly what `analyze_tokendata_to_files()` itself returns
    for stage 2 (a list of `(path, warnings)` pairs for every sentence
    actually analyzed, and a list of `arsgrammatica.FailedPassage` for any
    that failed outright -- see this module's own docstring for what
    "failed" means here); `written_diagrams` is a list of every PNG path
    stage 3 wrote (naturally just the ones stage 2 actually produced a file
    for -- a failed sentence has nothing for stage 3 to diagram at all).
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1/3] Tokenizing {len(rows)} passage(s)...", file=sys.stderr)
    text, tokenize_warnings = tokenize_ctsdata(rows)
    for w in tokenize_warnings:
        print(f"Warning: {w}", file=sys.stderr)

    tokenized_path = out_dir / f"{file_stem}_tokenized.txt"
    tokenized_path.write_text(text)
    print(f"Wrote {tokenized_path}")

    sentences = read_segmentation(str(tokenized_path))

    print(f"[2/3] Analyzing {len(sentences)} sentence(s)...", file=sys.stderr)
    written_analyses, failed = analyze_tokendata_to_files(sentences, output_dir, file_stem, model=model)
    for out_path, warnings in written_analyses:
        for w in warnings:
            print(f"Warning ({out_path}): {w}", file=sys.stderr)
        print(f"Wrote {out_path}")

    print(f"[3/3] Rendering {len(written_analyses)} diagram(s)...", file=sys.stderr)
    analysis_paths = [path for path, _warnings in written_analyses]
    written_diagrams = _write_diagrams(
        analysis_paths,
        out_dir / "dots",
        orientation=orientation,
        color_by_verbal_unit=color_by_verbal_unit,
        rank_by_depth=rank_by_depth,
        show_root=show_root,
    )
    for png_path in written_diagrams:
        print(f"Wrote {png_path}")

    return tokenized_path, written_analyses, written_diagrams, failed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Run a #!ctsdata (CEX) corpus through the full pipeline: "
            "tokenize (tokenize_ctsdata.py's own clustering + "
            "segmentation), analyze every resulting sentence "
            "(analyze_tokendata_to_files.py), and render each analysis as "
            "a PNG diagram (analyses_to_dot_pngs.py) -- writing everything "
            "under one output directory."
        )
    )
    parser.add_argument("ctsdata_path", help="Path to a #!ctsdata (CEX) source file.")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to write everything to -- the tokenized-data file, "
             "one analysis file per sentence, and a 'dots/' subdirectory "
             "of PNG diagrams. Created if it doesn't already exist.",
    )
    parser.add_argument(
        "--delimiter",
        default="|",
        help="Column delimiter used by the SOURCE #!ctsdata file (default '|'). "
             "Does not affect any of this script's own '|'-delimited output.",
    )
    parser.add_argument(
        "--orientation",
        choices=["BT", "TB", "LR", "RL"],
        default="BT",
        help="DOT rankdir for stage 3's diagrams -- tokengraph_to_dot()'s own "
             "orientation values (default: %(default)s).",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable verbal-unit coloring in stage 3's diagrams "
             "(tokengraph_to_dot()'s color_by_verbal_unit=False).",
    )
    parser.add_argument(
        "--no-rank",
        action="store_true",
        help="Disable forcing same-AAT-depth verbal expressions onto the same "
             "rank in stage 3's diagrams (tokengraph_to_dot()'s rank_by_depth=False).",
    )
    parser.add_argument(
        "--no-root",
        action="store_true",
        help="Omit the dedicated 'root' node every independent verb points to "
             "in stage 3's diagrams (tokengraph_to_dot()'s show_root=False).",
    )
    args = parser.parse_args()

    # Checked FIRST, before the source file is even read: a missing
    # graphviz install would otherwise only surface after two whole
    # stages of real, possibly costly LM work -- see this module's own
    # docstring.
    if graphviz is None:
        print(
            "The `graphviz` package isn't installed, so stage 3's PNGs "
            "can't be rendered. Install it with `pip install graphviz` "
            "(already covered by `pip install -e \".[dev]\"`) -- see "
            "notes/install.md.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Read (and validate) the source file before configuring an LM or
    # spending any calls on it, matching every other script in this
    # directory's own convention -- a bad path or malformed #!ctsdata
    # file fails fast and cheaply.
    rows = read_ctsdata(args.ctsdata_path, delimiter=args.delimiter)

    lm = _configure_lm()
    tokenized_path, written_analyses, written_diagrams, failed = analyze_w_diagrams(
        rows,
        args.output_dir,
        Path(args.ctsdata_path).stem,
        model=lm.model,
        orientation=args.orientation,
        color_by_verbal_unit=not args.no_color,
        rank_by_depth=not args.no_rank,
        show_root=not args.no_root,
    )

    # stdout carries nothing but the "Wrote ..." lines already printed
    # inside analyze_w_diagrams() above -- same stdout/stderr split every
    # other script here uses -- so the total-cost line goes to stderr
    # instead. This totals EVERY LM call across BOTH LM-calling stages:
    # tokenize_ctsdata()'s own segmentation calls (one per cluster group)
    # plus analyze_tokendata_to_files()'s own SentenceAnalysis calls (one
    # per sentence) -- diagramming makes no LM calls at all.
    cost_summary = summarize_lm_cost(lm.history)
    print(f"LM cost: {format_lm_cost(cost_summary)}", file=sys.stderr)

    # warnings.txt gets its own "Wrote ..." line on stdout, same as every
    # other output file above -- see this module's own docstring for what
    # it contains and why it's always written, even when `failed` is empty.
    warnings_path = write_warnings_report(Path(args.output_dir) / "warnings.txt", failed, lm.history)
    print(f"Wrote {warnings_path}")

    if not written_analyses:
        print("No analyses were written -- the corpus had no sentences.", file=sys.stderr)
        sys.exit(1)
    if failed:
        sys.exit(1)
