"""
Orchestrates the two-stage pipeline: segmentation_dspy.py's citation-aware
sentence/token segmentation, feeding latin_syntax_dspy.py's unmodified
SentenceAnalysis one sentence at a time.
 
Kept as its own module, separate from both stages, so neither stage needs
to know the other exists -- segmentation_dspy.py doesn't import
latin_syntax_dspy.py or vice versa. This is the only place that does.
"""
 
import sys
from typing import Callable, List, Optional, Tuple

from .models import CitedText, Sentence
from .segmentation_dspy import segment_sources
from .latin_syntax_dspy import validate
from .token_budget import analyze_with_retry
from .token_ids import assign_passage_scoped_ids
from .ctsdata import read_ctsdata
 
 
def _render_sentence_text(sentence: Sentence) -> str:
    """Reconstruct a surface string for a sentence from its tokens, to pass
    as SentenceAnalysis's `passage` field.
 
    This is an approximation, not a faithful re-rendering: it puts a space
    before every token, including punctuation and enclitics (so "tres."
    round-trips as "tres ." and "virumque" as "virum que"). SentenceAnalysis
    uses `passage` for readability alongside the authoritative `tokens`
    list, not for anything validate() checks, so exact fidelity isn't
    required -- but don't reuse this helper anywhere that *does* need
    faithful surface text without tightening it first.
    """
    return " ".join(tok.text for tok in sentence.tokens)
 
 
def analyze_sources(
    sources: List[CitedText],
    *,
    progress_callback: Optional[Callable[[int, int, Sentence], None]] = None,
    on_sentence_error: Optional[Callable[[Sentence, Exception], None]] = None,
) -> Tuple[List[Sentence], list]:
    """Segment `sources` into citation-aware sentences, run each sentence's
    tokens through SentenceAnalysis, and validate each result.

    Returns (sentences, results): results[i] is the SentenceAnalysis result
    for sentences[i], same order, one entry per sentence.

    Each sentence's SentenceAnalysis call goes through
    `token_budget.analyze_with_retry()` rather than calling `analyze()`
    directly, so a sentence whose analysis needs more output than a fixed
    `max_tokens` would allow (a long or deeply subordinated sentence) gets
    an estimated, appropriately-sized budget up front, and a retry with a
    larger one if it still comes back truncated -- see token_budget.py's
    module docstring for the full design.

    `progress_callback`, if given, is called as `progress_callback(index,
    total, sentence)` immediately BEFORE each sentence's own
    SentenceAnalysis call starts -- `index` is that sentence's own 0-based
    position, `total` is `len(sentences)` (already known at that point,
    since segmentation has already finished), and `sentence` is that
    Sentence itself (e.g. for its own first token's citation, to report
    something more specific than a bare counter). This is purely a
    reporting hook for a caller that wants to show progress across a
    potentially long run of per-sentence LM calls -- see
    `utilities/analyze_ctsdata_to_files.py`'s own use of it -- and never
    affects this function's own behavior; omitted (the default), this
    function's return value and every other observable effect are exactly
    as they were before this parameter existed.

    `on_sentence_error`, if given, is called as `on_sentence_error(sentence,
    exc)` whenever that one sentence's own `analyze_with_retry()` call
    raises -- even after that function's own retries are exhausted --
    instead of letting the exception propagate out of THIS call entirely.
    That one sentence is then left out of both returned lists (`sentences`
    and `results` stay parallel and the same length as each other, just
    possibly shorter than `segment_sources()`'s own output, by however many
    sentences failed); every OTHER sentence in `sources` -- including ones
    segmented into the SAME call as the one that failed -- still gets
    analyzed normally. Omitted (the default, `None`), this function's
    behavior is exactly what it always was: a failing sentence's exception
    propagates immediately, and this call returns nothing at all. Existing
    callers that don't pass it (`analyze_string()`,
    `analyze_selected_passages()`, `analyze_ctsdata()`, `syntaxer_main.py`,
    every marimo notebook) are unaffected by this parameter's existence --
    that's the right default for a single hand-typed passage in an
    interactive session, where the real exception should surface right
    away rather than being swallowed into a report nobody's watching yet.
    Only a script wide enough to want to survive one bad passage out of
    many should pass this -- see `utilities/analyze_ctsdata_to_files.py`'s
    own use of it, and `arsgrammatica.FailedPassage`/`write_warnings_report()`
    for a ready-made way to collect and report what it catches.

    Before any SentenceAnalysis call, every token whose citation is a CTS
    URN (`token_ids.assign_passage_scoped_ids()`) has its id rewritten to a
    passage-scoped composite id (e.g. `1.1.t0`) instead of whatever bare id
    `segment_sources()` gave it. This makes a given passage's own tokens
    get the SAME ids every time it's analyzed, regardless of what other
    passages happened to be segmented alongside it in this particular
    call -- which in turn means the SentenceAnalysis prompt for that
    passage is identical across runs/callers, so DSPy's own LM response
    cache can actually be shared between them (see that module's own
    docstring for the full rationale). A token with no citation, or a
    citation that isn't a 5-part CTS URN, keeps whatever id
    `segment_sources()` assigned it.
    """
    sentences = assign_passage_scoped_ids(segment_sources(sources))

    kept_sentences = []
    results = []
    for index, sentence in enumerate(sentences):
        if progress_callback is not None:
            progress_callback(index, len(sentences), sentence)

        try:
            result = analyze_with_retry(passage=_render_sentence_text(sentence), tokens=sentence.tokens)
        except Exception as exc:
            if on_sentence_error is None:
                raise
            on_sentence_error(sentence, exc)
            continue

        problems = validate(sentence.tokens, result)
        if problems:
            first_id = sentence.tokens[0].id if sentence.tokens else "?"
            # To stderr, not stdout -- same convention every CLI script
            # built on this function keeps for its OWN output (e.g.
            # utilities/analyze_ctsdata_to_files.py's "Wrote ..." lines),
            # so a problem surfacing here can never corrupt a caller's own
            # piped/redirected stdout.
            print(f"Validation warnings (sentence starting at {first_id}):", file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)

        kept_sentences.append(sentence)
        results.append(result)

    return kept_sentences, results
 
 
def combined_tokengraph(results) -> list:
    """Concatenate every sentence result's tokengraph, in order, into one
    flat list spanning the whole input -- since token ids are global,
    tokengraph_to_mermaid() (mermaid.py) needs no changes at all to render
    this as one diagram for a multi-sentence, multi-citation passage."""
    combined = []
    for result in results:
        combined.extend(result.tokengraph)
    return combined
 
 
def analyze_string(passage: str, citation: str = "") -> Tuple[List[Sentence], list]:
    """Convenience wrapper for the common case of a single string rather
    than a list of citation-labeled CitedText sources -- kept here so
    existing callers (syntaxer_main.py, the marimo notebook) have a
    one-string entry point rather than needing to build a CitedText list
    themselves for the ordinary case of one passage from one source.
 
    Wraps `passage` as one CitedText (using `citation` if given, else an
    empty string -- fine for callers that don't track citations) and runs
    it through analyze_sources(). Returns (sentences, results) -- the exact
    same shape analyze_sources() returns, one entry per sentence
    segmentation finds in `passage`, in order.
 
    `passage` may contain any number of sentences: each is segmented and
    analyzed successively, same as if you'd called analyze_sources() with
    one CitedText yourself. (An earlier version of this function raised
    ValueError on multi-sentence input and returned a single (tokens,
    result) pair for exactly one sentence; callers written against that
    contract need to change to unpack (sentences, results) and iterate.)
    """
    return analyze_sources([CitedText(citation=citation, text=passage)])


def analyze_selected_passages(
    passage_ids: List[str], cited_texts: List[CitedText]
) -> Tuple[List[Sentence], list]:
    """Select the entries of `cited_texts` whose `citation` is in
    `passage_ids`, then run exactly those through analyze_sources() --
    e.g. after read_ctsdata() has loaded a whole source file but only some
    of its passages are wanted for this run.

    Selected passages are analyzed in `cited_texts`' OWN order, not
    `passage_ids`' order -- the same convention
    marimo/latin_syntaxer_ctsdata.py's own `selected_rows` cell already
    uses, and for the same reason: segment_sources() (inside
    analyze_sources()) treats consecutive sources as potentially sharing a
    sentence, so an out-of-file-order source list could segment
    incorrectly, or produce citations in a confusing order.
    `passage_ids` therefore acts purely as a filter -- which passages to
    include -- never as a sort key.

    Raises ValueError, naming every missing id at once, if any entry of
    `passage_ids` doesn't match any `cited_texts` citation -- a typo'd or
    stale passage id fails loudly here rather than silently analyzing
    fewer passages than asked for.

    Returns (sentences, results) -- the exact same shape analyze_sources()
    returns, spanning only the selected passages.
    """
    wanted = set(passage_ids)
    selected = [ct for ct in cited_texts if ct.citation in wanted]

    found = {ct.citation for ct in selected}
    missing = sorted(pid for pid in wanted if pid not in found)
    if missing:
        raise ValueError(
            f"passage id(s) not found in cited_texts: {missing!r}"
        )

    return analyze_sources(selected)


def analyze_ctsdata(path: str, delimiter: str = "|") -> Tuple[List[Sentence], list]:
    """Convenience wrapper for the common case of a whole `#!ctsdata` (CEX)
    source file on disk, rather than an in-memory `List[CitedText]` --
    reads `path` with `read_ctsdata()` (ctsdata.py) and runs the result
    straight through `analyze_sources()`, the same "read a CEX corpus,
    then analyze it" pair every entry point in this codebase that starts
    from a CEX file already does by hand (`utilities/tokenize_ctsdata.py`,
    `utilities/analyze_ctsdata_to_files.py`, `utilities/
    group_ctsdata_by_sentence.py`, each of the marimo ctsdata notebooks).

    `delimiter` is passed straight through to `read_ctsdata()` -- it's the
    SOURCE file's own column delimiter ('|' by default, matching every
    other serialized format in this codebase), not related to anything
    `analyze_sources()` itself does.

    Returns `(sentences, results)` -- the exact same shape
    `analyze_sources()` returns, spanning every passage in `path`, in the
    file's own order. Every passage in the file is analyzed; use
    `analyze_selected_passages()` instead if only some of them are wanted.

    Propagates `read_ctsdata()`'s own `ValueError`/`OSError` as-is for a
    missing file or a malformed `#!ctsdata` block (see that function's own
    docstring for exactly what's checked) -- raised before any LM call is
    made, same as every CLI entry point that reads a CEX file up front for
    the same reason.
    """
    cited_texts = read_ctsdata(path, delimiter=delimiter)
    return analyze_sources(cited_texts)
