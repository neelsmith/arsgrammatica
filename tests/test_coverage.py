"""
Meta-test: checks that every documented RelationLabel actually has at least
one gold example exercising it, so a relation type doesn't silently go
untested the way "agent" and the relatedtoken2/relationship2 overflow slot
did in the original single-fixture suite.
 
This is expected to FAIL until fixtures/gold_examples.py has coverage for
every label -- that's the point. The assertion message names exactly which
labels still need an example.
"""
 
import typing
 
from arsgrammatica.models import RelationLabel
from fixtures.gold_examples import GOLD_EXAMPLES
 
 
def test_every_relation_label_has_a_gold_example():
    seen = {
        tok.get(field)
        for example in GOLD_EXAMPLES
        for tok in example.canned_answer["tokengraph"]
        for field in ("relationship1", "relationship2")
    } - {None}
 
    all_labels = set(typing.get_args(RelationLabel))
    missing = all_labels - seen
 
    assert not missing, (
        f"no gold example exercises: {sorted(missing)} -- add one to "
        f"fixtures/gold_examples.py"
    )

