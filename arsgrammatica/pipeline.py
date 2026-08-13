"""
Orchestrates the two-stage pipeline: segmentation_dspy.py's citation-aware
sentence/token segmentation, feeding latin_syntax_dspy.py's unmodified
SyntaxAnalysis one sentence at a time.
 
Kept as its own module, separate from both stages, so neither stage needs
to know the other exists -- segmentation_dspy.py doesn't import
latin_syntax_dspy.py or vice versa. This is the only place that does.
"""
 
from typing import List, Tuple
 
from .models import CitedText, Sentence
from .segmentation_dspy import segment_sources
from .latin_syntax_dspy import analyze, validate
 
 
def _render_sentence_text(sentence: Sentence) -> str:
    """Reconstruct a surface string for a sentence from its tokens, to pass
    as SyntaxAnalysis's `passage` field.
 
    This is an approximation, not a faithful re-rendering: it puts a space
    before every token, including punctuation and enclitics (so "tres."
    round-trips as "tres ." and "virumque" as "virum que"). SyntaxAnalysis
    uses `passage` for readability alongside the authoritative `tokens`
    list, not for anything validate() checks, so exact fidelity isn't
    required -- but don't reuse this helper anywhere that *does* need
    faithful surface text without tightening it first.
    """
    return " ".join(tok.text for tok in sentence.tokens)
 
 
def analyze_sources(sources: List[CitedText]) -> Tuple[List[Sentence], list]:
    """Segment `sources` into citation-aware sentences, run each sentence's
    tokens through SyntaxAnalysis, and validate each result.
 
    Returns (sentences, results): results[i] is the SyntaxAnalysis result
    for sentences[i], same order, one entry per sentence.
    """
    sentences = segment_sources(sources)
 
    results = []
    for sentence in sentences:
        result = analyze(passage=_render_sentence_text(sentence), tokens=sentence.tokens)
 
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