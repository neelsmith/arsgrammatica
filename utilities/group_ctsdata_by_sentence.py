"""
Command-line utility: read every passage out of a `#!ctsdata` (CEX) source
file (`ctsdata.py`'s `read_ctsdata()`), group them with
`passage_grouping.py`'s `group_passages_by_sentence_boundary()` -- the
smallest runs of consecutive passages that each begin and end on a sentence
boundary, per that function's own fast, LM-free text-ending heuristic (see
`notes/passage_grouping.md`) -- and write the result to standard output.

No LM access needed at all, unlike `utilities/tokenize_ctsdata.py` (which
reads the same kind of source file but calls `segment_sources()`): this
script never configures an LM and needs no `.env`. That also means its
grouping is only an approximation of real sentence boundaries -- see
`passage_grouping.py`'s own module docstring for exactly what it gets wrong
(abbreviation periods) compared to the LM-driven segmentation
`tokenize_ctsdata.py`/`analyze_sources()` do.

Output format: one line per group, that group's passage ids (each
`CitedText.citation` -- for a `#!ctsdata` file, its full CTS URN) joined by
a single space by default, in `read_ctsdata()`'s own file order -- both
across groups and within each group. A group of one passage is just that
one id, no delimiter. Space-separated by default (rather than this
codebase's usual '|') specifically so a line of output can be pasted
directly into marimo/latin_syntaxer_selected_ids.py's own passage-id text
box, which splits on whitespace -- see that notebook's own
parse_passage_ids(). Pass `--output-delimiter` to use something else (e.g.
'|', to match every other serialized format here) if that's more useful
for a given downstream consumer. Any warning
`group_passages_by_sentence_boundary()` returns (only ever the final group
not ending at a sentence boundary) is written to stderr, not stdout, so
redirecting or piping stdout stays clean either way -- same convention as
`analysis_to_dot.py`/`analyses_to_dot_pngs.py`'s own stdout/stderr split.

Usage:
    python utilities/group_ctsdata_by_sentence.py path/to/source.cex > groups.txt
    python utilities/group_ctsdata_by_sentence.py --delimiter ';' path/to/source.cex
    python utilities/group_ctsdata_by_sentence.py path/to/source.cex --output-delimiter '|'

`--delimiter` controls the SOURCE `#!ctsdata` file's own column delimiter
(passed straight through to `read_ctsdata()`). `--output-delimiter`
controls what joins a group's ids on this script's OWN output line
(default a single space, see above) -- the two are independent; changing
one never affects the other. (Same caveat `ctsdata.py`/`serialization.py`
already note for their own delimiters: there's no escaping mechanism, so a
passage id that itself contains the chosen output delimiter would
round-trip ambiguously -- not a concern for an ordinary CTS URN, which
never contains a space or '|'.)
"""

import argparse
import sys
from typing import List, Tuple

from pathlib import Path

# utilities/ isn't the repo root -- add the root so this imports the same
# way it would from a script sitting at the repo root, same as
# utilities/tokenize_ctsdata.py's own identical comment (though this script
# doesn't need syntaxer_main._configure_lm(), since it makes no LM call).
sys.path.insert(0, str(Path(__file__).parent.parent))

from arsgrammatica import CitedText, group_passages_by_sentence_boundary, read_ctsdata


def format_groups(groups: List[List[str]], delimiter: str = " ") -> str:
    """Render `groups` (as `group_passages_by_sentence_boundary()` returns
    them) as this script's own stdout text: one line per group, that
    group's ids joined by `delimiter` (a single space by default -- see
    this module's own docstring for why), terminated by a trailing
    newline. An empty `groups` list renders as an empty string (no
    trailing newline) -- there's nothing to write a blank line for."""
    if not groups:
        return ""
    return "\n".join(delimiter.join(group) for group in groups) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Group the passages in a #!ctsdata (CEX) source file into the "
            "smallest runs that each begin and end on a sentence boundary "
            "(group_passages_by_sentence_boundary()'s own fast, LM-free "
            "heuristic), writing one line per group to stdout."
        )
    )
    parser.add_argument("ctsdata_path", help="Path to a #!ctsdata (CEX) source file.")
    parser.add_argument(
        "--delimiter",
        default="|",
        help="Column delimiter used by the SOURCE #!ctsdata file (default '|'). "
             "Does not affect this script's own output -- see --output-delimiter.",
    )
    parser.add_argument(
        "--output-delimiter",
        default=" ",
        help="Delimiter joining a group's ids on this script's own output "
             "(default: a single space, so a line can be pasted directly "
             "into marimo/latin_syntaxer_selected_ids.py's own passage-id "
             "box). Independent of --delimiter, which is the SOURCE file's "
             "own column delimiter.",
    )
    args = parser.parse_args()

    cited_texts: List[CitedText] = read_ctsdata(args.ctsdata_path, delimiter=args.delimiter)

    groups, warnings = group_passages_by_sentence_boundary(cited_texts)
    for w in warnings:
        print(f"Warning: {w}", file=sys.stderr)

    sys.stdout.write(format_groups(groups, delimiter=args.output_delimiter))
