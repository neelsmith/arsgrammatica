"""
Gold-annotated examples for the segmentation stage (segmentation_dspy.py) --
the segmentation-stage counterpart to fixtures/gold_examples.py.
 
Each SegmentationExample pairs a list of CitedText sources with the
sentences/tokens a *correctly working* context-aware segmenter should
produce. Like fixtures/gold_examples.py, these are structural fixtures:
running them through DummyLM proves the code (models, segment_sources()
plumbing) handles a well-formed, correct answer properly. It does NOT
prove a real LM produces that answer -- see test_segmentation_live.py for
that half of the picture, which hits the actual configured LM instead of
DummyLM and is skipped by default (opt in with `pytest -m live`).
 
These three examples are exactly the gaps the old deterministic tokenizer
(tokenizer.py, since retired) got wrong: false-positive enclitic splitting
on real words, the genuinely context-dependent -ne case, and abbreviation
recognition. Same scenarios, now specified for the new pipeline instead.
"""
 
from dataclasses import dataclass
from typing import Any
 
from arsgrammatica.models import CitedText
 
 
@dataclass
class SegmentationExample:
    slug: str
    sources: list[CitedText]
    tags: list[str]
    canned_sentences: dict[str, Any]
 
 
SEGMENTATION_EXAMPLES = [
    SegmentationExample(
        slug="enclitic_no_false_positive_sine_bene",
        sources=[
            CitedText(citation="ex.1", text="sine ira et studio."),
            CitedText(citation="ex.2", text="bene vixit."),
        ],
        tags=["enclitic false-positive guard"],
        canned_sentences={
            "reasoning": (
                "sine and bene are real words on their own; nothing about "
                "them is enclitic, so neither is split."
            ),
            "sentences": [
                {"tokens": [
                    {"id": "t0", "text": "sine", "citation": "ex.1"},
                    {"id": "t1", "text": "ira", "citation": "ex.1"},
                    {"id": "t2", "text": "et", "citation": "ex.1"},
                    {"id": "t3", "text": "studio", "citation": "ex.1"},
                    {"id": "t4", "text": ".", "citation": "ex.1"},
                ]},
                {"tokens": [
                    {"id": "t5", "text": "bene", "citation": "ex.2"},
                    {"id": "t6", "text": "vixit", "citation": "ex.2"},
                    {"id": "t7", "text": ".", "citation": "ex.2"},
                ]},
            ],
        },
    ),
    SegmentationExample(
        slug="ratione_enclitic_split_depends_on_context",
        sources=[
            CitedText(citation="ex.3", text="aequa ratione imperat."),
            CitedText(citation="ex.4", text="ratione docet?"),
        ],
        tags=["context-dependent enclitic split"],
        canned_sentences={
            "reasoning": (
                "In ex.3, ratione is ablative of ratio, mid-sentence, not a "
                "question: stays whole. In ex.4, ratione is sentence-initial "
                "in a question: splits into ratio (nominative) + the "
                "interrogative enclitic -ne."
            ),
            "sentences": [
                {"tokens": [
                    {"id": "t0", "text": "aequa", "citation": "ex.3"},
                    {"id": "t1", "text": "ratione", "citation": "ex.3"},
                    {"id": "t2", "text": "imperat", "citation": "ex.3"},
                    {"id": "t3", "text": ".", "citation": "ex.3"},
                ]},
                {"tokens": [
                    {"id": "t4", "text": "ratio", "citation": "ex.4"},
                    {"id": "t5", "text": "ne", "citation": "ex.4"},
                    {"id": "t6", "text": "docet", "citation": "ex.4"},
                    {"id": "t7", "text": "?", "citation": "ex.4"},
                ]},
            ],
        },
    ),
    SegmentationExample(
        slug="abbreviations_stay_one_token",
        sources=[
            CitedText(citation="ex.5", text="M. Agrippa L. f. cos. tertium fecit."),
        ],
        tags=["abbreviation recognition", "praenomen"],
        canned_sentences={
            "reasoning": (
                "M. and L. are praenomina; f. (filius) and cos. (consul) are "
                "other abbreviations. All four keep their period glued on as "
                "one token, unlike the sentence-final period."
            ),
            "sentences": [
                {"tokens": [
                    {"id": "t0", "text": "M.", "citation": "ex.5"},
                    {"id": "t1", "text": "Agrippa", "citation": "ex.5"},
                    {"id": "t2", "text": "L.", "citation": "ex.5"},
                    {"id": "t3", "text": "f.", "citation": "ex.5"},
                    {"id": "t4", "text": "cos.", "citation": "ex.5"},
                    {"id": "t5", "text": "tertium", "citation": "ex.5"},
                    {"id": "t6", "text": "fecit", "citation": "ex.5"},
                    {"id": "t7", "text": ".", "citation": "ex.5"},
                ]},
            ],
        },
    ),
]
 