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
 
 
def test_ablative_absolute_noun_belongs_to_its_circumstantial_participle():
    """In "Anco regnante Lucumo Romam commigravit", Anco is a true ablative
    absolute (per syntax_model.md, "otherwise unconnected syntactically"):
    syntactically absolute from commigravit's own clause, it takes its
    verbal unit instead from regnante, the circumstantial participle it
    grammatically agrees with -- so Anco and regnante end up in the SAME
    (regnante's) verbal unit, not split between regnante and commigravit."""
    tokengraph = _tokengraph("participle_predicate_anco_regnante")
    assignment = assign_verbal_units(tokengraph)
    assert assignment["t0"] == "t1"  # Anco -> regnante (its circumstantial participle)
    assert assignment["t1"] == "t1"  # regnante -> itself
    assert assignment["t2"] == "t4"  # Lucumo (subject of commigravit)
    assert assignment["t3"] is None  # Romam: bare accusative of place, not covered
 
 
def test_ablative_absolute_with_implied_participle_of_sum():
    """"P. Valerius ... Agrippa Menenio P. Postumio consulibus moritur":
    consulibus is a true ablative absolute (Latin has no present participle
    of sum, so an implied one -- t8_implied -- stands in), so consulibus
    takes ITS verbal unit from that implied participle, not from moritur.
    Menenio and Postumio are each in apposition to consulibus, not to
    moritur -- so they follow consulibus's own (redirected) resolution and
    land in the implied participle's unit too, exactly the "new subgraphs
    begin from the ablative-absolute noun" shape this feature is for."""
    tokengraph = _tokengraph("implied_participle_of_sum_consulibus")
    assignment = assign_verbal_units(tokengraph)
    assert assignment["t8"] == "t8_implied"  # consulibus -> the implied participle
    assert assignment["t8_implied"] == "t8_implied"  # implied participle -> itself
    assert assignment["t5"] == "t8_implied"  # Menenio, apposed to consulibus
    assert assignment["t7"] == "t8_implied"  # Postumio, apposed to consulibus
    assert assignment["t1"] == "t9"  # Valerius (subject of moritur) stays with the main verb
    assert assignment["t9"] == "t9"  # moritur -> itself


def test_ablative_absolute_re_cognita_belongs_to_its_participle():
    """"Sed re cognita, iussu Cereris Triptolemo regnum dedit": re is a true
    ablative absolute agreeing with cognita, so re takes its verbal unit
    from cognita rather than from dedit, the main verb it otherwise points
    at via 'ablative absolute'."""
    tokengraph = _tokengraph("coordinating_conjunction_sentence_initial_sed_dedit")
    assignment = assign_verbal_units(tokengraph)
    assert assignment["t1"] == "t2"  # re -> cognita (its circumstantial participle)
    assert assignment["t2"] == "t2"  # cognita -> itself
    assert assignment["t8"] == "t8"  # dedit -> itself
    assert assignment["t4"] == "t8"  # iussu (ablative modifying dedit) stays with dedit


def test_praenomen_chains_through_to_the_verb_like_any_other_relation():
    """"Sex. Tarquinius inscio Collatino cum comite uno Collatiam venit":
    Sex. relates to Tarquinius via 'praenomen', a relation like any other
    for assign_verbal_units()'s purposes -- it chains forward exactly the
    same way, landing in the same (venit's) verbal unit as Tarquinius
    itself. Collatino (a true ablative absolute) belongs instead to the
    implied participle of sum it agrees with, per the ablative-absolute
    redirect -- and inscio, adjectival to Collatino, follows it there."""
    tokengraph = _tokengraph("praenomen_sex_tarquinius_venit")
    assignment = assign_verbal_units(tokengraph)
    assert assignment["t0"] == "t8"  # Sex. -> venit (via Tarquinius)
    assert assignment["t1"] == "t8"  # Tarquinius -> venit (subject)
    assert assignment["t3"] == "t3_implied"  # Collatino -> the implied participle
    assert assignment["t2"] == "t3_implied"  # inscio, adjectival to Collatino


def test_accusative_links_to_a_verb_or_to_another_noun():
    """The 'accusative' relation can target either a verb (a bare
    accusative of place to which, "Romam" in "Romam venit") or another
    noun (an accusative of extent qualifying it, "milia" in "duo milia
    passuum iter fecerunt", qualifying "iter" rather than "fecerunt")."""
    tokengraph = _tokengraph("accusative_romam_venit")
    assignment = assign_verbal_units(tokengraph)
    assert assignment["t0"] == "t1"  # Romam -> venit directly

    tokengraph = _tokengraph("accusative_milia_passuum_iter")
    assignment = assign_verbal_units(tokengraph)
    assert assignment["t1"] == "t4"  # milia -> iter -> fecerunt's unit
    assert assignment["t0"] == "t4"  # Duo, adjectival to milia, follows it there
    assert assignment["t2"] == "t4"  # passuum, genitive on milia, follows it there too


def test_opus_est_ablative_relates_to_opus_not_to_the_verb():
    """"Collatinus negat verbis opus esse": in the idiomatic 'opus est'
    construction, the ablative verbis relates to opus itself (not to esse,
    the verb) -- so verbis resolves through opus to esse's own (indirect
    statement) verbal unit, exactly as opus itself does."""
    tokengraph = _tokengraph("ablative_opus_est_verbis")
    assignment = assign_verbal_units(tokengraph)
    assert assignment["t3"] == "t4"  # opus -> esse (predicate)
    assert assignment["t2"] == "t4"  # verbis -> opus -> esse


def test_circumstantial_participle_noun_keeps_its_own_clause_role():
    """In "Eum advenientem laeti omnes accepere", Eum fits into the main
    clause as accepere's direct object, so it's assigned there -- not to
    advenientem, the participle it agrees with."""
    tokengraph = _tokengraph("circumstantial_participle_eum_advenientem")
    assignment = assign_verbal_units(tokengraph)
    assert assignment["t0"] == "t4"  # Eum -> accepere (its own direct-object role)
    assert assignment["t1"] == "t1"  # advenientem -> itself (singleton unit)
 
 
def test_apposition_does_not_disturb_verbal_unit_assignment():
    """Apposition is not a "unit verb" relation, so it never triggers the
    inner-clause wrinkle assign_verbal_units() applies to subordinating
    conjunctions/relative pronouns -- an appositive and its dependent
    genitive just chase forward through the noun they're apposed to,
    landing in the same single verbal unit as everything else in this
    one-clause sentence."""
    tokengraph = _tokengraph("apposition_neptunus_aegeus_filius")
    assignment = assign_verbal_units(tokengraph)
    assert assignment["t4"] == "t14"  # filius (apposed to Aegeus) -> concubuerunt
    assert assignment["t3"] == "t14"  # Pandionis (genitive on filius) -> concubuerunt
    assert assignment["t11"] == "t14"  # filia (apposed to Aethra) -> concubuerunt
    assert assignment["t10"] == "t14"  # Pitthei (genitive on filia) -> concubuerunt
    assert assignment["t14"] == "t14"  # concubuerunt -> itself


def test_complementary_infinitive_and_infinitive_as_noun_are_not_anchors():
    """A complementary infinitive (expugnare, completing vellet) and an
    infinitive used as an ordinary noun (dolere, the subject of est) are
    both NEW relation shapes syntax_model.md added, but neither makes its
    token a verbal-unit anchor -- they resolve to whichever governing verb
    they point at, exactly like a direct object or adverb would, with zero
    changes needed to assign_verbal_units() itself."""
    tokengraph = _tokengraph("complementary_infinitive_amphion_expugnare_vellet")
    assignment = assign_verbal_units(tokengraph)
    assert assignment["t5"] == "t6"  # expugnare -> vellet's own unit
    assert all(tok.verbalunitid is None for tok in tokengraph if tok.id == "t5")

    tokengraph = _tokengraph("infinitive_as_subject_dolere_malum")
    assignment = assign_verbal_units(tokengraph)
    assert assignment["t0"] == "t2"  # dolere -> est's unit
    assert all(tok.verbalunitid is None for tok in tokengraph if tok.id == "t0")


def test_gerund_and_gerundive_are_not_anchors():
    """A gerund (disserendi) and a gerundive (faciendum) are both treated
    as ordinary noun/adjective relations, not new verbal expressions --
    each resolves to its governing verb's unit like any other dependent
    token, with no verbalunitid of its own."""
    tokengraph = _tokengraph("gerund_ars_bene_disserendi")
    assignment = assign_verbal_units(tokengraph)
    assert assignment["t2"] == "t4"  # disserendi (genitive on Ars) -> est's unit
    assert all(tok.verbalunitid is None for tok in tokengraph if tok.id == "t2")

    tokengraph = _tokengraph("gerundive_metapontus_sacrum_faciendum")
    assignment = assign_verbal_units(tokengraph)
    assert assignment["t7"] == "t1"  # faciendum (adjectival on sacrum) -> exiit's unit
    assert all(tok.verbalunitid is None for tok in tokengraph if tok.id == "t7")


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
    # "milia passuum XXV" is an accusative-of-extent phrase: milia now
    # relates to aberant via 'accusative' (see syntax_model.md's "Noun
    # relations" section), so it resolves to aberant's own verbal unit;
    # passuum and XXV still have no relation in the scheme and stay None.
    assert assignment["t4"] == "t1"
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


def test_dependent_verb_via_interrogative_word_has_depth_one():
    """quanta introduces an indirect question exactly like a subordinating
    conjunction would -- syntax_model.md reuses that same relationship
    label for it (relatedtoken1 -> audit, relationship1 'subordinating
    conjunction'), so afficeretur (relatedtoken1 -> quanta, relationship1
    'unit verb') resolves its depth via the identical chase a plain
    subordinating conjunction gets, with no code changes needed."""
    tokengraph = _tokengraph("indirect_question_theseus_audit_quanta")
    depths, warnings = compute_subordination_depths(tokengraph)
    assert depths["t1"] == 0  # audit, independent
    assert depths["t5"] == 1  # afficeretur, dependent on audit via quanta
    assert warnings == []


def test_circumstantial_participle_preferred_over_attributive_reaches_depth_two():
    """Regression check for the syntax_model.md 'prefer circumstantial when
    uncertain' rule (using its own worked example): tinctas now anchors its
    own circumstantial-participle verbal expression agreeing with sagittas,
    which is itself sciret's direct object -- sciret already sits one level
    below dedit, so tinctas, one hop further out, lands at depth 2."""
    tokengraph = _tokengraph("coordinating_conjunction_dedit_et_dixit_esse")
    depths, warnings = compute_subordination_depths(tokengraph)
    assert depths["t15"] == 0  # dedit, independent
    assert depths["t4"] == 1  # sciret, dependent on dedit via cum
    assert depths["t9"] == 2  # tinctas, circumstantial participle agreeing with sagittas
    assert warnings == []


def test_complementary_infinitive_adds_no_extra_depth_hop():
    """expugnare (the complementary infinitive) isn't an anchor, so it
    never appears in compute_subordination_depths()'s output at all --
    vellet's own relatedtoken1 points at cum, not at expugnare, so the
    chase to est is exactly as short as an ordinary cum-clause's."""
    tokengraph = _tokengraph("complementary_infinitive_amphion_expugnare_vellet")
    depths, warnings = compute_subordination_depths(tokengraph)
    assert depths["t11"] == 0  # est (interfectus), independent
    assert depths["t6"] == 1  # vellet, dependent on est via cum
    assert "t5" not in depths  # expugnare is not an anchor at all
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
