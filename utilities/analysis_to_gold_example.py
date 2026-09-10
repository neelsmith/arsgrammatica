"""
Read a saved analysis file (write_analyses()'s own pipe-delimited format --
see USAGE.md's "Saving and loading analyses", or notes/dot_diagrams.md) and
print it as ready-to-paste Python `GoldExample` source, via
tests/fixtures/harvest.py's gold_example_from_analysis() and
format_gold_example_source(). A thin command-line wrapper around those two
functions, for turning an already-reviewed, correct analysis straight into
a fixture without hand-transcribing it -- see harvest.py's own module
docstring for the full "harvest a real analysis into gold_examples.py"
workflow and the trainset-vs-held-out-eval judgment call that comes with
it.

No LM access needed -- read_analyses() reconstructs everything from the
file's own text, the same way analysis_to_dot.py and
marimo/latin_syntaxer_review.py's own analysis_file_browser cell do.

Operates on the file's whole tokengraph/verbalunits/sentences as
read_analyses() returns them -- already flat, spanning every sentence in
the file, the same shape write_analyses() saved it in -- and hands that
whole triple to gold_example_from_analysis() as ONE GoldExample, exactly
the same "no splitting" precedent analysis_to_dot.py already sets: that
function's own docstring is explicit that it does not split a multi-
sentence `sentences` list into several GoldExamples on its own. Point this
at a single-sentence saved file (e.g. one sentence at a time out of
marimo/latin_syntaxer_textinput.py's own "Save analysis" section) if
that's the fixture shape you want, which matches every existing
GOLD_EXAMPLES entry in tests/fixtures/gold_examples.py.

Usage:
    python utilities/analysis_to_gold_example.py analysis.cex my_new_slug > snippet.py
    python utilities/analysis_to_gold_example.py analysis.cex my_new_slug --tags "ablative absolute,depth two" > snippet.py
    python utilities/analysis_to_gold_example.py analysis.cex my_new_slug --answer-var _MY_OWN_ANSWER > snippet.py
    python utilities/analysis_to_gold_example.py analysis.cex my_new_slug --skip-validation > snippet.py

`slug` and `--tags` are exactly gold_example_from_analysis()'s own `slug`/
`tags` arguments (see that function's own docstring for gold_examples.py's
own naming convention) -- `--tags` takes a single comma-separated string,
split and stripped here, defaulting to no tags at all if omitted.
`--answer-var` defaults to the module-level constant name gold_examples.py's
own convention would suggest mechanically (`_<SLUG UPPERCASED>_ANSWER`,
alphanumeric-sanitized the same way marimo/latin_syntaxer_textinput.py's
own filename_base is) -- override it if you'd rather match an existing
file's own, usually shorter, naming by hand. `--passage` overrides
gold_example_from_analysis()'s own default (reconstructing the surface
text from the tokengraph).

`--reasoning`, if omitted, is NOT always gold_example_from_analysis()'s
own placeholder string: read_analyses() also returns each sentence's own
`#!LM` block (serialize_analyses()'s own REASONING= line -- see
notes/serialization_formats.md), and when the file has exactly one such
block with a real reasoning string, that becomes the default instead --
the model's own actual reasoning is usually a better draft explanation
than a placeholder, given a single-sentence file already carries it. A
multi-sentence file (more than one `#!LM` block) has no single unambiguous
reasoning to default to, so the placeholder still applies there unless
`--reasoning` is given explicitly. Either way, re-read whatever ends up in
the pasted snippet before treating it as more than a draft -- fill in (or
correct) a real explanation by hand once it's in gold_examples.py, per
gold_example_from_analysis()'s own docstring: the placeholder is meant to
be replaced, not shipped, and even the model's own reasoning is worth a
human check.

`--skip-validation` passes straight through to gold_example_from_analysis()'s
own `skip_validation` -- use it only if you already know why validate()
would object and mean to harvest the analysis anyway; leaving it off (the
default) is what actually catches a malformed analysis before it becomes a
fixture.

The printed snippet is a convenience for a human pasting/reviewing the
result, not a guarantee of gold_examples.py's exact hand-wrapped
formatting (long 'reasoning' strings especially) -- re-read it once it's
pasted in and re-wrap/word it by hand as needed, same as
format_gold_example_source()'s own docstring already says.
"""

import argparse
import sys
from pathlib import Path

# utilities/ isn't the repo root -- add the root to sys.path so
# "from arsgrammatica import ..." resolves the same way it does for a
# script run straight from the repo root (see tokenize_ctsdata.py's own
# copy of this comment/pattern). tests/ needs the same treatment for
# "from fixtures.harvest import ..." below -- fixtures/ has no __init__.py
# of its own (an implicit PEP 420 namespace package, the same way every
# test file's own "from fixtures.gold_examples import GOLD_EXAMPLES" and
# pytest.ini's "pythonpath = ." already rely on), so it only resolves once
# tests/ itself, not the repo root, is on sys.path.
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "tests"))
from arsgrammatica import read_analyses  # noqa: E402
from fixtures.harvest import format_gold_example_source, gold_example_from_analysis  # noqa: E402


def default_answer_var_name(slug: str) -> str:
    """A mechanical `_<SLUG UPPERCASED>_ANSWER` default for `--answer-var`,
    alphanumeric-sanitized the same way marimo/latin_syntaxer_textinput.py's
    own filename_base is -- gold_examples.py's own hand-written constants
    are often a shorter, more readable abbreviation of their slug (see
    format_gold_example_source()'s own docstring), so this is only a
    reasonable starting point to rename by hand, not a claim that it
    matches existing style."""
    sanitized = "".join(c if c.isalnum() else "_" for c in slug).strip("_")
    return f"_{sanitized.upper()}_ANSWER"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Render a saved analysis file as ready-to-paste Python GoldExample source."
    )
    parser.add_argument(
        "analysis_file",
        help="Path to a saved analysis file (write_analyses()'s own format).",
    )
    parser.add_argument(
        "slug",
        help="GoldExample.slug for the harvested fixture (gold_examples.py's own naming convention).",
    )
    parser.add_argument(
        "--tags",
        default="",
        help="Comma-separated GoldExample.tags (default: no tags).",
    )
    parser.add_argument(
        "--answer-var",
        default=None,
        help="Module-level canned_answer constant name (default: derived mechanically from slug).",
    )
    parser.add_argument(
        "--passage",
        default=None,
        help="Override GoldExample.passage (default: reconstructed from the tokengraph).",
    )
    parser.add_argument(
        "--reasoning",
        default=None,
        help="Override canned_answer['reasoning'] (default: the file's own single #!LM "
             "reasoning, if it has exactly one, else an obvious placeholder string).",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip gold_example_from_analysis()'s own validate() call (default: run it).",
    )
    args = parser.parse_args()

    try:
        tokengraph, verbalunits, sentences, lm_infos = read_analyses(args.analysis_file)
    except (ValueError, OSError) as e:
        print(f"Could not read {args.analysis_file!r} as a saved analysis: {e}", file=sys.stderr)
        sys.exit(1)

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    answer_var_name = args.answer_var or default_answer_var_name(args.slug)

    # A single-sentence file's own #!LM reasoning (see this script's own
    # module docstring) is a better default draft explanation than
    # gold_example_from_analysis()'s own generic placeholder -- but only
    # when there's exactly one such block to draw from unambiguously; a
    # multi-sentence file, or one with no reasoning recorded at all, falls
    # straight through to that function's own default instead.
    reasoning = args.reasoning
    if reasoning is None and len(lm_infos) == 1 and lm_infos[0].reasoning:
        reasoning = lm_infos[0].reasoning

    try:
        example = gold_example_from_analysis(
            args.slug,
            tags,
            sentences,
            verbalunits,
            tokengraph,
            passage=args.passage,
            reasoning=reasoning,
            skip_validation=args.skip_validation,
        )
    except ValueError as e:
        print(f"Could not build a GoldExample from {args.analysis_file!r}: {e}", file=sys.stderr)
        sys.exit(1)

    # Only the formatted source goes to stdout, so `... > snippet.py`
    # redirects cleanly -- same stdout/stderr split analysis_to_dot.py's
    # own script uses.
    print(format_gold_example_source(example, answer_var_name))
