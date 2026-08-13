"""
DummyLM-backed tests for the segmentation stage (segmentation_dspy.py),
including citation tracking, plus one end-to-end check that its output
composes with the *existing, unmodified* SyntaxAnalysis.
"""
 
import re
 
import dspy
from dspy.utils.dummies import DummyLM
 
from arsgrammatica import analyze, validate
from arsgrammatica.models import CitedText
from arsgrammatica.segmentation_dspy import segment_sources
from fixtures.gold_examples import GOLD_EXAMPLES
 
 
def _shift_ids(obj, offset):
    """Recursively shift every 't<N>' id-shaped string in obj by offset.
    Used below to reuse the existing unit_verb_hercules_cum gold fixture as
    if it were a later sentence in a longer input, without hand-retyping
    every id. Citation strings like "Aeneid 1.1" never match t<N>, so this
    is safe to run over a whole canned answer unconditionally."""
    if isinstance(obj, dict):
        return {k: _shift_ids(v, offset) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_shift_ids(v, offset) for v in obj]
    if isinstance(obj, str) and re.fullmatch(r"t\d+", obj):
        return f"t{int(obj[1:]) + offset}"
    return obj
 
 
# ---------------------------------------------------------------------------
# Single citation unit, two sentences: re-checks global sequential ids
# across sentence boundaries (from before), now under the sources: List[
# CitedText] contract, and confirms every token still carries its citation.
# ---------------------------------------------------------------------------
 
SOURCES_ONE_UNIT = [
    CitedText(
        citation="Caesar, BG 1.1",
        text=(
            "Gallia est omnis divisa in partes tres. "
            "Hercules cum gregem perlustrasset, pergit ad proximam speluncam."
        ),
    ),
]
 
CANNED_ONE_UNIT = {
    "reasoning": "Two sentences from one citation unit; ids run continuously across both.",
    "sentences": [
        {"tokens": [
            {"id": "t0", "text": "Gallia", "citation": "Caesar, BG 1.1"},
            {"id": "t1", "text": "est", "citation": "Caesar, BG 1.1"},
            {"id": "t2", "text": "omnis", "citation": "Caesar, BG 1.1"},
            {"id": "t3", "text": "divisa", "citation": "Caesar, BG 1.1"},
            {"id": "t4", "text": "in", "citation": "Caesar, BG 1.1"},
            {"id": "t5", "text": "partes", "citation": "Caesar, BG 1.1"},
            {"id": "t6", "text": "tres", "citation": "Caesar, BG 1.1"},
            {"id": "t7", "text": ".", "citation": "Caesar, BG 1.1"},
        ]},
        {"tokens": [
            {"id": "t8", "text": "Hercules", "citation": "Caesar, BG 1.1"},
            {"id": "t9", "text": "cum", "citation": "Caesar, BG 1.1"},
            {"id": "t10", "text": "gregem", "citation": "Caesar, BG 1.1"},
            {"id": "t11", "text": "perlustrasset", "citation": "Caesar, BG 1.1"},
            {"id": "t12", "text": ",", "citation": "Caesar, BG 1.1"},
            {"id": "t13", "text": "pergit", "citation": "Caesar, BG 1.1"},
            {"id": "t14", "text": "ad", "citation": "Caesar, BG 1.1"},
            {"id": "t15", "text": "proximam", "citation": "Caesar, BG 1.1"},
            {"id": "t16", "text": "speluncam", "citation": "Caesar, BG 1.1"},
            {"id": "t17", "text": ".", "citation": "Caesar, BG 1.1"},
        ]},
    ],
}
 
 
def test_segmentation_round_trips_with_globally_unique_sequential_ids():
    dspy.configure(lm=DummyLM([CANNED_ONE_UNIT]))
    sentences = segment_sources(SOURCES_ONE_UNIT)
 
    assert len(sentences) == 2
    assert [t.id for t in sentences[0].tokens] == [f"t{i}" for i in range(0, 8)]
    assert [t.id for t in sentences[1].tokens] == [f"t{i}" for i in range(8, 18)]
 
    all_ids = [t.id for s in sentences for t in s.tokens]
    assert len(all_ids) == len(set(all_ids)), "token ids must be unique across the whole input"
 
    assert all(t.citation == "Caesar, BG 1.1" for s in sentences for t in s.tokens)
 
 
def test_segmented_sentence_feeds_unmodified_syntax_analysis():
    """The point of keeping segmentation as a separate stage: its output
    (a Sentence's tokens) must work as SyntaxAnalysis's input with zero
    changes to SyntaxAnalysis -- even though its tokens now carry a
    citation field SyntaxAnalysis has never heard of."""
    dspy.configure(lm=DummyLM([CANNED_ONE_UNIT]))
    sentences = segment_sources(SOURCES_ONE_UNIT)
    hercules_sentence = sentences[1]
 
    hercules_gold = next(e for e in GOLD_EXAMPLES if e.slug == "unit_verb_hercules_cum")
    shifted_answer = _shift_ids(hercules_gold.canned_answer, offset=8)
 
    dspy.configure(lm=DummyLM([shifted_answer]))
    result = analyze(passage=hercules_gold.passage, tokens=hercules_sentence.tokens)
 
    problems = validate(hercules_sentence.tokens, result)
    assert not problems, problems
    assert result.tokengraph[0].id == "t8"  # Hercules, at its shifted global id
 
 
# ---------------------------------------------------------------------------
# The actual point of citation tracking: one sentence spanning two citation
# units (Aeneid 1.1-1.2), each token still correctly attributed.
# ---------------------------------------------------------------------------
 
SOURCES_SPANNING_TWO_UNITS = [
    CitedText(citation="Aeneid 1.1", text="Arma virumque canō, Trōiae quī prīmus ab ōrīs"),
    CitedText(citation="Aeneid 1.2", text="Ītaliam, fātō profugus, Lāvīniaque vēnit"),
]
 
CANNED_SPANNING_TWO_UNITS = {
    "reasoning": (
        "One sentence continues from Aeneid 1.1 into 1.2; ids stay global "
        "and each token keeps the citation of the source unit it came from."
    ),
    "sentences": [
        {"tokens": [
            {"id": "t0", "text": "Arma", "citation": "Aeneid 1.1"},
            {"id": "t1", "text": "virum", "citation": "Aeneid 1.1"},
            {"id": "t2", "text": "que", "citation": "Aeneid 1.1"},
            {"id": "t3", "text": "canō", "citation": "Aeneid 1.1"},
            {"id": "t4", "text": ",", "citation": "Aeneid 1.1"},
            {"id": "t5", "text": "Trōiae", "citation": "Aeneid 1.1"},
            {"id": "t6", "text": "quī", "citation": "Aeneid 1.1"},
            {"id": "t7", "text": "prīmus", "citation": "Aeneid 1.1"},
            {"id": "t8", "text": "ab", "citation": "Aeneid 1.1"},
            {"id": "t9", "text": "ōrīs", "citation": "Aeneid 1.1"},
            {"id": "t10", "text": "Ītaliam", "citation": "Aeneid 1.2"},
            {"id": "t11", "text": ",", "citation": "Aeneid 1.2"},
            {"id": "t12", "text": "fātō", "citation": "Aeneid 1.2"},
            {"id": "t13", "text": "profugus", "citation": "Aeneid 1.2"},
            {"id": "t14", "text": ",", "citation": "Aeneid 1.2"},
            {"id": "t15", "text": "Lāvīnia", "citation": "Aeneid 1.2"},
            {"id": "t16", "text": "que", "citation": "Aeneid 1.2"},
            {"id": "t17", "text": "vēnit", "citation": "Aeneid 1.2"},
        ]},
    ],
}
 
 
def test_one_sentence_spanning_two_citation_units_keeps_each_token_attributed():
    dspy.configure(lm=DummyLM([CANNED_SPANNING_TWO_UNITS]))
    sentences = segment_sources(SOURCES_SPANNING_TWO_UNITS)
 
    # It's one sentence, not two -- the whole point of the example.
    assert len(sentences) == 1
    tokens = sentences[0].tokens
 
    # ids stay globally sequential and unique even though this sentence
    # crosses a citation-unit boundary.
    assert [t.id for t in tokens] == [f"t{i}" for i in range(18)]
    assert len({t.id for t in tokens}) == 18
 
    # Each half of the sentence is attributed to its own source unit.
    assert [t.citation for t in tokens[:10]] == ["Aeneid 1.1"] * 10
    assert [t.citation for t in tokens[10:]] == ["Aeneid 1.2"] * 8
 
    # The exact crossover point: "ōrīs" (end of 1.1) into "Ītaliam" (start
    # of 1.2), still one continuous sentence with no gap or reset in ids.
    assert tokens[9].text == "ōrīs" and tokens[9].citation == "Aeneid 1.1"
    assert tokens[10].text == "Ītaliam" and tokens[10].citation == "Aeneid 1.2"
    assert tokens[10].id == "t10"