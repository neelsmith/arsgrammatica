"""
Command-line utility: estimate the total LM cost of fully analyzing an
entire `#!ctsdata` (CEX) corpus, WITHOUT actually analyzing the whole
thing -- read the corpus (`ctsdata.py`'s `read_ctsdata()`), pick `n`
passages out of it at random, run only THOSE through full syntax analysis
(`analyze_sources()`, exactly what `analyze_ctsdata_to_files.py` and every
marimo ctsdata notebook already do), and serialize their combined analyses
to one output file, same `write_analyses()` format `read_analyses()`,
`analysis_to_dot.py`, and `analyses_to_dot_pngs.py` already read.

The point is the report this then writes to stdout: the sample's own cost
per sentence and per token, multiplied out against a MECHANICAL, LM-free
approximation of the WHOLE corpus's own sentence/token counts, to estimate
what analyzing every passage in the file would cost -- without actually
paying for that yet, and without spending a real LM call just to count the
corpus either.

An earlier version of this script got the corpus's own total sentence/token
counts from one real `segment_sources()` call over the ENTIRE corpus, up
front -- accurate, but itself a real (if usually much smaller) LM call, and
for a genuinely large corpus, one that can be slow or costly in its own
right -- exactly the kind of expense this script exists to help avoid
paying blindly. So the corpus-wide counts are now purely mechanical, no LM
call at all: tokens are a plain whitespace word count across every
passage's own raw text (`len(text.split())`, summed -- the same rough
measure `wc -w` gives on the command line), and sentences are `len(groups)`
from `passage_grouping.py`'s `group_passages_by_sentence_boundary()` -- an
existing, already-LM-free heuristic in this codebase that groups passages
into runs that begin and end at a likely sentence boundary, per-passage,
with no LM call. Both are rough by design, not a substitute for real
segmentation -- see `_approximate_corpus_counts()`'s own docstring for
exactly what each one gets wrong, and why that means the two extrapolated
cost estimates at the end of the report are approximations of an
approximation, not a precise projection.

A passage's own analysis can fail outright -- a live LM call can come back
malformed, rate-limited, or simply time out. Rather than losing the whole
sample (and whatever it's already spent) to one bad passage, each of the
`n` passages is analyzed with its OWN, individual `analyze_sources()` call
-- one at a time, in a random order -- and a passage that raises is simply
skipped in favor of the next untried passage in that order, so the sample
still always ends up with exactly `n` successfully analyzed passages (see
`estimate_corpus_cost()`'s own docstring for exactly what "skipped" means
for cost accounting, and for the one trade-off this makes: giving up
`analyze_sources()`'s own cross-passage sentence-spanning, since batching
several passages into one call is exactly what would make a single bad one
poison the whole batch). Every `n` passages tried, a conspicuous progress
banner goes to stderr, purely as a heartbeat -- see `_log_progress_banner()`.

"Sentences"/"tokens" for the SAMPLE (as opposed to the corpus-wide
approximations above) are always real segmentation's own counts:
`len(sentences)` and each sentence's own `len(sentence.tokens)`, i.e. the
tokens actually fed INTO analysis. This deliberately excludes any
"implied" token (an implied subject, an implied "sum", etc. -- see
`serialization.py`'s module docstring) a sentence's own full analysis
might additionally synthesize into its `tokengraph` -- there's no
comparable "implied token" notion for the corpus-wide word count to
match, so counting the sample the same, narrower way keeps the two sides
of the extrapolation this script's report exists to support at least
built the same way, even though the corpus side is already only a rough
approximation to begin with (see `_approximate_corpus_counts()`).

Usage:
    python utilities/estimate_corpus_cost.py corpus.cex
    python utilities/estimate_corpus_cost.py corpus.cex --n 10
    python utilities/estimate_corpus_cost.py corpus.cex --n 10 --output-file sample.cex
    python utilities/estimate_corpus_cost.py corpus.cex --seed 42
    python utilities/estimate_corpus_cost.py corpus.cex --delimiter ';'

Needs the same `.env` as `syntaxer_main.py` (`API_BASE`/`MODEL`/`API_KEY`) --
the sampled passages' full analysis makes real LM calls; the corpus-wide
counts do not.
"""

import argparse
import random
import sys
from pathlib import Path
from typing import List, NamedTuple, Optional, Tuple

# utilities/ isn't the repo root -- add the root so this imports the same
# way it would from a script sitting at the repo root, same as every other
# utilities/*.py script's own identical comment (e.g. tokenize_ctsdata.py,
# analyze_ctsdata_to_files.py).
sys.path.insert(0, str(Path(__file__).parent.parent))
from syntaxer_main import _configure_lm  # noqa: E402

from arsgrammatica import (
    CitedText,
    LMCostSummary,
    analyze_sources,
    combined_tokengraph,
    group_passages_by_sentence_boundary,
    read_ctsdata,
    summarize_lm_cost,
    write_analyses,
)


def _approximate_corpus_counts(cited_texts: List[CitedText]) -> Tuple[int, int, List[str]]:
    """Cheap, LM-free stand-ins for the corpus's own total sentence/token
    counts -- no LM call at all, unlike a real `segment_sources()` call
    over the whole corpus (which is what an earlier version of this script
    used instead; see the module docstring for why that was too expensive
    to run just for a count).

    Tokens: a plain whitespace word count across every passage's own raw
    text (`len(text.split())`, summed) -- the same rough measure `wc -w`
    gives on the command line. This is NOT the same notion as the sample's
    own `tokens_analyzed` (real segmentation: one token per word AND one
    per punctuation mark, counted separately -- see `serialization.py`'s
    module docstring): a whitespace split undercounts relative to that,
    since e.g. "cano." is one whitespace-word but two real tokens ("cano",
    "."). Treat any extrapolation built on this count as a rough, likely
    UNDER-estimate for exactly that reason, not an apples-to-apples
    multiplication.

    Sentences: `len(groups)` from `group_passages_by_sentence_boundary()`
    (`passage_grouping.py`) -- the number of passage-groups its own fast,
    per-passage text-ending heuristic finds, with no cross-passage
    reasoning and no LM call at all (see that module's own docstring for
    exactly what it gets wrong: an abbreviation's trailing period misread
    as sentence-final, same as `SegmentPassage`'s own documented
    exception). Using its group COUNT as a sentence count adds one more
    source of error beyond that: a single passage whose own raw text
    already contains more than one complete sentence is still only ONE
    group, so this can UNDER-count whenever a passage isn't exactly one
    sentence -- there's no cheaper way to catch that without segmenting
    for real.

    Returns `(approx_sentences, approx_tokens, warnings)` -- `warnings` is
    whatever `group_passages_by_sentence_boundary()` itself returned (only
    ever the one case of a final group not ending at a sentence boundary),
    for the caller to print or ignore.
    """
    approx_tokens = sum(len(cited_text.text.split()) for cited_text in cited_texts)
    groups, warnings = group_passages_by_sentence_boundary(cited_texts)
    approx_sentences = len(groups)
    return approx_sentences, approx_tokens, warnings


def _log_progress_banner(attempts: int, n: int, accepted_count: int, failed_count: int) -> None:
    """Print a conspicuous, hard-to-miss progress banner to STDERR (never
    stdout -- see this script's own stdout/stderr split, kept so stdout
    carries nothing but `format_report()`'s own lines) every time
    `attempts` completes another full cycle of `n` candidate passages
    tried, successful or not.

    Analyzing one passage is a real, live LM call, and with the
    skip-and-replace failure handling in `estimate_corpus_cost()`,
    `attempts` can climb well past `n` before the sample is actually done
    -- this exists purely as a heartbeat so a long run doesn't look hung,
    not as a diagnostic (see `failed_passages`/`corpus_count_warnings`/
    `write_warnings`, printed separately once the whole run is over, for
    that).
    """
    banner = "=" * 70
    print(
        f"\n{banner}\n"
        f">>> PROGRESS: {attempts} passage(s) tried so far -- "
        f"{accepted_count} accepted, {failed_count} failed "
        f"(need {n} accepted total) <<<\n"
        f"{banner}\n",
        file=sys.stderr,
    )


def _random_order(cited_texts: List[CitedText], rng: Optional[random.Random] = None) -> List[int]:
    """Return a random permutation of every index into `cited_texts` -- the
    order `estimate_corpus_cost()` tries candidate passages in. A full
    permutation (not just `n` indices) so that, if some early candidates
    fail, there are always more untried ones left to fall back to, right
    up until every passage in the corpus has been tried exactly once.

    `rng` is an optional `random.Random` instance (e.g. seeded, for a
    reproducible trial order across runs); omit it for an unseeded
    `random.Random()` of this call's own -- a different order every time.
    """
    rng = rng if rng is not None else random.Random()
    indices = list(range(len(cited_texts)))
    rng.shuffle(indices)
    return indices


class CorpusCostEstimate(NamedTuple):
    """Everything `format_report()` needs to render the report this
    script writes to stdout -- see that function for exactly what each
    field becomes. `failed_passages` and `corpus_count_warnings` aren't
    part of the report itself -- they're diagnostic detail for the caller
    to print or inspect (`__main__` below prints both to stderr):
    `failed_passages` about any passage that was tried and skipped along
    the way, `corpus_count_warnings` about `_approximate_corpus_counts()`'s
    own `group_passages_by_sentence_boundary()` call."""

    n: int
    sentences_analyzed: int
    tokens_analyzed: int
    cost_summary: LMCostSummary
    corpus_sentences_approx: int
    corpus_tokens_approx: int
    corpus_count_warnings: List[str]
    output_path: Path
    write_warnings: List[str]
    failed_passages: List[Tuple[str, str]]


def estimate_corpus_cost(
    cited_texts: List[CitedText],
    n: int,
    output_path: str,
    lm,
    model: Optional[str] = None,
    rng: Optional[random.Random] = None,
) -> CorpusCostEstimate:
    """Get a cheap, LM-free approximation of the corpus's own total
    sentences/tokens (`_approximate_corpus_counts()`), then try passages
    one at a time, in a random order (`_random_order()`), running each
    through its own `analyze_sources([candidate])` call until `n` of them
    have succeeded -- and write their combined analyses to `output_path`
    (`write_analyses()`'s own format -- `model` controls its optional
    `#!lm` block exactly as it does there).

    A candidate whose analysis raises outright (a live LM call can fail in
    many ways: a malformed/unparseable response, a rate limit, a timeout --
    see `utilities/model_bakeoff.py`'s own `_score_program()` for the same
    "that's data about this one item, not a bug in the script" precedent)
    is skipped: its citation and the exception are recorded in the
    returned `failed_passages`, and the NEXT candidate in the random order
    is tried in its place -- so the final sample still always has exactly
    `n` passages in it (`sentences_analyzed`/`tokens_analyzed` reflect only
    those `n`, never anything from a failed attempt). Every candidate is
    tried AT MOST ONCE, whether it succeeds or fails; if the corpus runs
    out of untried passages before `n` have succeeded, this raises
    `RuntimeError` naming how many succeeded, how many failed, and why,
    rather than silently returning fewer than `n`.

    Every `n` attempts (successful or not -- see `_log_progress_banner()`),
    a conspicuous progress banner is printed to stderr, so a long run
    (several real LM calls, possibly stretched further by failed-and-
    replaced passages) doesn't look hung. It's a heartbeat, not part of
    this function's return value or of `format_report()`'s own report.

    Each candidate is analyzed with its OWN `analyze_sources([candidate])`
    call, one passage at a time -- unlike `analyze_ctsdata_to_files.py`'s
    own batched `analyze_sources(cited_texts)` over a whole file at once,
    which lets one sentence run from the end of one passage's text into
    the start of the next. That cross-passage sentence-spanning is
    deliberately given up here: batching several passages into one call is
    exactly what would let one bad response discard however many good
    sentences the OTHER passages in that same batch would otherwise have
    contributed, and would leave no single passage to blame (and retry) in
    its place. Passages that do succeed are still combined into
    `output_path` in the corpus's OWN file order (not the random trial
    order they happened to succeed in), for readability.

    `lm` is the configured `dspy.LM` instance (e.g. `_configure_lm()`'s
    return value) -- its own `.history` is how this function prices the
    sample: `len(lm.history)` is snapshotted once, immediately before the
    first candidate is tried, so only history entries recorded from that
    point on are ever summed (`summarize_lm_cost()`) -- never any LM call
    made before this function was ever called (there's no whole-corpus LM
    call of this function's own anymore for it to also need to exclude --
    see the module docstring). This DOES include whatever a passage that
    ultimately failed still cost before failing (e.g. a billed call that
    came back malformed) -- that's real spend incurred getting to an
    n-passage sample, not overhead to hide from the report.

    Raises `ValueError` immediately -- before any LM call at all -- if `n`
    is negative, or greater than `len(cited_texts)`: there's no way to ever
    reach `n` successes out of a corpus that small even if every passage in
    it succeeded. Propagates `write_analyses()`'s own `ValueError` for a
    field value that can't round-trip through '|'-delimited text.
    """
    if n < 0:
        raise ValueError(f"n must be non-negative; got {n}")
    if n > len(cited_texts):
        raise ValueError(
            f"n ({n}) is greater than the number of passages in the corpus "
            f"({len(cited_texts)})"
        )

    corpus_sentences_approx, corpus_tokens_approx, corpus_count_warnings = (
        _approximate_corpus_counts(cited_texts)
    )

    order = _random_order(cited_texts, rng=rng)

    sample_start = len(lm.history)

    # (original corpus index, sentences, results) per successfully
    # analyzed passage -- kept indexed so the accepted passages can be
    # written back out in the corpus's own file order (see this function's
    # own docstring) regardless of the random order they succeeded in.
    accepted: List[Tuple[int, list, list]] = []
    failed_passages: List[Tuple[str, str]] = []

    attempts = 0
    for index in order:
        if len(accepted) >= n:
            break
        candidate = cited_texts[index]
        attempts += 1
        try:
            candidate_sentences, candidate_results = analyze_sources([candidate])
        except Exception as exc:  # noqa: BLE001 -- a live LM call can fail in many ways (a malformed response, a rate limit, a timeout); that's data about THIS passage, not a bug in this script -- skip it and try another, same convention utilities/model_bakeoff.py's own _score_program() uses for one candidate example failing outright.
            failed_passages.append((candidate.citation, f"{type(exc).__name__}: {exc}"))
        else:
            accepted.append((index, candidate_sentences, candidate_results))

        # A progress heartbeat every n attempts (not n successes -- see
        # _log_progress_banner()'s own docstring), so a long-running sample
        # with several failed-and-replaced passages doesn't look hung.
        if attempts % n == 0:
            _log_progress_banner(attempts, n, len(accepted), len(failed_passages))

    if len(accepted) < n:
        raise RuntimeError(
            f"Could only analyze {len(accepted)} of the {n} requested passages -- "
            f"{len(failed_passages)} passage(s) failed and there were no more "
            f"untried passages left in the corpus ({len(cited_texts)} total). "
            "Failures: "
            + "; ".join(f"{citation!r}: {message}" for citation, message in failed_passages)
        )

    cost_summary = summarize_lm_cost(lm.history[sample_start:])

    accepted.sort(key=lambda item: item[0])
    sentences = [sentence for _, sents, _ in accepted for sentence in sents]
    results = [result for _, _, res in accepted for result in res]

    # Flatten every accepted sentence's own verbalunits/tokengraph into the
    # one flat list write_analyses() expects -- same convention every
    # marimo ctsdata notebook's own "Serialize analysis to file" cell uses
    # (combined_tokengraph() for the tokengraph, a list comprehension for
    # verbalunits, since there's no dedicated flattening helper for those).
    finaltokens = combined_tokengraph(results)
    all_verbalunits = [vu for result in results for vu in result.verbalunits]
    write_warnings = write_analyses(
        sentences,
        all_verbalunits,
        finaltokens,
        output_path,
        model=model,
        reasoning=[result.reasoning for result in results],
    )

    return CorpusCostEstimate(
        n=n,
        sentences_analyzed=len(sentences),
        tokens_analyzed=sum(len(sentence.tokens) for sentence in sentences),
        cost_summary=cost_summary,
        corpus_sentences_approx=corpus_sentences_approx,
        corpus_tokens_approx=corpus_tokens_approx,
        corpus_count_warnings=corpus_count_warnings,
        output_path=Path(output_path),
        write_warnings=write_warnings,
        failed_passages=failed_passages,
    )


def format_report(estimate: CorpusCostEstimate) -> str:
    """Render `estimate` as the one-item-per-line, labelled report this
    script writes to stdout. `estimate.failed_passages` and
    `estimate.corpus_count_warnings` are deliberately NOT part of this
    report (see `__main__` below, which prints both to stderr instead) --
    every line here reflects only the `n` passages that ultimately
    succeeded, plus the corpus-wide approximate counts. Both
    "(approx.)"-labelled corpus lines, and the two estimates built from
    them, come from `_approximate_corpus_counts()` -- a mechanical,
    LM-free stand-in for real segmentation (see that function's own
    docstring for exactly what each one gets wrong).

    "Total cost"/"cost per sentence"/"cost per token" all read "N/A" (with
    a reason) instead of a number whenever `estimate.cost_summary` has no
    priced calls to report at all -- either because every one of the
    sample's own LM calls happened to be served from cache (`total_cost`
    is `None`; see `lm_cost.py`'s own docstring for exactly when that
    happens), or because `n` was 0 (`sentences_analyzed`/`tokens_analyzed`
    both 0, nothing to divide by) -- rather than raising `ZeroDivisionError`
    or silently printing a misleading `$0.00`. The two extrapolated
    estimates at the end are each "N/A" under that same condition, since
    both are built from those same per-unit rates.
    """
    total_cost = estimate.cost_summary.total_cost
    priced = total_cost is not None and estimate.sentences_analyzed > 0 and estimate.tokens_analyzed > 0

    cost_per_sentence = total_cost / estimate.sentences_analyzed if priced else None
    cost_per_token = total_cost / estimate.tokens_analyzed if priced else None

    lines = [
        f"Passages analyzed: {estimate.n}",
        f"Sentences analyzed: {estimate.sentences_analyzed}",
        f"Tokens analyzed: {estimate.tokens_analyzed}",
    ]

    if priced:
        lines.append(f"Total cost: ${total_cost:.4f}")
        lines.append(f"Cost per sentence: ${cost_per_sentence:.6f}")
        lines.append(f"Cost per token: ${cost_per_token:.6f}")
    elif total_cost is None:
        uncosted = estimate.cost_summary.uncosted_calls
        call_word = "call" if uncosted == 1 else "calls"
        reason = (
            f"no LM calls made ({estimate.n} passages sampled)"
            if uncosted == 0
            else f"all {uncosted} LM {call_word} served from cache, no cost recorded"
        )
        lines.append(f"Total cost: N/A ({reason})")
        lines.append("Cost per sentence: N/A")
        lines.append("Cost per token: N/A")
    else:
        lines.append(f"Total cost: ${total_cost:.4f}")
        lines.append("Cost per sentence: N/A (no sentences analyzed)")
        lines.append("Cost per token: N/A (no tokens analyzed)")

    lines.append(f"Sentences in entire corpus (approx.): {estimate.corpus_sentences_approx}")
    lines.append(f"Tokens in entire corpus (approx., word count): {estimate.corpus_tokens_approx}")

    if priced:
        lines.append(
            "Estimated cost (approx. corpus sentences x cost per sentence): "
            f"${cost_per_sentence * estimate.corpus_sentences_approx:.4f}"
        )
        lines.append(
            "Estimated cost (approx. corpus tokens x cost per token): "
            f"${cost_per_token * estimate.corpus_tokens_approx:.4f}"
        )
    else:
        lines.append("Estimated cost (approx. corpus sentences x cost per sentence): N/A")
        lines.append("Estimated cost (approx. corpus tokens x cost per token): N/A")

    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Sample n passages at random from a #!ctsdata (CEX) corpus, fully "
            "analyze just that sample, and report its cost per sentence/token "
            "alongside an estimate of what analyzing the whole corpus would cost."
        )
    )
    parser.add_argument("ctsdata_path", help="Path to a #!ctsdata (CEX) source file.")
    parser.add_argument(
        "-n",
        "--n",
        dest="n",
        type=int,
        default=5,
        help="Number of passages to sample at random (default: %(default)s).",
    )
    parser.add_argument(
        "-o",
        "--output-file",
        default="analyses.cex",
        help="File to write the sampled passages' combined analyses to, in "
             "write_analyses()'s own format (default: %(default)s).",
    )
    parser.add_argument(
        "--delimiter",
        default="|",
        help="Column delimiter used by the SOURCE #!ctsdata file (default '|'). "
             "Does not affect the output analyses file, which always uses '|'.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed the random sample for a reproducible selection across runs "
             "(default: unseeded -- a different sample each run).",
    )
    args = parser.parse_args()

    # Read (and validate) the source file, and check n against its size,
    # before configuring an LM or spending any calls on it -- same
    # fail-fast-and-cheaply convention every other utilities/*.py script
    # that starts from a #!ctsdata file already follows.
    cited_texts = read_ctsdata(args.ctsdata_path, delimiter=args.delimiter)
    if args.n < 1:
        parser.error(f"--n must be at least 1; got {args.n}")
    if args.n > len(cited_texts):
        parser.error(
            f"--n ({args.n}) is greater than the number of passages in "
            f"{args.ctsdata_path!r} ({len(cited_texts)})"
        )

    lm = _configure_lm()
    rng = random.Random(args.seed)

    estimate = estimate_corpus_cost(
        cited_texts, args.n, args.output_file, lm, model=lm.model, rng=rng
    )

    # Diagnostics go to stderr, same stdout/stderr split every other
    # utilities/*.py script in this codebase uses -- so stdout carries
    # nothing but the report itself.
    for citation, message in estimate.failed_passages:
        print(f"Skipped passage {citation!r} after a failed analysis: {message}", file=sys.stderr)
    if estimate.failed_passages:
        print(
            f"{len(estimate.failed_passages)} passage(s) failed analysis and were "
            "each replaced with another randomly-chosen passage from the corpus.",
            file=sys.stderr,
        )
    for w in estimate.corpus_count_warnings:
        print(f"Warning (approximate corpus counts): {w}", file=sys.stderr)
    for w in estimate.write_warnings:
        print(f"Warning ({estimate.output_path}): {w}", file=sys.stderr)
    print(f"Wrote {estimate.output_path}", file=sys.stderr)

    print(format_report(estimate))
