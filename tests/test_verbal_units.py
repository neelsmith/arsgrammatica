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
from arsgrammatica.verbal_units import (
    assign_verbal_units,
    compute_subordination_depths,
    find_unanchored_coordinated_verbs,
)
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



# ---------------------------------------------------------------------------
# compute_subordination_depths()
# ---------------------------------------------------------------------------


def test_independent_verb_has_depth_zero():
    """An independent verb's own relatedtoken1 is the 'root' sentinel,
    which compute_subordination_depths() special-cases directly rather
    than chasing a governing relation at all."""
    tokengraph = _tokengraph("unit_verb_hercules_cum")
    depths, warnings = compute_subordination_depths(tokengraph)
    assert depths["t5"] == 0  # pergit, independent
    assert warnings == []


def test_dependent_verb_via_subordinating_conjunction_has_depth_one():
    """perlustrasset's own relatedtoken1 points at cum (t1), which is not
    itself an anchor -- chasing cum's own outgoing relation reaches pergit
    (t5), the anchor one level up."""
    tokengraph = _tokengraph("unit_verb_hercules_cum")
    depths, warnings = compute_subordination_depths(tokengraph)
    assert depths["t3"] == 1  # perlustrasset, dependent on pergit
    assert warnings == []


def test_dependent_verb_via_relative_pronoun_has_depth_one():
    """erat's own relatedtoken1 points at quibus (t3), which points (via
    relatedtoken1) at its antecedent Latini (t0), which in turn points at
    sustulerant (t8) -- a two-hop chase through two non-anchor
    intermediaries before reaching the governing anchor."""
    tokengraph = _tokengraph("relative_pronoun_latini_cum_quibus")
    depths, warnings = compute_subordination_depths(tokengraph)
    assert depths["t8"] == 0  # sustulerant, independent
    assert depths["t6"] == 1  # erat, dependent on sustulerant
    assert warnings == []


def test_direct_quote_and_aside_have_depth_one():
    tokengraph = _tokengraph("direct_quote_tuum_est_inquit")
    depths, warnings = compute_subordination_depths(tokengraph)
    assert depths["t3"] == 0  # inquit, independent
    assert depths["t1"] == 1  # est, direct quote framed by inquit
    assert warnings == []

    tokengraph = _tokengraph("aside_equidem_pace_dixerim")
    depths, warnings = compute_subordination_depths(tokengraph)
    assert depths["t13"] == 0  # spero, independent
    assert depths["t3"] == 1  # dixerim, aside interrupting spero
    # esse's own relatedtoken1 points at spero (t13) directly, NOT at
    # dixerim (t3) -- the whole point of the fixture's own retrofit -- so
    # esse sits at depth 1 too, a sibling of dixerim, not nested under it.
    assert depths["t12"] == 1  # esse, indirect statement governed by spero
    assert warnings == []


def test_circumstantial_participle_and_ablative_absolute_have_depth_one():
    tokengraph = _tokengraph("participle_predicate_anco_regnante")
    depths, warnings = compute_subordination_depths(tokengraph)
    assert depths["t4"] == 0  # commigravit, independent
    assert depths["t1"] == 1  # regnante, ablative absolute
    assert warnings == []

    tokengraph = _tokengraph("circumstantial_participle_eum_advenientem")
    depths, warnings = compute_subordination_depths(tokengraph)
    assert depths["t4"] == 0  # accepere, independent
    assert depths["t1"] == 1  # advenientem, circumstantial participle
    assert warnings == []


def test_indirect_statement_has_depth_one():
    """fuisse's own relatedtoken1 -> dixit (the new relation this whole
    feature depended on adding) makes its depth directly resolvable, one
    level below the verb of saying that governs it."""
    tokengraph = _tokengraph("indirect_statement_facturum_fuisse_dixit")
    depths, warnings = compute_subordination_depths(tokengraph)
    assert depths["t4"] == 0  # dixit, independent
    assert depths["t3"] == 1  # fuisse, indirect statement governed by dixit
    assert warnings == []


def test_depth_two_nesting_through_a_dependent_clause():
    """peccavisse is an indirect statement governed by sciret -- itself a
    dependent verb one level below doluit -- so peccavisse sits two levels
    below the root, not one: exactly the 'a dependent clause introduces an
    indirect statement' case the feature was requested for."""
    tokengraph = _tokengraph("depth_two_cum_sciret_peccavisse_doluit")
    depths, warnings = compute_subordination_depths(tokengraph)
    assert depths["t5"] == 0  # doluit, independent
    assert depths["t1"] == 1  # sciret, dependent on doluit via cum
    assert depths["t3"] == 2  # peccavisse, indirect statement governed by sciret
    assert warnings == []


def test_every_gold_example_anchor_resolves_with_no_warnings():
    """Sanity check across the whole fixture set: every documented
    governing-relation pattern (subordinating conjunction, relative
    pronoun, direct quote, aside, circumstantial participle, ablative
    absolute, indirect statement) should resolve cleanly, with no
    unresolved anchors and no warnings -- a regression here would mean a
    fixture's relation shape silently stopped being chase-able."""
    for example in GOLD_EXAMPLES:
        tokengraph = [TokenAnalysis(**tok) for tok in example.canned_answer["tokengraph"]]
        depths, warnings = compute_subordination_depths(tokengraph)
        assert warnings == [], f"{example.slug}: {warnings}"
        assert all(v is not None for v in depths.values()), (
            f"{example.slug}: unresolved depth in {depths}"
        )


def test_cycle_in_relations_leaves_depth_unresolved_with_warning():
    """Two anchors whose own outgoing relations point only at each other
    (no 'root' sentinel, no third party to break the cycle) must resolve
    to None with an explanatory warning, not recurse forever."""
    tokengraph = [
        TokenAnalysis(
            id="t0", token="a", tokentype="lexical", verbalunitid="t0",
            relatedtoken1="t1", relationship1="unit verb",
        ),
        TokenAnalysis(
            id="t1", token="b", tokentype="lexical", verbalunitid="t1",
            relatedtoken1="t0", relationship1="unit verb",
        ),
    ]
    depths, warnings = compute_subordination_depths(tokengraph)
    assert depths == {"t0": None, "t1": None}
    assert len(warnings) >= 1



# ---------------------------------------------------------------------------
# find_unanchored_coordinated_verbs()
# ---------------------------------------------------------------------------


def test_correctly_coordinated_verbs_produce_no_warning():
    """noluit and adduxit are both anchors of their own verbal unit --
    symmetric, so nothing to flag."""
    tokengraph = _tokengraph("coordinating_conjunction_verbs_ille_hermionenque")
    assert find_unanchored_coordinated_verbs(tokengraph) == []


def test_coordinated_nouns_produce_no_warning():
    """arma and virum (joined by the enclitic que) are both ordinary nouns
    -- neither is a verbal-unit anchor, which is the OTHER symmetric case
    (not a mistake): the heuristic must not mistake a noun/adjective pair
    for a broken verb pair."""
    tokengraph = _tokengraph("enclitic_arma_virumque_cano")
    assert find_unanchored_coordinated_verbs(tokengraph) == []


def test_sentence_initial_one_sided_coordination_produces_no_warning():
    """sed's own relation1 points only at dedit (the sentence-initial,
    one-sided case -- see that relation's own documented exception); with
    no second conjunct to compare against, this must not crash or flag
    anything."""
    tokengraph = _tokengraph("coordinating_conjunction_sentence_initial_sed_dedit")
    assert find_unanchored_coordinated_verbs(tokengraph) == []


def test_correct_dedit_et_dixit_fixture_produces_no_warning():
    tokengraph = _tokengraph("coordinating_conjunction_dedit_et_dixit_esse")
    assert find_unanchored_coordinated_verbs(tokengraph) == []


def test_flags_a_coordinated_verb_that_lost_its_own_anchor():
    """Simulates the real live-LM mistake this function exists to catch:
    take the correct dedit/dixit fixture and strip dixit's own anchor
    (verbalunitid, and its 'root'/'unit verb' relation) -- exactly what a
    live model actually produced for this sentence -- and confirm the
    asymmetry (dedit still anchored, dixit no longer) is flagged, naming
    both the conjunction and the token that lost its anchor."""
    tokengraph = _tokengraph("coordinating_conjunction_dedit_et_dixit_esse")
    for tok in tokengraph:
        if tok.id == "t20":
            tok.verbalunitid = None
            tok.relatedtoken1 = None
            tok.relationship1 = None

    warnings = find_unanchored_coordinated_verbs(tokengraph)
    assert len(warnings) == 1
    assert "t16" in warnings[0]  # et, the conjunction
    assert "t15" in warnings[0]  # dedit, still correctly anchored
    assert "t20" in warnings[0]  # dixit, the one that lost its anchor


def test_both_sides_anchored_but_neither_actually_verbs_is_not_flagged():
    """The heuristic only looks at anchoring symmetry, not part of speech --
    if BOTH sides of a coordinating-conjunction pair happen to be anchors
    (whatever they are), that's the same shape as a correct verb pairing,
    so nothing is flagged. This documents that the check is a heuristic,
    not a guarantee: it can't independently confirm the pair really is
    verbs, only that the anchoring pattern isn't the specific asymmetry
    the real bug produced."""
    tokengraph = [
        TokenAnalysis(
            id="t0", token="a", tokentype="lexical", verbalunitid="t0",
            relatedtoken1="root", relationship1="unit verb",
        ),
        TokenAnalysis(
            id="t1", token="et", tokentype="lexical",
            relatedtoken1="t0", relationship1="coordinating conjunction",
            relatedtoken2="t2", relationship2="coordinating conjunction",
        ),
        TokenAnalysis(
            id="t2", token="b", tokentype="lexical", verbalunitid="t2",
            relatedtoken1="root", relationship1="unit verb",
        ),
    ]
    assert find_unanchored_coordinated_verbs(tokengraph) == []
