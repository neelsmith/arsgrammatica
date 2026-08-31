"""
Bridge from arsgrammatica's own Latin syntax analysis (models.py's
VerbalExpression/TokenAnalysis scheme, syntax_model.md) to the
Agent-Action-Target (AAT) model implemented by the separate `aat` package
(https://github.com/neelsmith/aat, docs at
https://neelsmith.github.io/aat/aat.html).

`aat` already ships a DSPy pipeline that produces an AATGraph directly
from English text (aat.english) -- there, the LM is asked to emit
agent/action/target nodes itself. arsgrammatica's own Latin pipeline
predates and doesn't use that model at all: it produces a much richer,
Latin-specific relational graph (models.py's TokenAnalysis/
VerbalExpression, syntax_model.md's full case/relation inventory) with no
notion of "agent"/"target" built in. `attgraph()`, below, is the
converter: given an already-completed arsgrammatica analysis, it derives
an AATGraph from it, applying (to Latin) the same role rules aat.english's
own DSPy signature documents for English (see
AgentActionTarget.__doc__ in the installed `aat` package):

  - every verbal expression (VerbalExpression -- a finite verb, an
    indirect-statement infinitive, or a predicate-sense participle) is an
    *action*. A compound verbal expression (participle + a form of *sum*)
    becomes one action node, anchored at arsgrammatica's own compound-form
    id (per VerbalExpression.id's docstring, the form of *sum* -- e.g.
    "est" in "condita est" -- rather than AAT's own English convention of
    the most specific/final component; arsgrammatica's anchor-id
    convention is kept as-is here rather than re-derived, since it's
    already what the rest of this codebase treats as authoritative and
    the choice makes no difference to referential validity), with `value`
    set to every component token's own text joined by spaces in surface
    order (e.g. "condita est").
  - a verbal expression that is NOT an independent, root-level clause is
    *subordinated* to its governing verbal expression (`related_node` set
    to that governing action's own id), via
    `verbal_units.find_governing_verbal_expression()`.
  - the *agent* of a transitive-active, intransitive, or linking verb is
    its "subject"-related token; the agent of a transitive-passive verb is
    its ablative-of-agent phrase -- syntax_model.md's "agent" relation
    label sits on the preposition ("a"/"ab"), not the noun, so the actual
    agent node is the noun the preposition's own "object of preposition"
    relation points at (see this module's docstring below and
    gold_examples.py's urbs_a_romulo_condita_answer fixture for the
    worked case).
  - the *target* of a transitive-active verb is its "direct object"-
    related token; the target of a transitive-passive verb is its
    "subject"-related token (the surface subject of a passive verb is
    always its underlying direct object); the target of a linking verb is
    its "predicate"-related token (its predicate nominative/adjective) --
    this last rule isn't stated in the user's own instructions, but
    matches aat.english's own documented convention ("target: ... the
    predicate of a linking verb") and "Latin will work much like the
    English examples" was the explicit brief, so it's included here; flag
    it if a predicate complement should instead get no AAT role at all.
  - an agent/target candidate whose own token is an implied/elided token
    (models.py's IMPLIED_TOKENTYPES -- most often an "implied subject"
    standing in for a participle's unexpressed antecedent) is skipped
    entirely, rather than given an AATNode with a placeholder value --
    matching aat.english's own "either may be absent if the passage
    doesn't express one" convention. An implied ACTION anchor (an
    "implied sum" or "continued discourse" verbal expression, which --
    unlike an implied agent/target -- arsgrammatica does still list in
    `verbalunits`) is NOT skipped: it still becomes its own action node
    (aat.english's model has no equivalent gap to model, since English
    text never elides its own verb the way Latin does), using
    `mermaid.token_label()`'s own placeholder text ("elided sum",
    "continued discourse", ...) as `value`, so the node's `value` is never
    empty (aat.core.validate.validate() requires this).

`AATGraph`/`AATNode` require every node to carry a `context` (aat's
per-passage identifier, e.g. a CTS URN) and use it, together with `id`, as
the referential key `validate()` checks -- but arsgrammatica's own
TokenAnalysis has no citation field at all (only the original Token
objects in `Sentence.tokens` do, and only for real, non-implied tokens).
Rather than trying to assign each individual node its own precise
citation (impossible for an implied token with no original Token at all,
and awkward for a subordinate clause's governing link crossing a
citation boundary -- both arise in this corpus, e.g. "Cumque venissent in
eam, pertransivit Abram..." spans Genesis 12.5 -> 12.6), every node
derived from one Sentence shares ONE context: that sentence's own first
token's citation (or "" if the sentence has no tokens, or its first
token's citation is None). This keeps every `related_node` link
(subordination, and every agent/target's link to its action) valid,
since arsgrammatica's segmentation never lets a relation cross a sentence
boundary -- the one thing AAT's context-scoped id space actually needs.
A sentence whose tokens span more than one citation gets a warning (see
`attgraph()`'s return value) rather than a raised error, noting which
citation was used for the whole sentence.
"""

from typing import List, Optional, Tuple

from aat.core import AATGraph, AATNode

from .mermaid import token_label
from .models import IMPLIED_TOKENTYPES, Sentence, TokenAnalysis
from .verbal_units import find_governing_verbal_expression

_AGENT_RELATIONS = {"subject", "agent"}
_TARGET_RELATIONS = {"direct object", "subject", "predicate"}


def _sentence_context(sentence: Sentence, warnings: List[str], index: int) -> str:
    """This sentence's shared AAT context: its first token's citation, or
    "" if it has no tokens or that token's citation is unset. Appends a
    warning (naming the sentence by its position, 1-based, in the
    `sentences` list `attgraph()` was called with) if its tokens span more
    than one distinct citation, since only the first one is used."""
    if not sentence.tokens:
        return ""
    context = sentence.tokens[0].citation or ""
    distinct = {tok.citation for tok in sentence.tokens if tok.citation is not None}
    if len(distinct) > 1:
        warnings.append(
            f"sentence {index + 1} spans citations {sorted(distinct)!r} -- "
            f"using {context!r} (its first token's citation) as the "
            "context for every AAT node derived from it"
        )
    return context


def _object_of_preposition(
    preposition_id: str, tokengraph: List[TokenAnalysis]
) -> Optional[TokenAnalysis]:
    """The token that relates to `preposition_id` via 'object of
    preposition' -- syntax_model.md's convention for a passive verb's
    ablative-of-agent phrase (see this module's docstring): the "agent"
    relation label sits on the preposition itself, so the real agent noun
    is one hop further out, via this relation."""
    for tok in tokengraph:
        for related_field, label_field in (
            ("relatedtoken1", "relationship1"),
            ("relatedtoken2", "relationship2"),
        ):
            if (
                getattr(tok, label_field) == "object of preposition"
                and getattr(tok, related_field) == preposition_id
            ):
                return tok
    return None


def _role_for_relation(label: Optional[str], semantic_type: Optional[str]) -> Optional[str]:
    """AAT role ('agent'/'target') a token relating to a verbal
    expression's anchor via `label` should take, given that verb's own
    `semantic_type` -- or None if this relation label/semantic-type
    combination doesn't correspond to any AAT role at all (e.g. "direct
    object" on an intransitive verb, which shouldn't occur but isn't this
    function's job to police)."""
    if label == "subject":
        return "target" if semantic_type == "transitive passive" else "agent"
    if label == "direct object":
        return "target" if semantic_type == "transitive active" else None
    if label == "agent":
        return "agent" if semantic_type == "transitive passive" else None
    if label == "predicate":
        return "target" if semantic_type == "linking verb" else None
    return None


def _component_ids(anchor_id: str, tokengraph: List[TokenAnalysis]) -> List[str]:
    """`anchor_id` plus every token that relates to it via "auxiliary" --
    the components of a compound verbal expression (e.g. "condita" ->
    "est"; see this module's docstring)."""
    ids = [anchor_id]
    for tok in tokengraph:
        for related_field, label_field in (
            ("relatedtoken1", "relationship1"),
            ("relatedtoken2", "relationship2"),
        ):
            if (
                getattr(tok, label_field) == "auxiliary"
                and getattr(tok, related_field) == anchor_id
            ):
                ids.append(tok.id)
    return ids


def attgraph(sentences: List[Sentence], results: list) -> Tuple[AATGraph, List[str]]:
    """Build an `aat.core.AATGraph` from an already-completed
    arsgrammatica analysis -- `sentences`/`results`, in the exact shape
    `pipeline.analyze_sources()` (or `analyze_passage()`) returns them:
    `results[i]` is the SyntaxAnalysis result (with its own `.tokengraph`
    and `.verbalunits`) for `sentences[i]`, same order, one entry per
    sentence.

    Returns `(graph, warnings)` -- `warnings` follows this codebase's
    usual "degrade visibly, don't raise" convention (see
    `verbal_units.compute_subordination_depths()`): a sentence whose
    tokens span more than one citation, or a verbal expression missing
    its own `verbalunits` entry (shouldn't happen in well-formed output,
    but this function doesn't assume it), is reported here rather than
    raising. An empty list means nothing unusual was found -- not that
    the underlying Latin analysis itself is correct; run the resulting
    graph through `aat.core.validate.validate()` (with a matching
    `CitableToken` list) for that.

    Every action, agent, and target node this function can derive is
    documented in this module's own docstring, above.
    """
    warnings: List[str] = []
    nodes: List[AATNode] = []

    for index, (sentence, result) in enumerate(zip(sentences, results)):
        tokengraph = result.tokengraph
        verbalunits = result.verbalunits

        context = _sentence_context(sentence, warnings, index)
        by_id = {tok.id: tok for tok in tokengraph}
        order_index = {tok.id: i for i, tok in enumerate(tokengraph)}
        anchor_ids = sorted(
            (tok.id for tok in tokengraph if tok.verbalunitid == tok.id),
            key=lambda tid: order_index.get(tid, -1),
        )
        vu_by_id = {vu.id: vu for vu in verbalunits}
        governing = find_governing_verbal_expression(tokengraph)

        for anchor_id in anchor_ids:
            vu = vu_by_id.get(anchor_id)
            if vu is None:
                warnings.append(
                    f"sentence {index + 1}: anchor {anchor_id!r} has no "
                    "matching entry in verbalunits -- skipping its action "
                    "(and any agent/target) node"
                )
                continue

            component_ids = sorted(
                set(_component_ids(anchor_id, tokengraph)),
                key=lambda tid: order_index.get(tid, -1),
            )
            value = " ".join(token_label(by_id[tid]) for tid in component_ids)

            nodes.append(
                AATNode(
                    context=context,
                    id=anchor_id,
                    value=value,
                    role="action",
                    related_node=governing.get(anchor_id),
                )
            )

            semantic_type = vu.semantic_type
            seen_role_token_ids: set = set()
            for tok in tokengraph:
                for related_field, label_field in (
                    ("relatedtoken1", "relationship1"),
                    ("relatedtoken2", "relationship2"),
                ):
                    label = getattr(tok, label_field)
                    target_id = getattr(tok, related_field)
                    if target_id != anchor_id:
                        continue
                    role = _role_for_relation(label, semantic_type)
                    if role is None:
                        continue

                    if label == "agent":
                        role_tok = _object_of_preposition(tok.id, tokengraph)
                        if role_tok is None:
                            warnings.append(
                                f"sentence {index + 1}: {tok.id!r} relates to "
                                f"{anchor_id!r} as 'agent' but has no 'object "
                                "of preposition' dependent -- skipping its "
                                "agent node"
                            )
                            continue
                    else:
                        role_tok = tok

                    if role_tok.tokentype in IMPLIED_TOKENTYPES:
                        continue
                    if role_tok.id in seen_role_token_ids:
                        continue
                    seen_role_token_ids.add(role_tok.id)

                    nodes.append(
                        AATNode(
                            context=context,
                            id=role_tok.id,
                            value=token_label(role_tok),
                            role=role,
                            related_node=anchor_id,
                        )
                    )

    return AATGraph(nodes=nodes), warnings
