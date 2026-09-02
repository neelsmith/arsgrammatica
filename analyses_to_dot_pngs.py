"""
Read one or more saved analysis files (write_analyses()'s own pipe-
delimited format -- see notes/dot_diagrams.md, notes/install.md), render
every sentence's tokengraph as a Graphviz DOT diagram via
tokengraph_to_dot(), and write each one as a PNG to an output directory.
The batch/PNG counterpart to analysis_to_dot.py's own single-file, DOT-
text-to-stdout script -- use that one instead if you just want the DOT
source itself (e.g. to pipe into `dot -Tsvg` yourself, or for a format
other than PNG).

No LM access needed -- read_analyses() reconstructs everything from each
file's own text, the same way analysis_to_dot.py and
marimo/latin_syntaxer_dot.py's own analysis_file_browser cell do.

Needs the `graphviz` PyPI package AND a separate Graphviz installation
(the `dot` command-line tool) -- see notes/graphviz_install.md and
notes/install.md. `pip install -e ".[dev]"` covers the `graphviz` package;
the `dot` executable itself is always a separate install, on top of that.

Usage:
    python analyses_to_dot_pngs.py analysis.cex --output-dir diagrams/
    python analyses_to_dot_pngs.py a.cex b.cex c.cex --output-dir diagrams/
    python analyses_to_dot_pngs.py analysis.cex --output-dir diagrams/ --orientation LR
    python analyses_to_dot_pngs.py analysis.cex --output-dir diagrams/ --no-color --no-rank

One PNG per sentence, named "<file_stem>_<sentence_number>_<citation>.png"
(alphanumeric-sanitized, same convention marimo/latin_syntaxer_dot.py's
own download button uses) -- prefixed with the source file's own stem so
sentences from different input files never collide in the same output
directory. The output directory is created if it doesn't already exist.

A file that can't be read, or can't be split by sentence, is skipped (with
a message on stderr) rather than aborting the whole run -- everything else
still gets rendered. The script exits non-zero if any file was skipped, or
if nothing was written at all.
"""

import argparse
import sys
from pathlib import Path

from arsgrammatica import read_analyses, split_analysis_by_sentence, tokengraph_to_dot

try:
    import graphviz
except ImportError:
    graphviz = None


def sentence_filename_stem(file_stem, index, citation):
    """"<file_stem>_<n>_<citation>", alphanumeric-sanitized -- same
    convention marimo/latin_syntaxer_dot.py's own dot_filename_stem cell
    uses for its download button, prefixed with the source file's own
    stem so sentences from different input files never collide in one
    output directory."""
    raw = f"{file_stem}_{index + 1}_{citation or ''}"
    sanitized = "".join(c if c.isalnum() else "_" for c in raw).strip("_")
    return sanitized or f"{file_stem}_sentence_{index + 1}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Render every sentence in one or more saved analysis files as "
            "a Graphviz DOT diagram, and write each one as a PNG."
        )
    )
    parser.add_argument(
        "analysis_files",
        nargs="+",
        help="Path(s) to saved analysis file(s) (write_analyses()'s own format).",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to write PNGs to -- created if it doesn't already exist.",
    )
    parser.add_argument(
        "--orientation",
        choices=["BT", "TB", "LR", "RL"],
        default="BT",
        help="DOT rankdir -- tokengraph_to_dot()'s own orientation values (default: %(default)s).",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable verbal-unit coloring (tokengraph_to_dot()'s color_by_verbal_unit=False).",
    )
    parser.add_argument(
        "--no-rank",
        action="store_true",
        help="Disable forcing same-AAT-depth verbal expressions onto the same rank "
             "(tokengraph_to_dot()'s rank_by_depth=False).",
    )
    args = parser.parse_args()

    if graphviz is None:
        print(
            "The `graphviz` package isn't installed, so PNGs can't be rendered. "
            "Install it with `pip install graphviz` (already covered by "
            "`pip install -e \".[dev]\"`) -- see notes/install.md. Use "
            "analysis_to_dot.py instead if you just want the DOT text itself.",
            file=sys.stderr,
        )
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    wrote_any = False
    had_failure = False

    for analysis_file in args.analysis_files:
        file_stem = Path(analysis_file).stem
        try:
            tokengraph, verbalunits, sentences, lm_infos = read_analyses(analysis_file)
        except (ValueError, OSError) as e:
            print(
                f"Skipping {analysis_file!r}: could not read it as a saved analysis: {e}",
                file=sys.stderr,
            )
            had_failure = True
            continue

        try:
            sentence_slices = split_analysis_by_sentence(tokengraph, verbalunits, sentences)
        except ValueError as e:
            print(
                f"Skipping {analysis_file!r}: could not split it by sentence: {e}",
                file=sys.stderr,
            )
            had_failure = True
            continue

        # zip() stops at whichever list is shorter, same defensive
        # convention marimo/latin_syntaxer_dot.py's own sentence_dropdown
        # cell uses -- a split_analysis_by_sentence() result shorter than
        # `sentences` can't produce a mismatched, out-of-range index here.
        for index, (sentence, (sentence_tokengraph, _sentence_verbalunits)) in enumerate(
            zip(sentences, sentence_slices)
        ):
            citation = sentence.tokens[0].citation if sentence.tokens else None
            dot_source, warnings = tokengraph_to_dot(
                sentence_tokengraph,
                orientation=args.orientation,
                color_by_verbal_unit=not args.no_color,
                rank_by_depth=not args.no_rank,
            )
            for w in warnings:
                print(f"Warning ({analysis_file}, sentence {index + 1}): {w}", file=sys.stderr)

            try:
                png_bytes = graphviz.Source(dot_source).pipe(format="png")
            except graphviz.ExecutableNotFound:
                print(
                    "The `graphviz` package is installed, but the Graphviz "
                    "`dot` command itself isn't on your system's PATH -- "
                    "see notes/graphviz_install.md.",
                    file=sys.stderr,
                )
                sys.exit(1)

            stem = sentence_filename_stem(file_stem, index, citation)
            png_path = output_dir / f"{stem}.png"
            png_path.write_bytes(png_bytes)
            print(f"Wrote {png_path}")
            wrote_any = True

    if not wrote_any:
        print("No PNGs were written.", file=sys.stderr)
        sys.exit(1)
    if had_failure:
        sys.exit(1)
