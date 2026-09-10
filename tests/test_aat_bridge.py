"""
Offline tests for arsgrammatica/aat_bridge.py's aatgraph() -- the
converter from an arsgrammatica analysis (models.py's TokenAnalysis/
VerbalExpression scheme) to an `aat` package AATGraph.

Like test_verbal_units.py, these run against real gold fixtures
(fixtures/gold_examples.py) built directly from their own canned_answer
dicts -- no DummyLM, no live LM call -- since aatgraph() is a pure
function of (sentences, results) and the gold fixtures already exercise
the tricky real cases (subordination through an intermediate token,
implied tokens, compound verb forms) that a hand-rolled synthetic example
would risk getting subtly wrong.
"""

from types import SimpleNamespace

import pytest
from aat.core import CitableToken, validate as aat_validate

from arsgrammatica.aat_bridge import aatgraph
from arsgrammatica.models import IMPLIED_TOKENTYPES, Sentence, Token, TokenAnalysis, VerbalExpression
from fixtures.gold_examples import GOLD_EXAMPLES


def _example(slug):
    return next(e for e in GOLD_EXAMPLES if e.slug == slug)


def _sentence_and_result(slug, citation=None):
    """Build (sentence, result) for one gold example: `sentence.tokens`
    from its non-implied tokengraph entries (optionally all sharing one
    `citation`), and `result` as a bare SimpleNamespace carrying
    `.tokengraph`/`.verbalunits` built from the same canned_answer --
    exactly the two attributes aatgraph() reads off each `results[i]`,
    without needing an actual dspy.Prediction."""
    canned = _example(slug).canned_answer
    tokens = [
        Token(id=entry["id"], text=entry["token"], citation=citation)
        for entry in canned["tokengraph"]
        if entry.get("tokentype") not in IMPLIED_TOKENTYPES
    ]
    sentence = Sentence(tokens=tokens)
    result = SimpleNamespace(
        tokengraph=[TokenAnalysis(**tok) for tok in canned["tokengraph"]],
        verbalunits=[VerbalExpression(**vu) for vu in canned["verbalunits"]],
    )
    return sentence, result


def _by_role(graph, role):
    return {n.id: n for n in graph.nodes if n.role == role}


def test_hercules_subordination_and_agent_target_mapping():
    """'Hercules cum gregem perlustrasset, pergit ad proximam speluncam.'
    perlustrasset (t3, dependent, transitive active) is subordinate to
    pergit (t5, independent, intransitive); gregem is perlustrasset's
    target (direct object); Hercules is pergit's agent (subject);
    perlustrasset has no agent of its own (no explicit subject token
    relates to it -- the 'cum'-clause leaves it implicit) and pergit has
    no target (intransitive)."""
    sentence, result = _sentence_and_result("unit_verb_hercules_cum", citation="Livy 1.7")
    graph, warnings = aatgraph([sentence], [result])
    assert warnings == []

    actions = _by_role(graph, "action")
    assert set(actions) == {"t3", "t5"}
    assert actions["t3"].related_node == "t5"
    assert actions["t3"].value == "perlustrasset"
    assert actions["t5"].related_node is None
    assert actions["t5"].value == "pergit"

    agents = _by_role(graph, "agent")
    targets = _by_role(graph, "target")
    assert set(agents) == {"t0"}  # Hercules -> pergit
    assert agents["t0"].related_node == "t5"
    assert set(targets) == {"t2"}  # gregem -> perlustrasset
    assert targets["t2"].related_node == "t3"

    for node in graph.nodes:
        assert node.context == "Livy 1.7"


def test_transitive_passive_agent_via_object_of_preposition_and_compound_value():
    """'urbs a Romulo condita est.' The 'agent' relation label sits on the
    preposition 'a' (t1), not the real agent noun 'Romulo' (t2) -- the
    AATNode built for this action's agent must be anchored on t2 (the
    object of the preposition), not t1. The action itself is a compound
    (condita + est), anchored at t3 (condita, per VerbalExpression's own
    compound-id convention -- the participle anchors, not the auxiliary),
    with value 'condita est' in surface order. urbs (subject of a
    transitive-passive verb) is a target, not an agent."""
    sentence, result = _sentence_and_result("semantic_type_transitive_passive_urbs_condita")
    graph, warnings = aatgraph([sentence], [result])
    assert warnings == []

    actions = _by_role(graph, "action")
    assert set(actions) == {"t3"}
    assert actions["t3"].value == "condita est"
    assert actions["t3"].related_node is None

    agents = _by_role(graph, "agent")
    assert set(agents) == {"t2"}  # Romulo, not the preposition "a" (t1)
    assert agents["t2"].value == "Romulo"
    assert agents["t2"].related_node == "t3"

    targets = _by_role(graph, "target")
    assert set(targets) == {"t0"}  # urbs, subject of a transitive-passive verb
    assert targets["t0"].related_node == "t3"


def test_linking_verb_predicate_is_a_target():
    """'Etruria erat vicina.' Etruria (subject of a linking verb) is an
    agent; vicina (its predicate) is a target -- matching aat's own
    English convention for a linking verb's predicate, per aat_bridge.py's
    module docstring."""
    sentence, result = _sentence_and_result("semantic_type_linking_verb_etruria_vicina")
    graph, warnings = aatgraph([sentence], [result])
    assert warnings == []

    agents = _by_role(graph, "agent")
    targets = _by_role(graph, "target")
    assert set(agents) == {"t0"}  # Etruria
    assert set(targets) == {"t2"}  # vicina
    assert targets["t2"].related_node == "t1"  # erat


def test_implied_subject_is_skipped_and_subordination_chases_through_it():
    """'Recordatus somniorum ait ad eos.' t0_implied (an implied-subject
    token standing in for ait's own unexpressed subject) must NOT become
    an agent node for ait, even though it does carry a 'subject' relation
    into it -- it has no surface realization at all. Recordatus (t0,
    dependent, transitive active) is still correctly subordinated to ait
    (t2) by chasing through t0_implied (a non-anchor token), and gets no
    agent or target node of its own (its own subject is never stated
    separately, and 'somniorum' relates to it via 'genitive', not 'direct
    object')."""
    sentence, result = _sentence_and_result("implied_subject_recordatus_somniorum_ait")
    graph, warnings = aatgraph([sentence], [result])
    assert warnings == []

    actions = _by_role(graph, "action")
    assert set(actions) == {"t0", "t2"}
    assert actions["t0"].related_node == "t2"  # Recordatus subordinate to ait
    assert actions["t2"].related_node is None

    agents = _by_role(graph, "agent")
    targets = _by_role(graph, "target")
    assert "t0_implied" not in {n.id for n in graph.nodes}
    assert agents == {}
    assert targets == {}


def test_graph_validates_referentially_against_a_matching_token_list():
    """A graph aatgraph() builds should always pass aat.core.validate()
    given a CitableToken list covering the same (context, id) pairs --
    referential soundness, not correctness of the underlying Latin
    analysis, which is all validate() ever checks."""
    sentence, result = _sentence_and_result("unit_verb_hercules_cum", citation="Livy 1.7")
    graph, warnings = aatgraph([sentence], [result])
    assert warnings == []

    tokens = [
        CitableToken(context="Livy 1.7", id=tok.id, value=tok.text)
        for tok in sentence.tokens
    ]
    problems = aat_validate(tokens, graph)
    assert problems == []


def test_multi_citation_sentence_warns_and_uses_first_token_citation():
    """A sentence whose tokens span more than one citation (arsgrammatica
    lets a sentence cross a CitedText boundary -- see pipeline.py) gets a
    warning, and every node derived from it uses its first token's
    citation as the shared context, per aat_bridge.py's own module
    docstring."""
    sentence, result = _sentence_and_result("semantic_type_linking_verb_etruria_vicina")
    # Etruria erat vicina .  -> give the first two tokens one citation and
    # the rest another, to force a genuine span.
    for tok, citation in zip(sentence.tokens, ["Livy 1.1", "Livy 1.1", "Livy 1.2", "Livy 1.2"]):
        tok.citation = citation

    graph, warnings = aatgraph([sentence], [result])
    assert len(warnings) == 1
    assert "Livy 1.1" in warnings[0] and "Livy 1.2" in warnings[0]
    assert all(node.context == "Livy 1.1" for node in graph.nodes)


def test_no_citation_falls_back_to_empty_context():
    sentence, result = _sentence_and_result("semantic_type_linking_verb_etruria_vicina")
    graph, warnings = aatgraph([sentence], [result])
    assert warnings == []
    assert all(node.context == "" for node in graph.nodes)


# ---------------------------------------------------------------------------
# Composing with verbal_units.filter_tokengraph_by_aat_depth() -- building a
# depth-limited AAT graph, the way latin_syntaxer_review.py's own AAT
# display does: filter the tokengraph to a chosen aat_depth cutoff BEFORE
# calling aatgraph(), rather than trying to filter the resulting AATGraph's
# own nodes after the fact (aat.core has no direct support for that
# anyway). filter_tokengraph_by_aat_depth()'s own docstring (verbal_units.py)
# claims this is always safe -- no dangling related_node reference -- for
# exactly the reason these tests check.
# ---------------------------------------------------------------------------

from arsgrammatica.verbal_units import filter_tokengraph_by_aat_depth, max_aat_depth


@pytest.mark.parametrize(
    "slug",
    [
        "unit_verb_hercules_cum",
        "depth_two_cum_sciret_peccavisse_doluit",
        "depth_taurum_cum_quo_concubuit",
        "semantic_type_transitive_passive_urbs_condita",
        "circumstantial_participle_eum_advenientem",
        "relative_pronoun_latini_cum_quibus",
        "coordinating_conjunction_dedit_et_dixit_esse",
        "indirect_question_theseus_audit_quanta",
        "implied_subject_recordatus_somniorum_ait",
        "ablative_omnia_ferro_flammaque_miscet",
    ],
)
def test_filtering_by_aat_depth_before_building_never_leaves_a_dangling_governing_link(slug):
    """Every one of aat_bridge.py's own documented wrinkles (unit verb,
    circumstantial participle/ablative absolute, relative pronoun, a
    passive verb's agent-via-preposition, an implied-subject antecedent,
    a coordinated pair of verbs) -- filtered to EVERY depth cutoff from 0
    up to the sentence's own deepest AAT depth -- must still let aatgraph()
    resolve every surviving node's own related_node (if any) to another
    node actually present in the graph, with no warnings at all."""
    sentence, result = _sentence_and_result(slug, citation="Livy 1.1")
    maxd = max_aat_depth(result.tokengraph)
    for cap in range(0, (maxd or 0) + 1):
        filtered_tokengraph = filter_tokengraph_by_aat_depth(result.tokengraph, cap)
        filtered_result = SimpleNamespace(
            tokengraph=filtered_tokengraph, verbalunits=result.verbalunits
        )
        graph, warnings = aatgraph([sentence], [filtered_result])
        assert warnings == [], f"{slug} cap={cap}: {warnings}"
        node_ids = {n.id for n in graph.nodes}
        for node in graph.nodes:
            if node.related_node is not None:
                assert node.related_node in node_ids, (
                    f"{slug} cap={cap}: {node.id} ({node.role}) points at "
                    f"{node.related_node!r}, which isn't in the filtered graph"
                )


def test_filtering_at_or_beyond_max_aat_depth_matches_unfiltered():
    sentence, result = _sentence_and_result(
        "depth_two_cum_sciret_peccavisse_doluit", citation="Livy 1.1"
    )
    maxd = max_aat_depth(result.tokengraph)

    unfiltered_graph, unfiltered_warnings = aatgraph([sentence], [result])

    filtered_tokengraph = filter_tokengraph_by_aat_depth(result.tokengraph, maxd)
    filtered_result = SimpleNamespace(tokengraph=filtered_tokengraph, verbalunits=result.verbalunits)
    filtered_graph, filtered_warnings = aatgraph([sentence], [filtered_result])

    assert filtered_warnings == unfiltered_warnings == []
    assert {n.id for n in filtered_graph.nodes} == {n.id for n in unfiltered_graph.nodes}


def test_filtering_to_depth_zero_keeps_only_root_actions_and_their_own_dependents():
    """aat_depth=0 on 'Hercules cum gregem perlustrasset, pergit ad
    proximam speluncam.' must drop perlustrasset's whole subordinate
    clause (perlustrasset itself, and gregem, its own target) but keep
    pergit (the independent action) and Hercules (its own agent) --
    mirroring test_dot.py's/test_mermaid_ranking.py's own aat_depth=0
    diagram-level tests, now at the AAT-graph level."""
    sentence, result = _sentence_and_result("unit_verb_hercules_cum", citation="Livy 1.7")
    filtered_tokengraph = filter_tokengraph_by_aat_depth(result.tokengraph, 0)
    filtered_result = SimpleNamespace(tokengraph=filtered_tokengraph, verbalunits=result.verbalunits)
    graph, warnings = aatgraph([sentence], [filtered_result])
    assert warnings == []
    assert {n.id for n in graph.nodes} == {"t5", "t0"}
