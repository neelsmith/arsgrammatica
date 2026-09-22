"""
A small shared report for the multi-passage analysis scripts
(`utilities/analyze_ctsdata_to_files.py`, `utilities/
analyze_tokendata_to_files.py`, `utilities/analyze_w_diagrams.py`,
`utilities/analyze_tokendata_w_diagrams.py`): when one passage's own
SentenceAnalysis call fails outright -- raises, even after
`token_budget.analyze_with_retry()`'s own retries are exhausted -- that one
passage is now skipped rather than aborting the whole run (see
`pipeline.analyze_sources()`'s own `on_sentence_error` parameter, and each
of those scripts' own per-sentence/per-group try/except). This module gives
every one of them the same place to report which passages that happened
to, and what the whole run's LM calls cost in total, as one file
(conventionally `<output_dir>/warnings.txt`) rather than each inventing its
own ad-hoc report.

Deliberately distinct from `write_analyses()`'s own "warnings" (e.g. a
boundary-token mismatch on an otherwise-successful analysis, which still
gets written to its own output file -- see `serialization.py`'s module
docstring) and from `validate()`'s own "problems" (a referential issue in
an otherwise-parsed result) -- both of THOSE stay exactly where they
already were, printed to stderr per file/sentence, since the analysis in
question still produced something real. A `FailedPassage` here means the
opposite: no analysis, no output file, nothing for `validate()` to even
look at -- only a description of which passage it was and the exception
that stopped it cold.

Usage (see any of the four scripts named above):

    from arsgrammatica import FailedPassage, write_warnings_report

    failed: List[FailedPassage] = []
    ...
    failed.append(FailedPassage(description, str(exc)))
    ...
    warnings_path = write_warnings_report(Path(output_dir) / "warnings.txt", failed, lm.history)
    print(f"Wrote {warnings_path}")
"""

from pathlib import Path
from typing import List, NamedTuple, Union

from .lm_cost import format_lm_cost, summarize_lm_cost


class FailedPassage(NamedTuple):
    """One passage a multi-passage analysis script never managed to
    analyze at all.

    `description` is a short, human-readable label for which one -- e.g.
    "sentence starting at 'urn:cts:...:1.1'", optionally prefixed with an
    input file's own stem for a multi-file script (`analyze_tokendata_to_files.py`'s
    own convention), or "passage 'urn:cts:...:1.1'" for a whole CTS passage
    whose GROUP failed before it was even segmented into sentences
    (`analyze_ctsdata_to_files.py`'s own group-level fallback -- see that
    module's docstring). `error` is `str(exc)` for whatever exception
    ultimately stopped it: `token_budget.analyze_with_retry()`'s own,
    once its retries are exhausted, for a single sentence; `segment_sources()`'s
    own, for a whole group that never got that far."""

    description: str
    error: str


def format_warnings_report(failed: List[FailedPassage], lm_history: List) -> str:
    """Render `failed` plus `lm_history`'s own total cost
    (`lm_cost.summarize_lm_cost()`/`format_lm_cost()`) as one short,
    human-readable report -- see this module's own docstring for what
    "failed" means here specifically (not `write_analyses()`'s or
    `validate()`'s own, unrelated notions of "warnings"/"problems", which
    this report never repeats).

    Always ends with a cost line, and always says explicitly when there
    were no failures at all rather than leaving that to be inferred from
    an empty list -- matching the "always prints, no flag to suppress"
    convention `format_lm_cost()`'s own callers already follow for the
    same total, so a clean run and a run that never happened both leave
    behind an unambiguous file instead of requiring the reader to already
    know "no failure lines means it went fine".
    """
    lines: List[str] = []
    if failed:
        word = "passage" if len(failed) == 1 else "passages"
        lines.append(f"{len(failed)} {word} failed to analyze:")
        for fp in failed:
            lines.append(f"  - {fp.description}: {fp.error}")
    else:
        lines.append("No passages failed to analyze.")

    lines.append("")
    lines.append(f"LM cost: {format_lm_cost(summarize_lm_cost(lm_history))}")
    return "\n".join(lines) + "\n"


def write_warnings_report(
    path: Union[str, Path], failed: List[FailedPassage], lm_history: List
) -> Path:
    """Write `format_warnings_report(failed, lm_history)` to `path`
    (created, or overwritten if it already exists), returning `path` as a
    `Path` -- so a caller can print its own "Wrote ..." line the same way
    it already does for every other output file, e.g.:

        warnings_path = write_warnings_report(out_dir / "warnings.txt", failed, lm.history)
        print(f"Wrote {warnings_path}")
    """
    out_path = Path(path)
    out_path.write_text(format_warnings_report(failed, lm_history), encoding="utf-8")
    return out_path
