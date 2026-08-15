"""
Offline tests for arsgrammatica/verbal_units.py's assign_verbal_units().
 
These run against real gold fixtures (fixtures/gold_examples.py), not
synthetic data, since the tricky cases this function has to get right --
a subordinating conjunction or relative pronoun's own outgoing relation
pointing at the OUTER clause, while the token itself belongs to the INNER
clause it introduces -- only really show up in genuine sentences. See
verbal_units.py's module docstring for the reasoning.
"""
 
import pytest
 
from arsgrammatica.models import TokenAnalysis
from arsgrammatica.verbal_units import assign_verbal_units
from fixtures.gold_examples import GOLD_EXAMPLES
 
 
def _tokengraph(slug):
    example = next(e for e in GOLD_EXAMPLES if e.slug == slug)
    return [TokenAnalysis(**tok) for tok in example.canned_answer["tokengraph"]]
 
 
@pytest.mark.parametrize("example", GOLD_EXAMPLES, ids=lambda e: e.slug)
def test_every_token_gets_an_entry(example):
    """Every token id in the tokengraph -- including punctuation and
    tokens with no relation at all -- must appear as a key, even if its
    value is None."""
    tokengraph = [TokenAnalysis(**tok) for tok in example.canned_answer["tokengraph"]]
    assignment = assign_verbal_units(tokengraph)
    assert set(assignment.keys()) == {tok.id for tok in tokengraph}
 
 
@pytest.mark.parametrize("example", GOLD_EXAMPLES, ids=lambda e: e.slug)
def test_every_anchor_is_assigned_to_itself(example):
    tokengraph = [TokenAnalysis(**tok) for tok in example.canned_answer["tokengraph"]]
    assignment = assign_verbal_units(tokengraph)
    for tok in tokengraph:
        if tok.verbalunitid is not None:
            assert assignment[tok.id] == tok.verbalunitid
 
 
def test_subordinating_conjunction_belongs_to_the_clause_it_introduces():
    """"cum" in "Hercules cum gregem perlustrasset, pergit ad proximam
    speluncam" is grammatically part of the dependent clause it introduces
    ("cum gregem perlustrasset") -- even though cum's own relatedtoken1
    points at pergit (t5), the MAIN clause's verb, per the "subordinating
    conjunction" relation (see syntax_model.md). It must not be pulled into
    pergit's verbal unit."""
    tokengraph = _tokengraph("unit_verb_hercules_cum")
    assignment = assign_verbal_units(tokengraph)
    assert assignment["t1"] == "t3"  # cum -> perlustrasset's unit, not pergit's
    assert assignment["t2"] == "t3"  # gregem (direct object of perlustrasset)
    assert assignment["t0"] == "t5"  # Hercules (subject of pergit) stays in the main clause
 
 
def test_relative_pronoun_belongs_to_the_clause_it_introduces_not_its_antecedents():
    """"quibus" in "Latini, cum quibus ictum foedus erat, sustulerant
    animos" points back at its antecedent Latini via relatedtoken1
    ("relative pronoun"), and at "cum" via relatedtoken2 ("object of
    preposition") -- but grammatically, quibus is part of the erat clause,
    not Latini's. The relative-pronoun link must not win."""
    tokengraph = _tokengraph("relative_pronoun_latini_cum_quibus")
    assignment = assign_verbal_units(tokengraph)
    assert assignment["t3"] == "t6"  # quibus -> erat's unit, not sustulerant's
    assert assignment["t2"] == "t6"  # cum
    assert assignment["t0"] == "t8"  # Latini stays with the main verb, sustulerant
 
 
def test_ablative_absolute_noun_belongs_to_the_main_verb():
    """In "Anco regnante Lucumo Romam commigravit", Anco is a true ablative
    absolute (per syntax_model.md, "otherwise unconnected syntactically"),
    so it's assigned to the MAIN verb commigravit -- not to regnante, the
    participle it grammatically agrees with. regnante's own verbal unit
    ends up a singleton (nothing else resolves to it), which is the
    expected shape for this construction, not a bug."""
    tokengraph = _tokengraph("participle_predicate_anco_regnante")
    assignment = assign_verbal_units(tokengraph)
    assert assignment["t0"] == "t4"  # Anco -> commigravit
    assert assignment["t1"] == "t1"  # regnante -> itself (singleton unit)
    assert assignment["t2"] == "t4"  # Lucumo (subject of commigravit)
    assert assignment["t3"] is None  # Romam: bare accusative of place, not covered
 
 
def test_circumstantial_participle_noun_keeps_its_own_clause_role():
    """In "Eum advenientem laeti omnes accepere", Eum fits into the main
    clause as accepere's direct object, so it's assigned there -- not to
    advenientem, the participle it agrees with."""
    tokengraph = _tokengraph("circumstantial_participle_eum_advenientem")
    assignment = assign_verbal_units(tokengraph)
    assert assignment["t0"] == "t4"  # Eum -> accepere (its own direct-object role)
    assert assignment["t1"] == "t1"  # advenientem -> itself (singleton unit)
 
 
def test_direct_quote_and_aside_form_their_own_units_not_the_framing_verbs():
    """A direct-quote or aside verb's own outward relation names the verb
    it interrupts/is framed by -- but since it's itself a verbal-unit
    anchor, that outward relation must not pull it into the framing verb's
    unit."""
    tokengraph = _tokengraph("direct_quote_tuum_est_inquit")
    assignment = assign_verbal_units(tokengraph)
    assert assignment["t1"] == "t1"  # est (direct quote) -> itself
    assert assignment["t3"] == "t3"  # inquit (framing verb) -> itself
    assert assignment["t0"] == "t1"  # Tuum (predicate of est) stays with the quote
    assert assignment["t6"] == "t1"  # regnum (subject of est) stays with the quote
 
    tokengraph = _tokengraph("aside_equidem_pace_dixerim")
    assignment = assign_verbal_units(tokengraph)
    assert assignment["t3"] == "t3"  # dixerim (aside) -> itself
    assert assignment["t13"] == "t13"  # spero (framed verb) -> itself, not merged with the aside
    assert assignment["t2"] == "t3"  # pace stays with the aside
    assert assignment["t7"] is None  # nos: left unrelated per syntax_model.md
 
 
def test_unrelated_and_punctuation_tokens_get_none():
    tokengraph = _tokengraph("numeral_hiberna_aberant_xxv")
    assignment = assign_verbal_units(tokengraph)
    assert assignment["t7"] is None  # trailing "."
    # "milia passuum XXV" (accusative of extent) has no relation in the
    # current scheme -- none of the three should resolve to a verbal unit.
    assert assignment["t4"] is None
    assert assignment["t5"] is None
    assert assignment["t6"] is None
 
 
def test_cycle_in_relations_does_not_infinite_loop():
    """Two tokens relating only to each other, with no anchor reachable,
    must resolve to None rather than recursing forever."""
    tokengraph = [
        TokenAnalysis(
            id="t0", token="a", tokentype="lexical",
            relatedtoken1="t1", relationship1="adverbial",
        ),
        TokenAnalysis(
            id="t1", token="b", tokentype="lexical",
            relatedtoken1="t0", relationship1="adverbial",
        ),
    ]
    assignment = assign_verbal_units(tokengraph)
    assert assignment == {"t0": None, "t1": None}