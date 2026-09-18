"""
Command-line utility: read a `#!ctsdata` (CEX) corpus from an input file
(`ctsdata.py`'s `read_ctsdata()`), run it through full syntax analysis, and
write EACH resulting sentence's own analysis to its own file in an output
directory, using `serialization.py`'s `write_analyses()` format (the same
`#!sentences`/`#!verbal_units`/`#!tokens`[/optional `#!lm`] format
`read_analyses()`, `analysis_to_dot.py`, and `analyses_to_dot_pngs.py`
already read).

Unlike `utilities/tokenize_ctsdata.py` (segmentation only, no syntax
analysis at all), this script runs the FULL pipeline: `analyze_sources()`
(segmentation, then one `SentenceAnalysis` call per sentence via
`token_budget.analyze_with_retry()`, the same retry-on-truncation behavior
every other analysis entry point in this codebase gets). It's essentially
`syntaxer_main.py` generalized from one hand-typed passage to a whole CEX
corpus file, writing one output file per sentence instead of one combined
stream to stdout.

It follows the SAME clustering strategy `tokenize_ctsdata.py` uses ahead of
its own segmentation call, rather than calling `analyze_sources()` once
across the whole corpus: `passage_grouping.group_passages_by_sentence_boundary()`
first clusters the corpus's passages into the smallest possible runs of
consecutive passages that each begin and end at a likely sentence boundary
-- no LM call for this step -- and `analyze_sources()` then runs ONCE PER
GROUP (segmentation AND every one of that group's own sentences' full
analysis), rather than once for the whole corpus. A single sentence
spanning several passages is still segmented and analyzed as one
continuous unit (it's in one group together); it just no longer forces
every OTHER, unrelated sentence in the corpus into the same pair of LM
calls. As with `tokenize_ctsdata.py`, this trades a little accuracy for
smaller, cheaper calls: the grouping heuristic has no abbreviation
handling, so a passage ending in a praenomen or other abbreviation (e.g.
"M.", "cos.") is (wrongly) treated as its own sentence boundary, closing a
group one passage too early (see `passage_grouping.py`'s own module
docstring for this exact, pre-existing caveat) -- `analyze_sources()`
itself is still fully accurate for whatever text it's actually given; only
the grouping step ahead of it can misjudge where one group ends and the
next begins. Any warning `group_passages_by_sentence_boundary()` itself
returns (only ever: the corpus's last group not ending at a sentence
boundary, e.g. because the corpus is a truncated excerpt) is printed to
stderr.

Unlike `tokenize_ctsdata.py`, this script itself doesn't need to do
anything extra for cross-group id uniqueness: it writes ONE FILE PER
SENTENCE, and each file is entirely self-contained, so a token id only
ever needs to be unique and internally consistent WITHIN its own
sentence's own file. `analyze_sources()` (`pipeline.py`) already rewrites
every CTS-URN-cited token's id to a passage-scoped composite id
(`arsgrammatica.assign_passage_scoped_ids()`) before it ever calls
SentenceAnalysis, for a different reason than uniqueness within one file:
it's what makes a given passage's own tokens get the SAME ids here as they
would running `tokenize_ctsdata.py` then `analyze_tokendata_to_files.py`
on the same corpus, so the two pipelines can actually share DSPy's LM
response cache for a passage they both segment the same way, instead of
each independently sampling the LM for what should be an identical call.

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

Each file also records a `#!lm` block (the configured model, plus that
sentence's own reasoning), matching `syntaxer_main.py`'s own convention --
see `serialization.py`'s module docstring for the `#!lm` block's exact
shape. Any validation problem `analyze_sources()` finds for a sentence is
printed by `analyze_sources()` itself, to stderr, rather than duplicated by
this script; any warning
`write_analyses()` itself returns (e.g. a boundary-token mismatch) is
printed per file, to stderr, alongside a "Wrote ..." line per file on
stdout -- same stdout/stderr split `analyses_to_dot_pngs.py` uses. The
script exits non-zero if nothing was written at all (an empty corpus).

After every file is written, one more line goes to stderr reporting the
TOTAL LM cost of the whole run -- every call `analyze_sources()` made
across every group (one segmentation call per group, plus one
`SentenceAnalysis` call per sentence in it), via
`arsgrammatica.summarize_lm_cost()`/`format_lm_cost()` -- the same helpers
`utilities/tokenize_ctsdata.py` and every marimo notebook's own "See cost"
display already use, so the wording (no calls, an all-cache-hit history, a
priced/cached mix, every call priced) is consistent with the rest of the
codebase. Always prints, with no flag to suppress it.

A corpus of any real size can take a while -- every group's own
segmentation call, and every sentence's own `SentenceAnalysis` call, is a
real, possibly slow LM round trip -- so this also prints a one-line
progress message to STDERR before each of those calls: one summarizing how
many groups the (instant, LM-free) clustering step found, one per group as
its own segmentation-and-analysis call starts (`[g/G] ...`), and one per
sentence within it (`  [i/N] ...`, via `analyze_sources()`'s own
`progress_callback` hook, numbered within that group), so a long run
doesn't look hung. Purely a heartbeat, not a diagnostic -- it carries no
information `written`'s own return value doesn't already have -- and, like
every other diagnostic here, never touches stdout, so
`... > out_dir_manifest.txt`-style redirection of just the "Wrote ..."
lines is unaffected.
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

from arsgrammatica import (
    CitedText,
    Sentence,
    analyze_sources,
    format_lm_cost,
    group_passages_by_sentence_boundary,
    read_ctsdata,
    summarize_lm_cost,
    write_analyses,
)


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
    """Cluster `cited_texts` into the smallest possible groups that each
    begin and end at a sentence boundary
    (`group_passages_by_sentence_boundary()`'s fast, LM-free heuristic --
    no LM call for this step, same as `tokenize_ctsdata.py`'s own
    identical clustering step), run ONE `analyze_sources()` call PER GROUP
    (segmentation, then full syntax analysis, one sentence at a time --
    rather than one `analyze_sources()` call across the whole corpus), and
    write each resulting sentence's own analysis to its own file under
    `output_dir` -- created if it doesn't already exist -- named via
    `sentence_filename_stem()`. See this module's own docstring for the
    full rationale and its one accuracy tradeoff.

    `model` is recorded on every file's own `#!lm` block (see
    `serialization.py`'s module docstring), alongside that sentence's own
    `reasoning` -- typically the configured LM's own `.model` (e.g.
    `_configure_lm()`'s return value's `.model`), matching
    `syntaxer_main.py`'s own convention; omit it (the default) to skip
    `#!lm` entirely, same as `write_analyses()` itself does when `model`
    isn't given.

    Returns a list of `(path, warnings)` pairs, one per sentence written,
    in group order and then in each group's own `analyze_sources()` order
    -- `warnings` is whatever `write_analyses()` itself returned for that
    one file (empty if nothing looks wrong; see `serialize_analyses()`'s
    docstring for what each warning means). Any validation problem
    `analyze_sources()` itself finds for a sentence is printed by
    `analyze_sources()` directly, to stderr, before this function ever
    gets to write that sentence's file; any warning
    `group_passages_by_sentence_boundary()` itself returns (only ever: the
    corpus's last group not ending at a sentence boundary) is printed to
    stderr up front, before any LM call is made.

    Prints a one-line progress message to stderr before each group's own
    `analyze_sources()` call, and again before each sentence's own
    `SentenceAnalysis` call within it (via `analyze_sources()`'s own
    `progress_callback` hook) -- see this module's own docstring for why.
    Never touches stdout.
    """
    groups, group_warnings = group_passages_by_sentence_boundary(cited_texts)
    print(
        f"Grouped {len(cited_texts)} passage(s) into {len(groups)} "
        "sentence-boundary group(s) (no LM call for this step).",
        file=sys.stderr,
    )
    for w in group_warnings:
        print(f"Warning: {w}", file=sys.stderr)

    all_sentences: List[Sentence] = []
    all_results = []
    remaining = iter(cited_texts)
    for group_num, group_ids in enumerate(groups, start=1):
        group_rows = [next(remaining) for _ in group_ids]
        print(
            f"[{group_num}/{len(groups)}] Segmenting and analyzing group of "
            f"{len(group_rows)} passage(s) starting {group_rows[0].citation!r}...",
            file=sys.stderr,
        )

        def _report_progress(index: int, total: int, sentence: Sentence) -> None:
            citation = sentence.tokens[0].citation if sentence.tokens else None
            print(
                f"  [{index + 1}/{total}] Analyzing sentence starting at "
                f"{citation or '(no citation)'!r}...",
                file=sys.stderr,
            )

        group_sentences, group_results = analyze_sources(group_rows, progress_callback=_report_progress)
        all_sentences.extend(group_sentences)
        all_results.extend(group_results)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    written: List[Tuple[Path, List[str]]] = []
    for index, (sentence, result) in enumerate(zip(all_sentences, all_results)):
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
            "Cluster a #!ctsdata (CEX) corpus into the smallest "
            "sentence-boundary-respecting groups (no LM call), run full "
            "syntax analysis on each group, and write one analysis file "
            "per sentence to an output directory."
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

    # stdout carries nothing but the per-file "Wrote ..." lines above --
    # same stdout/stderr split analyses_to_dot_pngs.py's own diagnostics
    # use -- so the total-cost line (via the same arsgrammatica.lm_cost
    # helpers utilities/tokenize_ctsdata.py and every marimo notebook's own
    # "See cost" display already use) goes to stderr instead, covering
    # every case format_lm_cost() itself handles: no calls, an
    # all-cache-hit history, a priced/cached mix, or every call priced.
    # This totals EVERY LM call analyze_sources() made across EVERY group --
    # one segmentation call per group, plus one SentenceAnalysis call per
    # sentence in it -- not just the last group's own calls.
    cost_summary = summarize_lm_cost(lm.history)
    print(f"LM cost: {format_lm_cost(cost_summary)}", file=sys.stderr)

    if not written:
        print("No analyses were written -- the corpus had no sentences.", file=sys.stderr)
        sys.exit(1)
