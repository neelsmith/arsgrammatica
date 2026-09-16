"""
Read a saved analysis file (write_analyses()'s own pipe-delimited format --
see USAGE.md's "Saving and loading analyses", or notes/dot_diagrams.md) and
write its tokengraph as a self-contained, browser-ready displaCy-style
dependency diagram (see notes/displacy_viz.md), via save_displacy_html().
The command-line counterpart to analysis_to_dot.py, for displaCy's own
sentence-and-arcs style instead of Graphviz's node-and-edge graph.

Unlike analysis_to_dot.py's DOT source (which still needs `dot -Tsvg` to
become a picture) or analysis_to_mermaid's Mermaid source (which needs a
Mermaid-aware viewer), this script's own output is a complete HTML file --
open it directly in a browser, no further rendering step needed.

No LM access needed -- read_analyses() reconstructs everything from the
file's own text, the same way analysis_to_dot.py does.

Operates on the file's whole tokengraph as read_analyses() returns it --
already one flat list spanning every sentence in the file, same as
analysis_to_dot.py -- not one sentence at a time. For a single sentence
out of a multi-sentence file, use marimo/latin_syntaxer_review.py instead,
or split_analysis_by_sentence() directly.

Usage:
    python utilities/analysis_to_displacy.py analysis.cex -o diagram.html
    python utilities/analysis_to_displacy.py analysis.cex -o diagram.html --no-color
    python utilities/analysis_to_displacy.py analysis.cex -o diagram.html --no-root
    python utilities/analysis_to_displacy.py analysis.cex -o diagram.html --caption "My own title"
"""

import argparse
import sys
from pathlib import Path

# utilities/ isn't the repo root -- add the root to sys.path so
# "from arsgrammatica import ..." resolves the same way it does for a
# script run straight from the repo root (see analysis_to_dot.py's own
# copy of this comment/pattern).
sys.path.insert(0, str(Path(__file__).parent.parent))
from arsgrammatica import read_analyses, save_displacy_html  # noqa: E402

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Render a saved analysis file's tokengraph as a self-contained "
            "displaCy-style dependency diagram, written as one HTML file."
        )
    )
    parser.add_argument(
        "analysis_file",
        help="Path to a saved analysis file (write_analyses()'s own format).",
    )
    parser.add_argument(
        "-o",
        "--output-file",
        default="displacy.html",
        help="HTML file to write the diagram to (default: %(default)s).",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable verbal-unit coloring (save_displacy_html()'s color_by_verbal_unit=False).",
    )
    parser.add_argument(
        "--no-root",
        action="store_true",
        help="Omit the synthetic ROOT word every independent verb points to "
             "(save_displacy_html()'s show_root=False).",
    )
    parser.add_argument(
        "--caption",
        default=None,
        help="Heading text shown above the diagram (default: the sentence's own "
             "reconstructed text). Pass an empty string for no heading at all.",
    )
    args = parser.parse_args()

    try:
        tokengraph, verbalunits, sentences, lm_infos = read_analyses(args.analysis_file)
    except (ValueError, OSError) as e:
        print(f"Could not read {args.analysis_file!r} as a saved analysis: {e}", file=sys.stderr)
        sys.exit(1)

    warnings = save_displacy_html(
        tokengraph,
        args.output_file,
        caption=args.caption,
        color_by_verbal_unit=not args.no_color,
        show_root=not args.no_root,
    )

    # Diagnostics go to stderr, same stdout/stderr split every other
    # utilities/*.py script in this codebase uses.
    for w in warnings:
        print(f"Warning: {w}", file=sys.stderr)
    print(f"Wrote {args.output_file}", file=sys.stderr)
