"""
DSPy program that analyzes the syntax of a Latin passage according to the scheme documented in syntax_model.md: a table of verbal expressions, plus a token-level dependency graph.
 
This module covers only the analysis stage:
  1. SyntaxAnalysis -- a dspy.Signature that takes a passage plus its pre-segmented token list and produces `verbalunits` and `tokengraph`, using the ids handed to it.
  2. validate()   -- a light sanity check that every id the LM refers to in its output actually exists in the input token list, so malformed output is easy to spot.
 
Tokens are no longer produced here. The old deterministic tokenizer.py has
been retired; tokens now come from segmentation_dspy.py's LLM-driven,
citation-aware segmentation stage. See pipeline.py for the module that ties
the two stages together, including its analyze_passage() convenience
wrapper (the replacement for the function that used to live in this file).
 
Run this file directly for a quick smoke test against the configured LM:
    python latin_syntax_dspy.py
 
For tests that don't need network access to the school proxy, see the
`tests/` directory, which drives this signature with dspy's DummyLM.
"""
 
from typing import List
 
import dspy
 
from .models import Token, VerbalExpression, TokenAnalysis
 
 
# ---------------------------------------------------------------------------
# Signature
# ---------------------------------------------------------------------------
 
class SyntaxAnalysis(dspy.Signature):
    """Analyze the syntax of a passage of Latin according to a two-part scheme:
 
    (1) a list of verbal expressions. Three constructions count as a verbal
        expression: finite verbs, infinitives, and participles.
 
        - A finite verb (including compound perfect/pluperfect passive forms
          of participle + a form of 'sum') is always a verbal expression.
          Classify its syntactic type as 'independent' (main/principal),
          'dependent' (subordinate, introduced by a subordinating word),
          'direct quote' (occurring in directly quoted speech framed by
          another verb, e.g. "est" in `"Tuum est," inquit, "Servi regnum."`),
          or 'aside' (a verbal expression that interrupts the surrounding
          syntax, e.g. "dixerim" in "pace dixerim deum" interrupting "eos...
          spero").
        - An infinitive is a verbal expression only when part of an indirect
          statement; its syntactic type is always 'indirect statement'. In a
          compound future-infinitive form (participle + a form of 'sum',
          e.g. "facturum...fuisse"), the form of 'sum' anchors the verbal
          expression, same as a compound passive.
        - A participle is a verbal expression only when it has a *predicate*
          sense (e.g. an ablative-absolute-like "Anco regnante Lucumo...",
          'while Ancus was reigning') rather than a purely *attributive*
          sense (modifying a noun like an ordinary adjective, e.g.
          "consentiens laus", 'universal praise' -- NOT a verbal expression
          at all). Use 'dependent' as its syntactic type.
 
        Classify each verbal expression's semantic type too (transitive
        active/transitive passive/intransitive/linking verb).
 
    (2) a token-by-token dependency graph. For each token, record up to two
        relations to other tokens (by id), using only these relation labels:
 
        - unit verb (independent): every INDEPENDENT verb has relatedtoken1
          = the special sentinel string 'root' -- never an actual token id;
          no real token may be assigned the id 'root' -- and relationship1 =
          'unit verb'.
        - unit verb (dependent) / subordinating conjunction / relative
          pronoun: the verb of a DEPENDENT clause has relatedtoken1 -> the
          id of its subordinating conjunction or relative pronoun,
          relationship1 = 'unit verb'. That conjunction or pronoun in turn
          has relatedtoken1 -> the id of the verb of the clause it is
          subordinate to, with relationship1 = 'subordinating conjunction'
          for a conjunction, or relatedtoken1 -> its antecedent's id with
          relationship1 = 'relative pronoun' for a relative pronoun.
        - coordinating conjunction: when a coordinating conjunction (e.g.
          'et', '-que') joins a pair of adjectives, nouns, or prepositional
          phrases, it has relatedtoken1 -> the id of the first joined
          token, relatedtoken2 -> the id of the second, with BOTH
          relationship1 and relationship2 = 'coordinating conjunction' (not
          an overflow slot here -- this is the one relation that genuinely
          uses relatedtoken1 and relatedtoken2 for two ends of the same
          relation at once). When it joins two verbal expressions instead,
          relatedtoken1/relatedtoken2 are the ids of the two verbs (or, for
          an infinitive/participle-anchored verbal expression, the id that
          anchors it) rather than of nearby nouns -- go by which verbal
          expression the conjunction functionally introduces, NOT by which
          token it happens to be adjacent to or (for an enclitic like
          '-que') physically attached to; those can differ (e.g. an
          enclitic conjunction attached to the second clause's direct
          object still relates the two VERBS, not the object). If the
          conjunction opens an entirely new sentence with no explicit verb
          to its left to pair with, set only relatedtoken1/relationship1 (->
          the verb it introduces); do not invent a link to an implied
          preceding clause. 'et' specifically can also function as a plain
          adverb ('even', 'also') rather than a conjunction -- when it
          does, treat it like any other adverb: relatedtoken1 -> the verb
          or (if there is none, e.g. a verbless exclamation) the nearest
          token it emphasizes, relationship1 = 'adverbial', not
          'coordinating conjunction'.
        - direct quote / aside: a verbal expression of syntactic type
          'direct quote' or 'aside' has relatedtoken1 -> the id of the verb
          of the clause it interrupts or is framed by, relationship1 =
          'direct quote' or 'aside' respectively (matching its syntactic
          type).
        - circumstantial participle / ablative absolute: a participial
          verbal expression's own relatedtoken1 -> the id of the noun or
          pronoun it agrees with, relationship1 = 'circumstantial
          participle'. That noun in turn: if it also fits a normal role in
          the surrounding clause (e.g. it's already the main verb's direct
          object), it takes THAT normal relation instead (nothing extra to
          add). If it's an ablative with no other syntactic connection to
          the sentence (a true ablative absolute), it instead has
          relatedtoken1 -> the id of the main verb, relationship1 =
          'ablative absolute'.
        - auxiliary: in a compound perfect/pluperfect passive, or compound
          future-infinitive, verb form (participle + a form of 'sum'), the
          form of 'sum' anchors the verbal expression and is the target of
          every relation into it (subject, direct object, agent, etc); the
          participle itself has relatedtoken1 -> the id of that form of
          'sum', relationship1 = 'auxiliary'. The same pattern applies to an
          impersonal passive of an intransitive verb (e.g. "ventum erat",
          'there had been a coming'): the participle still relates to the
          form of 'sum' as its auxiliary, even with no subject.
        - agent: the preposition 'a'/'ab' introducing the agent of a passive
          verb has relatedtoken1 -> the passive verb's id (the id of the
          form of 'sum', for a compound form), relationship1 = 'agent'. The
          noun/pronoun governed by that 'a'/'ab' has relatedtoken1 -> the id
          of 'a'/'ab', relationship1 = 'object of preposition'.
        - subject / direct object / predicate: a noun or pronoun serving as
          subject or direct object has relatedtoken1 -> the id of the verb
          (the id of the form of 'sum', for a compound passive or
          future-infinitive form), relationship1 = 'subject' or 'direct
          object'. This applies to the accusative subject of an infinitive
          in indirect statement too. A noun or pronoun serving as the
          predicate complement of a LINKING verb uses relationship1 =
          'predicate' instead, same relatedtoken1 target. If the token is a
          relative pronoun already using relatedtoken1/relationship1 for its
          antecedent link, put this relation in relatedtoken2/relationship2
          instead.
        - adjectival: an adjective (or an attributive participle) modifying
          a noun has relatedtoken1 -> the noun's id, relationship1 =
          'adjectival'. An adjective used as a substantive (standing in for
          a noun) is treated as a noun/pronoun instead, not as adjectival.
        - genitive / dative / ablative: a noun in the genitive, dative, or
          ablative case that depends on a verb or another noun -- and isn't
          already covered by a more specific relation above (subject,
          direct object, object of preposition, ablative absolute, etc) --
          has relatedtoken1 -> the id of the verb or noun it depends on,
          relationship1 = the matching case name ('genitive', 'dative', or
          'ablative'). These are purely syntactic (case-function) labels,
          not semantic ones -- don't distinguish e.g. possessive vs.
          partitive genitive.
        - prepositional phrases: the preposition has relatedtoken1 -> the id
          of the verb (adverbial) or noun (attributive) it modifies,
          relationship1 = 'adverbial' or 'attributive'. The noun/pronoun it
          governs has relatedtoken1 -> the id of the preposition,
          relationship1 = 'object of preposition' (or relatedtoken2/
          relationship2 if relatedtoken1 is already used for a
          relative-pronoun link).
        - adverbial (bare adverb): an adverb modifying a verb has
          relatedtoken1 -> the verb's id, relationship1 = 'adverbial' --
          the same relationship1 value as a preposition modifying a verb,
          just with no object-of-preposition token on the other end.
 
        Only assign relations described above. Leave relatedtoken/
        relationship fields unset for tokens with no relation of these
        kinds -- not every token will have one (e.g. apposition and a bare
        accusative of place aren't covered). Use only the token ids given in
        the input `tokens` list, or the sentinel 'root', in your output;
        never invent new ids.
    """
 
    passage: str = dspy.InputField(desc="The Latin passage to analyze, exactly as written.")
    tokens: List[Token] = dspy.InputField(
        desc="Pre-segmented tokens of the passage, in order, with fixed ids. Reference these ids in your output; do not create new ones."
    )
    verbalunits: List[VerbalExpression] = dspy.OutputField(
        desc="One entry per verbal expression (finite verb; infinitive used in indirect speech; or predicate-sense participle) in the passage."
    )
    tokengraph: List[TokenAnalysis] = dspy.OutputField(
        desc="One entry per token in `tokens`, in the same order, with its type and any relations."
    )
 
 
analyze = dspy.ChainOfThought(SyntaxAnalysis)
 
 
# ---------------------------------------------------------------------------
# Runner + validation
# ---------------------------------------------------------------------------
 
def validate(tokens: List[Token], result) -> List[str]:
    """Check that every id the LM produced actually exists among `tokens`.
    Returns a list of human-readable problem descriptions (empty if clean).
 
    'root' is a special sentinel value for an independent verb's own
    relatedtoken1 (see SyntaxAnalysis's docstring) -- it is never treated as
    an unknown id, but syntax_model.md also requires that no actual token
    ever be assigned the id 'root', so that's checked here too."""
    valid_ids = {t.id for t in tokens}
    problems = []
 
    if "root" in valid_ids:
        problems.append(
            "token id 'root' is reserved as the sentinel relatedtoken1 "
            "value for independent verbs and must not be assigned to an "
            "actual token"
        )
 
    for tok in result.tokengraph:
        if tok.id not in valid_ids:
            problems.append(f"tokengraph entry has unknown id {tok.id!r}")
        for field in ("relatedtoken1", "relatedtoken2"):
            val = getattr(tok, field)
            if val is not None and val != "root" and val not in valid_ids:
                problems.append(f"token {tok.id!r} {field}={val!r} is not a known token id")
 
    for vu in result.verbalunits:
        if vu.id not in valid_ids:
            problems.append(f"verbal expression id {vu.id!r} is not a known token id")
 
    return problems
 
 
def print_analysis(tokens: List[Token], result):
    print("Tokens:")
    for t in tokens:
        print(f"  {t.id:>4}  {t.text}")
 
    print("\nVerbal expressions:")
    for vu in result.verbalunits:
        print(f"  id={vu.id}  syntactic_type={vu.syntactic_type}  semantic_type={vu.semantic_type}")
 
    print("\nToken graph:")
    for tok in result.tokengraph:
        rels = []
        if tok.relationship1:
            rels.append(f"{tok.relationship1} -> {tok.relatedtoken1}")
        if tok.relationship2:
            rels.append(f"{tok.relationship2} -> {tok.relatedtoken2}")
        rel_str = "; ".join(rels) if rels else "-"
        vu_str = f" [verbal unit {tok.verbalunitid}]" if tok.verbalunitid else ""
        print(f"  {tok.id:>4}  {tok.token:<15} type={tok.tokentype:<11} lemma={tok.lemma or '-':<15} {rel_str}{vu_str}")