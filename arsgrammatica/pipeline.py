"""
Orchestrates the two-stage pipeline: segmentation_dspy.py's citation-aware
sentence/token segmentation, feeding latin_syntax_dspy.py's unmodified
SentenceAnalysis one sentence at a time.
 
Kept as its own module, separate from both stages, so neither stage needs
to know the other exists -- segmentation_dspy.py doesn't import
latin_syntax_dspy.py or vice versa. This is the only place that does.
"""
 
from typing import List, Tuple
 
from .models import CitedText, Sentence
from .segmentation_dspy import segment_sources
from .latin_syntax_dspy import validate
from .token_budget import analyze_with_retry
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
 
 
def analyze_sources(sources: List[CitedText]) -> Tuple[List[Sentence], list]:
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
    """
    sentences = segment_sources(sources)

    results = []
    for sentence in sentences:
        result = analyze_with_retry(passage=_render_sentence_text(sentence), tokens=sentence.tokens)
 
        problems = validate(sentence.tokens, result)
        if problems:
            first_id = sentence.tokens[0].id if sentence.tokens else "?"
            print(f"Validation warnings (sentence starting at {first_id}):")
            for p in problems:
                print(f"  - {p}")
 
        results.append(result)
 
    return sentences, results
 
 
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
