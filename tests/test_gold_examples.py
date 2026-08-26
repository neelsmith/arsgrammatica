
"""
Runs every fixture in fixtures/gold_examples.py through the real pipeline
(analyze() backed by DummyLM, not a live model) and checks that:
 
- validate() finds no referential-integrity problems, and
- tokengraph_to_mermaid() renders every non-punctuation token as a node,
  with no warnings.
 
This is a structural check, not an accuracy check: it confirms the code
handles each gold answer correctly, not that a real LM would produce that
answer. Add new fixtures to fixtures/gold_examples.py, not here -- these
tests are parametrized over GOLD_EXAMPLES and need no changes to cover a
new sentence.
"""
 
import pytest

from arsgrammatica import validate, tokengraph_to_mermaid
from arsgrammatica.models import IMPLIED_TOKENTYPES
from conftest import run_gold_example
from fixtures.gold_examples import GOLD_EXAMPLES
 
 
def _example(slug):
    return next(e for e in GOLD_EXAMPLES if e.slug == slug)
 
 
@pytest.mark.parametrize("example", GOLD_EXAMPLES, ids=lambda e: e.slug)
def test_gold_example_validates(example):
    tokens, result = run_gold_example(example)
    problems = validate(tokens, result)
    assert not problems, f"{example.slug}: {problems}"
 
 
@pytest.mark.parametrize("example", GOLD_EXAMPLES, ids=lambda e: e.slug)
def test_gold_example_renders_mermaid(example):
    tokens, result = run_gold_example(example)
    diagram, warnings = tokengraph_to_mermaid(result.tokengraph)
    assert not warnings, f"{example.slug}: {warnings}"
    for tok in result.tokengraph:
        if tok.tokentype == "punctuation":
            continue
        # An implied/elided token (IMPLIED_TOKENTYPES) is drawn as a
        # rounded-corner rectangle (Mermaid's `(...)` node shape), not the
        # plain `[...]` rectangle every other node uses -- see mermaid.py's
        # own module docstring.
        open_bracket = "(" if tok.tokentype in IMPLIED_TOKENTYPES else "["
        assert f'{tok.id}{open_bracket}"' in diagram, f"{example.slug}: missing node for {tok.id}"
 
 
# --- Spot-checks specific to one gold example -------------------------------
# The parametrized tests above are deliberately generic (they have to hold
# for every fixture); a few hand-picked assertions about *this* sentence's
# expected edges are worth keeping too, same as the original test_pipeline.py
# did for its one fixture.
 
def test_hercules_specific_edges():
    tokens, result = run_gold_example(_example("unit_verb_hercules_cum"))
    diagram, _warnings = tokengraph_to_mermaid(result.tokengraph)
 
    # Punctuation tokens ("," and ".") must not become nodes.
    assert 't4["' not in diagram
    assert 't9["' not in diagram
 
    assert "t3 -->|unit verb| t1" in diagram
    assert "t2 -->|direct object| t3" in diagram