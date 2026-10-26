"""
Bridge from arsgrammatica's own Latin syntax analysis (models.py's
VerbalExpression/TokenAnalysis scheme, quarto/concepts/) to the
Agent-Action-Target (AAT) model implemented by the separate `aat` package
(https://github.com/neelsmith/aat, docs at
https://neelsmith.github.io/aat/aat.html).

`aat` already ships a DSPy pipeline that produces an AATGraph directly
from English text (aat.english) -- there, the LM is asked to emit
agent/action/target nodes itself. arsgrammatica's own Latin pipeline
predates and doesn't use that model at all: it produces a much richer,
Latin-specific relational graph (models.py's TokenAnalysis/
VerbalExpression, with its full case/relation inventory) with no
notion of "agent"/"target" built in. `aatgraph()`, below, is the
converter: given an already-completed arsgrammatica analysis, it derives
an AATGraph from it, applying (to Latin) the same role rules aat.english's
own DSPy signature documents for English (see
AgentActionTarget.__doc__ in the installed `aat` package):

  - every verbal expression (VerbalExpression -- a finite verb, an
    indirect-statement infinitive, a circumstantial participle, or a
    gerundive) is an
    *action*. A compound verbal expression (participle + a form of *sum*)
    becomes one action node, anchored at arsgrammatica's own compound-form
    id (per VerbalExpression.id's docstring, the participle or infinitive
    itself -- e.g. "condita" in "condita est" -- rather than AAT's own
    English convention of the most specific/final component; arsgrammatica's
    anchor-id convention is kept as-is here rather than re-derived, since
    it's already what the rest of this codebase treats as authoritative and
    the choice makes no difference to referential validity), with `value`
    set to every component token's own text joined by spaces in surface
    order (e.g. "condita est").
  - a verbal expression that is NOT an independent, root-level clause is
    *subordinated* to its governing verbal expression (`related_node` set
    to that governing action's own id), via
    `verbal_units.find_governing_verbal_expression()`.
  - agent and target follow the A-A-T section of
    quarto/concepts/syntactic-analysis.qmd, which states them by VOICE:
    - active and deponent verbs: the 'subject' is the agent; a 'direct
      object' is the target; the 'predicate' of a linking verb (use 1 on
      that page) is the target. A 'predicate' of role or state (use 2) or
      a predicate of the direct object (use 3, which relates to the object,
      not the verb) is not a target.
    - passive (non-deponent) verbs, including a gerundive + *sum*: the
      'subject' is the target; 'agent-ablative' or 'agent-dative' gives the
      agent; a 'predicate' (use 4, e.g. "Cicero consul creatus est") is a
      target too. For 'agent-ablative', the relation sits on the
      preposition ("a"/"ab"), so the agent node is the noun its 'object of
      preposition' relation points at.
    The scheme no longer records voice (semantic types were retired), so
    `_voice()` infers it from the analysis: a verbal expression with an
    'agent-ablative'/'agent-dative' dependent, or a gerundive anchor, is
    passive; one whose lemma ends in "-or" (the dictionary form of a
    deponent verb) is active; a compound form with an 'auxiliary', or a
    form ending in -tur/-ntur, is otherwise passive; everything else is
    active. A verbal expression is a linking verb if its lemma is *sum*
    (or *fio*) or it is an implied *sum*. These are heuristics: see
    notes/model_switch_questions.md.
  - an agent/target candidate whose own token is an implied/elided token
    (models.py's IMPLIED_TOKENTYPES -- an "implied substantive"
    standing in for a participle's unexpressed antecedent) is skipped
    entirely, rather than given an AATNode with a placeholder value --
    matching aat.english's own "either may be absent if the passage
    doesn't express one" convention. An implied ACTION anchor (an
    "implied sum" or "implied verb" verbal expression, which --
    unlike an implied agent/target -- arsgrammatica does still list in
    `verbalunits`) is NOT skipped: it still becomes its own action node
    (aat.english's model has no equivalent gap to model, since English
    text never elides its own verb the way Latin does), using
    `mermaid.token_label()`'s own placeholder text ("elided sum",
    "implied verb", ...) as `value`, so the node's `value` is never
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
`aatgraph()`'s return value) rather than a raised error, noting which
citation was used for the whole sentence.
"""

from typing import List, Optional, Tuple

from aat.core import AATGraph, AATNode

from .mermaid import token_label
from .models import IMPLIED_TOKENTYPES, Sentence, TokenAnalysis
from .verbal_units import find_governing_verbal_expression

import re

_LINKING_LEMMAS = {"sum", "fio"}
_PASSIVE_ENDING = re.compile(r"(tur|ntur)$")
_GERUNDIVE_ENDING = re.compile(r"nd(us|a|um|i|ae|o|am|os|as|is|orum|arum)$")


def _sentence_context(sentence: Sentence, warnings: List[str], index: int) -> str:
    """This sentence's shared AAT context: its first token's citation, or
    "" if it has no tokens or that token's citation is unset. Appends a
    warning (naming the sentence by its position, 1-based, in the
    `sentences` list `aatgraph()` was called with) if its tokens span more
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
    preposition' -- for an 'agent-ablative' relation, which sits on the
    preposition a/ab, this is the actual agent noun."""
    for tok in tokengraph:
        if preposition_id in tok.related_ids("object of preposition"):
            return tok
    return None


def _dependents(anchor_id: str, tokengraph: List[TokenAnalysis]):
    """Every (token, relationship) pair relating directly to `anchor_id`."""
    return [
        (tok, relation.relationship)
        for tok in tokengraph
        for relation in tok.relations
        if relation.related == anchor_id
    ]


def _voice(anchor: TokenAnalysis, syntactic_type: str, dependents) -> str:
    """'active' or 'passive' for the verbal expression anchored on `anchor`,
    inferred from the analysis (see this module's docstring)."""
    labels = {label for _tok, label in dependents}
    if "agent-ablative" in labels or "agent-dative" in labels:
        return "passive"
    text = (anchor.token or "").lower()
    if syntactic_type == "gerundive" or _GERUNDIVE_ENDING.search(text):
        return "passive"
    lemma = (anchor.lemma or "").lower()
    if lemma.endswith("or"):
        return "active"  # deponent
    if "auxiliary" in labels or _PASSIVE_ENDING.search(text):
        return "passive"
    return "active"


def _is_linking(anchor: TokenAnalysis) -> bool:
    return anchor.tokentype == "implied sum" or (anchor.lemma or "").lower() in _LINKING_LEMMAS


def _role_for_relation(label: str, voice: str, linking: bool) -> Optional[str]:
    """AAT role ('agent'/'target') for a token relating to a verbal
    expression's anchor via `label`, or None."""
    if label == "subject":
        return "target" if voice == "passive" else "agent"
    if label == "direct object":
        return "target" if voice == "active" else None
    if label in ("agent-ablative", "agent-dative"):
        return "agent"
    if label == "predicate":
        return "target" if (linking or voice == "passive") else None
    return None


def _component_ids(anchor_id: str, tokengraph: List[TokenAnalysis]) -> List[str]:
    """`anchor_id` plus every token that relates to it via "auxiliary" --
    the components of a compound verbal expression (e.g. "est" ->
    "condita"; see this module's docstring)."""
    ids = [anchor_id]
    for tok in tokengraph:
        if anchor_id in tok.related_ids("auxiliary"):
            ids.append(tok.id)
    return ids


def aatgraph(sentences: List[Sentence], results: list) -> Tuple[AATGraph, List[str]]:
    """Build an `aat.core.AATGraph` from an already-completed
    arsgrammatica analysis -- `sentences`/`results`, in the exact shape
    `pipeline.analyze_sources()` (or `analyze_string()`) returns them:
    `results[i]` is the SentenceAnalysis result (with its own `.tokengraph`
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

            dependents = _dependents(anchor_id, tokengraph)
            voice = _voice(by_id[anchor_id], vu.syntactic_type, dependents)
            linking = _is_linking(by_id[anchor_id])
            seen_role_token_ids: set = set()
            for tok, label in dependents:
                role = _role_for_relation(label, voice, linking)
                if role is None:
                    continue

                if label == "agent-ablative":
                    role_tok = _object_of_preposition(tok.id, tokengraph)
                    if role_tok is None:
                        warnings.append(
                            f"sentence {index + 1}: {tok.id!r} relates to "
                            f"{anchor_id!r} as 'agent-ablative' but has no "
                            "'object of preposition' dependent -- skipping "
                            "its agent node"
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
