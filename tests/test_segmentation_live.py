"""
Live counterpart to test_segmentation_examples.py: runs the same three
scenarios against the actual configured LM (via the `real_lm` fixture in
conftest.py) instead of DummyLM.
 
This is the half of the picture DummyLM tests structurally cannot cover --
whether the LM itself actually performs the context-dependent segmentation
correctly, not just whether the code can represent a correct answer. Costs
real API calls, so it's marked `live` and skipped by default; run it with:
 
    pytest -m live tests/test_segmentation_live.py
 
I have not been able to run this against your configured model myself --
verify it once against the real thing before trusting these three gaps are
actually closed, not just well-specified.
"""
 
import pytest
 
from arsgrammatica.models import CitedText
from arsgrammatica.segmentation_dspy import segment_sources
 
pytestmark = pytest.mark.live
 
 
def _texts(sentence):
    return [t.text for t in sentence.tokens]
 
 
def test_live_sine_is_not_split(real_lm):
    sentences = segment_sources([CitedText(citation="ex.1", text="sine ira et studio.")])
    assert _texts(sentences[0]) == ["sine", "ira", "et", "studio", "."]
 
 
def test_live_bene_is_not_split(real_lm):
    sentences = segment_sources([CitedText(citation="ex.2", text="bene vixit.")])
    assert _texts(sentences[0]) == ["bene", "vixit", "."]
 
 
def test_live_ratione_ablative_reading_stays_whole(real_lm):
    sentences = segment_sources([CitedText(citation="ex.3", text="aequa ratione imperat.")])
    assert _texts(sentences[0]) == ["aequa", "ratione", "imperat", "."]
 
 
def test_live_ratione_interrogative_reading_splits(real_lm):
    sentences = segment_sources([CitedText(citation="ex.4", text="ratione docet?")])
    assert _texts(sentences[0]) == ["ratio", "ne", "docet", "?"]
 
 
def test_live_abbreviations_stay_one_token(real_lm):
    sentences = segment_sources(
        [CitedText(citation="ex.5", text="M. Agrippa L. f. cos. tertium fecit.")]
    )
    assert _texts(sentences[0]) == [
        "M.", "Agrippa", "L.", "f.", "cos.", "tertium", "fecit", ".",
    ]

 