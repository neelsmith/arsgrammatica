"""
Gold-annotated example sentences for arsgrammatica's test suite.
 
Each GoldExample pairs a Latin passage with a hand-written, notes.md-correct
`canned_answer` -- the same dict shape dspy.utils.dummies.DummyLM expects,
and the same shape a dspy.Example's outputs will eventually take if these
feed a GEPA trainset later. `tags` names the relation(s)/construction the
example is meant to exercise; test_coverage.py checks that every
RelationLabel in models.py has at least one tagged example.
 
Add new examples here, not in the test files -- test_gold_examples.py,
test_coverage.py, and test_validate.py all read GOLD_EXAMPLES rather than
defining their own fixtures.
"""
 
from dataclasses import dataclass
from typing import Any
 
 
@dataclass
class GoldExample:
    slug: str
    passage: str
    tags: list[str]
    canned_answer: dict[str, Any]
 
 
# ---------------------------------------------------------------------------
# "Hercules cum gregem perlustrasset, pergit ad proximam speluncam."
#   t0 Hercules  t1 cum  t2 gregem  t3 perlustrasset  t4 ,
#   t5 pergit    t6 ad   t7 proximam  t8 speluncam    t9 .
#
# syntax_model.md's own worked example for "unit verb" / "subordinating
# conjunction". Moved here unchanged from the original test_pipeline.py,
# other than adding pergit's relatedtoken1="root"/relationship1="unit verb"
# once syntax_model.md's "root" convention for independent verbs was added.
# ---------------------------------------------------------------------------
 
_HERCULES_ANSWER = {
    "reasoning": (
        "perlustrasset is the dependent verb of the cum-clause, linked to cum as "
        "its unit verb; cum is the subordinating conjunction linked to the main "
        "verb pergit; gregem is the direct object of perlustrasset; Hercules is "
        "the subject of pergit; ad is an adverbial preposition modifying pergit, "
        "governing speluncam as its object; pergit, being independent, has the "
        "sentinel relation1 'root'."
    ),
    "verbalunits": [
        {"id": "t3", "syntactic_type": "dependent", "semantic_type": "transitive active"},
        {"id": "t5", "syntactic_type": "independent", "semantic_type": "intransitive"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Hercules", "tokentype": "lexical", "lemma": "Hercules",
         "relatedtoken1": "t5", "relationship1": "subject"},
        {"id": "t1", "token": "cum", "tokentype": "lexical", "lemma": "cum",
         "relatedtoken1": "t5", "relationship1": "subordinating conjunction"},
        {"id": "t2", "token": "gregem", "tokentype": "lexical", "lemma": "grex",
         "relatedtoken1": "t3", "relationship1": "direct object"},
        {"id": "t3", "token": "perlustrasset", "tokentype": "lexical", "lemma": "perlustro",
         "verbalunitid": "t3", "relatedtoken1": "t1", "relationship1": "unit verb"},
        {"id": "t4", "token": ",", "tokentype": "punctuation"},
        {"id": "t5", "token": "pergit", "tokentype": "lexical", "lemma": "pergo",
         "verbalunitid": "t5", "relatedtoken1": "root", "relationship1": "unit verb"},
        {"id": "t6", "token": "ad", "tokentype": "lexical", "lemma": "ad",
         "relatedtoken1": "t5", "relationship1": "adverbial"},
        {"id": "t7", "token": "proximam", "tokentype": "lexical", "lemma": "proximus"},
        {"id": "t8", "token": "speluncam", "tokentype": "lexical", "lemma": "spelunca",
         "relatedtoken1": "t6", "relationship1": "object of preposition"},
        {"id": "t9", "token": ".", "tokentype": "punctuation"},
    ],
}
 
# ---------------------------------------------------------------------------
# "arma virumque cano."
#   t0 arma  t1 virum  t2 que  t3 cano  t4 .
#
# syntax_model.md's own worked example for the *enclitic* token type: "the
# enclitic que in the phrase arma virumque cano." virumque splits into
# virum (lexical) + que (enclitic). cano is also syntax_model.md's own
# worked example for the "root" convention: "cano is an independent verb
# with relation1 value root, and relationship1 value unit verb."
#
# que is ALSO syntax_model.md's own worked example for *coordinating
# conjunction* joining a pair of nouns: "in arma virumque cano, the
# conjunction que will have the ids of arma and virum for relation1 and
# relation2, and coordinating conjunction for both relationship1 and
# relationship2." (Previously que was left with no relation at all --
# "the scheme has no documented relation type for a connective enclitic" --
# that was true before this revision added "coordinating conjunction".)
# ---------------------------------------------------------------------------

_ENCLITIC_ANSWER = {
    "reasoning": (
        "cano is the independent main verb (transitive active, 'I sing'), "
        "with the sentinel relation1 'root'; arma and virum -- joined by "
        "the enclitic -que ('and') -- are both its direct objects, and que "
        "itself is a coordinating conjunction relating the pair of them to "
        "each other (relation1 -> arma, relation2 -> virum)."
    ),
    "verbalunits": [
        {"id": "t3", "syntactic_type": "independent", "semantic_type": "transitive active"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "arma", "tokentype": "lexical", "lemma": "arma",
         "relatedtoken1": "t3", "relationship1": "direct object"},
        {"id": "t1", "token": "virum", "tokentype": "lexical", "lemma": "vir",
         "relatedtoken1": "t3", "relationship1": "direct object"},
        {"id": "t2", "token": "que", "tokentype": "enclitic",
         "relatedtoken1": "t0", "relationship1": "coordinating conjunction",
         "relatedtoken2": "t1", "relationship2": "coordinating conjunction"},
        {"id": "t3", "token": "cano", "tokentype": "lexical", "lemma": "cano",
         "verbalunitid": "t3", "relatedtoken1": "root", "relationship1": "unit verb"},
        {"id": "t4", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "M. Agrippa L. f. cos. tertium fecit."
#   t0 M.  t1 Agrippa  t2 L.  t3 f.  t4 cos.  t5 tertium  t6 fecit  t7 .
#
# syntax_model.md's own worked example (the Pantheon's actual dedicatory
# inscription), now given in full: "M." and "L." are *praenomen* tokens
# (abbreviated first names, Marcus and Lucius); "f." (filius, "son [of]")
# and "cos." (consul) are *abbreviation* tokens -- syntax_model.md documents
# these as two distinct token types. A previous revision of this fixture had
# to trim the sentence down to just "M. Tullius epistulam scripsit." because
# TokenAnalysis.tokentype had no "abbreviation" value yet; that gap is now
# closed in models.py, so this fixture uses the real sentence. None of "M.",
# "L.", "f.", or "cos." gets a relation of its own: the scheme has no
# documented relation type linking a praenomen or other abbreviation to the
# name/title it modifies.
# ---------------------------------------------------------------------------

_PRAENOMEN_ABBREVIATION_ANSWER = {
    "reasoning": (
        "fecit is the independent main verb ('he built/made', transitive "
        "active -- its direct object, the building itself, is understood "
        "from context and left implicit, as is typical of a dedicatory "
        "inscription), with the sentinel relation1 'root'. Agrippa (M. "
        "Agrippa L. f. cos., 'Marcus Agrippa, son of Lucius, consul') is "
        "its subject; tertium ('for the third time', modifying his term as "
        "consul) is adverbial, modifying fecit."
    ),
    "verbalunits": [
        {"id": "t6", "syntactic_type": "independent", "semantic_type": "transitive active"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "M.", "tokentype": "praenomen"},
        {"id": "t1", "token": "Agrippa", "tokentype": "lexical", "lemma": "Agrippa",
         "relatedtoken1": "t6", "relationship1": "subject"},
        {"id": "t2", "token": "L.", "tokentype": "praenomen"},
        {"id": "t3", "token": "f.", "tokentype": "abbreviation"},
        {"id": "t4", "token": "cos.", "tokentype": "abbreviation"},
        {"id": "t5", "token": "tertium", "tokentype": "lexical", "lemma": "tertium",
         "relatedtoken1": "t6", "relationship1": "adverbial"},
        {"id": "t6", "token": "fecit", "tokentype": "lexical", "lemma": "facio",
         "verbalunitid": "t6", "relatedtoken1": "root", "relationship1": "unit verb"},
        {"id": "t7", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "Hiberna aberant ab eo milia passuum XXV."
#   t0 Hiberna  t1 aberant  t2 ab  t3 eo  t4 milia  t5 passuum  t6 XXV  t7 .
#
# syntax_model.md's own worked example for the *numeral* token type:
# "XXV in the phrase hiberna aberant ab eo milia passuum XXV." milia,
# passuum, and XXV together form an accusative-of-extent phrase ("twenty-
# five thousand paces") with no relation type in the current scheme, so
# none of the three gets a relatedtoken/relationship -- same as que in the
# enclitic example above, per "Incomplete status".
# ---------------------------------------------------------------------------
 
_NUMERAL_ANSWER = {
    "reasoning": (
        "aberant is the independent main verb (intransitive, 'were "
        "distant'), with the sentinel relation1 'root'; Hiberna is its "
        "subject; ab is an adverbial preposition modifying aberant, "
        "governing eo as its object of preposition; milia passuum XXV "
        "('twenty-five thousand paces') is an accusative-of-extent phrase "
        "with no relation type in the current scheme."
    ),
    "verbalunits": [
        {"id": "t1", "syntactic_type": "independent", "semantic_type": "intransitive"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Hiberna", "tokentype": "lexical", "lemma": "hiberna",
         "relatedtoken1": "t1", "relationship1": "subject"},
        {"id": "t1", "token": "aberant", "tokentype": "lexical", "lemma": "absum",
         "verbalunitid": "t1", "relatedtoken1": "root", "relationship1": "unit verb"},
        {"id": "t2", "token": "ab", "tokentype": "lexical", "lemma": "ab",
         "relatedtoken1": "t1", "relationship1": "adverbial"},
        {"id": "t3", "token": "eo", "tokentype": "lexical", "lemma": "is",
         "relatedtoken1": "t2", "relationship1": "object of preposition"},
        {"id": "t4", "token": "milia", "tokentype": "lexical", "lemma": "mille"},
        {"id": "t5", "token": "passuum", "tokentype": "lexical", "lemma": "passus"},
        {"id": "t6", "token": "XXV", "tokentype": "numeral"},
        {"id": "t7", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "principes Albanorum in patres, ut ea quoque pars rei publicae cresceret, legit."
#   t0 principes  t1 Albanorum  t2 in     t3 patres    t4 ,
#   t5 ut         t6 ea         t7 quoque t8 pars      t9 rei
#   t10 publicae  t11 cresceret t12 ,     t13 legit    t14 .
#
# syntax_model.md's own worked example for the *independent* vs *dependent*
# syntactic_type distinction: "legit is an independent verbal expression,
# and cresceret is dependent (introduced by the subordinating conjunction
# ut)" -- and, in the same sentence, for *transitive active* (legit) vs
# *intransitive* (cresceret) semantic_type. Both syntactic types and both
# of these semantic types are already exercised elsewhere (unit_verb_
# hercules_cum), but this fixture ties coverage directly to the spec's own
# example sentence for this distinction, not just to any sentence that
# happens to produce the right values.
# ---------------------------------------------------------------------------
 
_SYNTACTIC_TYPE_ANSWER = {
    "reasoning": (
        "legit is the independent main verb (transitive active, 'he "
        "chose'), with the sentinel relation1 'root', principes Albanorum "
        "as its direct object, and in patres as an adverbial phrase "
        "(patres as in's object of preposition); cresceret is the "
        "dependent verb of the ut-clause (intransitive, 'might grow'), "
        "linked to ut as its unit verb, with pars as its subject."
    ),
    "verbalunits": [
        {"id": "t11", "syntactic_type": "dependent", "semantic_type": "intransitive"},
        {"id": "t13", "syntactic_type": "independent", "semantic_type": "transitive active"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "principes", "tokentype": "lexical", "lemma": "princeps",
         "relatedtoken1": "t13", "relationship1": "direct object"},
        {"id": "t1", "token": "Albanorum", "tokentype": "lexical", "lemma": "Albanus"},
        {"id": "t2", "token": "in", "tokentype": "lexical", "lemma": "in",
         "relatedtoken1": "t13", "relationship1": "adverbial"},
        {"id": "t3", "token": "patres", "tokentype": "lexical", "lemma": "pater",
         "relatedtoken1": "t2", "relationship1": "object of preposition"},
        {"id": "t4", "token": ",", "tokentype": "punctuation"},
        {"id": "t5", "token": "ut", "tokentype": "lexical", "lemma": "ut",
         "relatedtoken1": "t13", "relationship1": "subordinating conjunction"},
        {"id": "t6", "token": "ea", "tokentype": "lexical", "lemma": "is"},
        {"id": "t7", "token": "quoque", "tokentype": "lexical", "lemma": "quoque"},
        {"id": "t8", "token": "pars", "tokentype": "lexical", "lemma": "pars",
         "relatedtoken1": "t11", "relationship1": "subject"},
        {"id": "t9", "token": "rei", "tokentype": "lexical", "lemma": "res"},
        {"id": "t10", "token": "publicae", "tokentype": "lexical", "lemma": "publicus"},
        {"id": "t11", "token": "cresceret", "tokentype": "lexical", "lemma": "cresco",
         "verbalunitid": "t11", "relatedtoken1": "t5", "relationship1": "unit verb"},
        {"id": "t12", "token": ",", "tokentype": "punctuation"},
        {"id": "t13", "token": "legit", "tokentype": "lexical", "lemma": "lego",
         "verbalunitid": "t13", "relatedtoken1": "root", "relationship1": "unit verb"},
        {"id": "t14", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "urbs a Romulo condita est."
#   t0 urbs  t1 a  t2 Romulo  t3 condita  t4 est  t5 .
#
# syntax_model.md's own worked example for *transitive passive*
# semantic_type: "the compound verb condita est is transitive passive." Also
# the spec's own worked example for the *agent* relation (a/ab plus an
# ablative introduces the agent of a passive verb) AND, once syntax_model.md
# spelled out the *auxiliary* relation, its own worked example for that too:
# "if urbs a Romulo condita est is tokenized ... condita has for its
# relation1 the value t5 (est), and for relationship1, auxiliary." Per the
# compound-perfect-passive rule ("use the id of the form of sum"), the
# verbal expression and every relation into it (subject, agent) anchor on
# est (t4), not condita (t3) -- condita instead relates to est as its
# auxiliary, and est (being independent) gets the "root" sentinel.
# ---------------------------------------------------------------------------
 
_TRANSITIVE_PASSIVE_ANSWER = {
    "reasoning": (
        "condita est is a compound perfect passive verbal expression, "
        "anchored at the id of est (the form of sum) per the compound-form "
        "rule, with est carrying the sentinel relation1 'root' as an "
        "independent verb and condita relating to est as its auxiliary; "
        "urbs is its subject; a introduces the agent of the passive verb, "
        "with Romulo as a's object of preposition."
    ),
    "verbalunits": [
        {"id": "t4", "syntactic_type": "independent", "semantic_type": "transitive passive"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "urbs", "tokentype": "lexical", "lemma": "urbs",
         "relatedtoken1": "t4", "relationship1": "subject"},
        {"id": "t1", "token": "a", "tokentype": "lexical", "lemma": "a",
         "relatedtoken1": "t4", "relationship1": "agent"},
        {"id": "t2", "token": "Romulo", "tokentype": "lexical", "lemma": "Romulus",
         "relatedtoken1": "t1", "relationship1": "object of preposition"},
        {"id": "t3", "token": "condita", "tokentype": "lexical", "lemma": "condo",
         "relatedtoken1": "t4", "relationship1": "auxiliary"},
        {"id": "t4", "token": "est", "tokentype": "lexical", "lemma": "sum",
         "verbalunitid": "t4", "relatedtoken1": "root", "relationship1": "unit verb"},
        {"id": "t5", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "Etruria erat vicina."
#   t0 Etruria  t1 erat  t2 vicina  t3 .
#
# syntax_model.md's own worked example for *linking verb* semantic_type:
# "the verb erat is a linking verb." vicina is erat's predicate adjective;
# it originally got no relation (the scheme didn't yet cover predicate
# complements when this fixture was first written) -- now that
# syntax_model.md's "predicate" relation covers exactly this case, vicina
# is updated here to use it, and erat (being independent) gets the "root"
# sentinel.
# ---------------------------------------------------------------------------
 
_LINKING_VERB_ANSWER = {
    "reasoning": (
        "erat is a linking verb (copula), with the sentinel relation1 "
        "'root', joining its subject Etruria to the predicate adjective "
        "vicina."
    ),
    "verbalunits": [
        {"id": "t1", "syntactic_type": "independent", "semantic_type": "linking verb"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Etruria", "tokentype": "lexical", "lemma": "Etruria",
         "relatedtoken1": "t1", "relationship1": "subject"},
        {"id": "t1", "token": "erat", "tokentype": "lexical", "lemma": "sum",
         "verbalunitid": "t1", "relatedtoken1": "root", "relationship1": "unit verb"},
        {"id": "t2", "token": "vicina", "tokentype": "lexical", "lemma": "vicinus",
         "relatedtoken1": "t1", "relationship1": "predicate"},
        {"id": "t3", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "gloria est consentiens laus bonorum."
#   t0 gloria  t1 est  t2 consentiens  t3 laus  t4 bonorum  t5 .
#
# syntax_model.md's own worked example for a participle used *attributively*
# rather than with predicate sense -- and therefore NOT a verbal expression:
# "in the sentence gloria est consentiens laus bonorum, the participle
# consentiens has an attributive sense with laus... this is not a verbal
# expression." The key thing this fixture checks is the negative: t2 must
# NOT appear in verbalunits. consentiens relates to laus the same way any
# attributive adjective would (per the adjectival rule -- the doc treats an
# attributive participle exactly like an ordinary adjective).
# ---------------------------------------------------------------------------
 
_PARTICIPLE_ATTRIBUTIVE_ANSWER = {
    "reasoning": (
        "est is a linking verb (root), joining subject gloria to predicate "
        "laus; consentiens is a participle used attributively (like an "
        "ordinary adjective) to modify laus, NOT a verbal expression, since "
        "it has attributive rather than predicate sense; bonorum is "
        "genitive, modifying laus."
    ),
    "verbalunits": [
        {"id": "t1", "syntactic_type": "independent", "semantic_type": "linking verb"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "gloria", "tokentype": "lexical", "lemma": "gloria",
         "relatedtoken1": "t1", "relationship1": "subject"},
        {"id": "t1", "token": "est", "tokentype": "lexical", "lemma": "sum",
         "verbalunitid": "t1", "relatedtoken1": "root", "relationship1": "unit verb"},
        {"id": "t2", "token": "consentiens", "tokentype": "lexical", "lemma": "consentio",
         "relatedtoken1": "t3", "relationship1": "adjectival"},
        {"id": "t3", "token": "laus", "tokentype": "lexical", "lemma": "laus",
         "relatedtoken1": "t1", "relationship1": "predicate"},
        {"id": "t4", "token": "bonorum", "tokentype": "lexical", "lemma": "bonus",
         "relatedtoken1": "t3", "relationship1": "genitive"},
        {"id": "t5", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "Anco regnante Lucumo Romam commigravit."
#   t0 Anco  t1 regnante  t2 Lucumo  t3 Romam  t4 commigravit  t5 .
#
# syntax_model.md's own worked example for the *ablative absolute* case of
# "verbal units with participles" (revised from an earlier draft that used
# a longer sentence and a plain "ablative" relation on Anco): "the
# participle regnante has the ID of Anco as its relation1 with the
# relationship1 value circumstantial participle. Anco in turn has the ID
# of the verb commigravit as its relation1, and has the relationship1
# value ablative absolute." Anco is "otherwise unconnected syntactically
# to the sentence" (it isn't the subject, object, or anything else of
# commigravit), which is what makes it a true ablative absolute rather
# than the "fits into the superior verbal unit" case (see the separate
# eum-advenientem fixture for that one). Romam (bare accusative of place,
# no preposition) is left unrelated -- not covered by the current relation
# set. syntax_model.md doesn't specify a syntactic_type value for a
# participial verbal expression; this codebase's convention (see
# VerbalExpression's docstring) is 'dependent'.
# ---------------------------------------------------------------------------
 
_PARTICIPLE_PREDICATE_ANSWER = {
    "reasoning": (
        "regnante is a dependent verbal expression (predicate-sense "
        "participle, intransitive: 'while Ancus was reigning'), with "
        "relatedtoken1 pointing to Anco, the noun it agrees with, via "
        "'circumstantial participle'. Anco doesn't otherwise fit into the "
        "sentence, so it's a true ablative absolute: it relates back to "
        "the main verb commigravit via 'ablative absolute' instead of a "
        "normal noun relation. Lucumo is the subject of the independent "
        "main verb commigravit (root, intransitive). Romam is left "
        "unrelated (bare accusative of place, not covered)."
    ),
    "verbalunits": [
        {"id": "t1", "syntactic_type": "dependent", "semantic_type": "intransitive"},
        {"id": "t4", "syntactic_type": "independent", "semantic_type": "intransitive"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Anco", "tokentype": "lexical", "lemma": "Ancus",
         "relatedtoken1": "t4", "relationship1": "ablative absolute"},
        {"id": "t1", "token": "regnante", "tokentype": "lexical", "lemma": "regno",
         "verbalunitid": "t1", "relatedtoken1": "t0", "relationship1": "circumstantial participle"},
        {"id": "t2", "token": "Lucumo", "tokentype": "lexical", "lemma": "Lucumo",
         "relatedtoken1": "t4", "relationship1": "subject"},
        {"id": "t3", "token": "Romam", "tokentype": "lexical", "lemma": "Roma"},
        {"id": "t4", "token": "commigravit", "tokentype": "lexical", "lemma": "commigro",
         "verbalunitid": "t4", "relatedtoken1": "root", "relationship1": "unit verb"},
        {"id": "t5", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "Eum advenientem laeti omnes accepere."
#   t0 Eum  t1 advenientem  t2 laeti  t3 omnes  t4 accepere  t5 .
#
# syntax_model.md's own worked example for the OTHER "verbal units with
# participles" case -- where the noun the participle agrees with DOES fit
# into the surrounding clause, so it keeps its own normal relation instead
# of "ablative absolute": "the participle advenientem has the id of eum for
# relation1 and has the relationship1 value circumstantial participle. The
# token eum in turn is the direct object of the independent verb accepere."
# ---------------------------------------------------------------------------
 
_CIRCUMSTANTIAL_PARTICIPLE_ANSWER = {
    "reasoning": (
        "advenientem is a dependent verbal expression (predicate-sense "
        "participle, intransitive: 'as he was arriving'), with "
        "relatedtoken1 pointing to eum, the noun it agrees with, via "
        "'circumstantial participle'. eum fits into the surrounding clause "
        "as accepere's direct object, so it keeps that normal relation "
        "rather than an ablative-absolute one. accepere is the independent "
        "main verb (root, transitive active), with omnes as its subject; "
        "laeti is adjectival, modifying omnes."
    ),
    "verbalunits": [
        {"id": "t1", "syntactic_type": "dependent", "semantic_type": "intransitive"},
        {"id": "t4", "syntactic_type": "independent", "semantic_type": "transitive active"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Eum", "tokentype": "lexical", "lemma": "is",
         "relatedtoken1": "t4", "relationship1": "direct object"},
        {"id": "t1", "token": "advenientem", "tokentype": "lexical", "lemma": "advenio",
         "verbalunitid": "t1", "relatedtoken1": "t0", "relationship1": "circumstantial participle"},
        {"id": "t2", "token": "laeti", "tokentype": "lexical", "lemma": "laetus",
         "relatedtoken1": "t3", "relationship1": "adjectival"},
        {"id": "t3", "token": "omnes", "tokentype": "lexical", "lemma": "omnis",
         "relatedtoken1": "t4", "relationship1": "subject"},
        {"id": "t4", "token": "accepere", "tokentype": "lexical", "lemma": "accipio",
         "verbalunitid": "t4", "relatedtoken1": "root", "relationship1": "unit verb"},
        {"id": "t5", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "Facturum enim se fuisse dixit."
#   t0 Facturum  t1 enim  t2 se  t3 fuisse  t4 dixit  t5 .
#
# syntax_model.md's own worked example for an infinitive's 'indirect
# statement' syntactic_type, and for the *auxiliary* relation extended to
# a compound future-infinitive form (participle + a form of sum, not just
# the perfect-passive case): "the verb dixit is an independent verbal
# expression, and facturum fuisse is the compound verb form for the future
# infinitive. The verbal unit will be anchored to the infinitive fuisse of
# syntactic type indirect statement... facturum will have the ID of fuisse
# as its relation1 value, with a relationship1 value of auxiliary." se
# (accusative subject of the infinitive) and enim (a postpositive particle,
# not covered) follow the general subject rule and "Incomplete status"
# respectively.
#
# fuisse ALSO now has its own relatedtoken1 -> dixit, relationship1 =
# "indirect statement" -- syntax_model.md's revision giving indirect-
# statement infinitives their own governing-verb relation, matching its
# own syntactic_type value the same way "direct quote" and "aside" verbal
# expressions already do for their own governing/framing verb. An AcI
# infinitive has no separate conjunction/pronoun token to point at first
# (unlike a dependent finite verb's "unit verb" relation), so it points
# directly at the verb of saying/thinking that governs it. This is what
# makes verbal_units.compute_subordination_depths() able to resolve
# fuisse's depth (1, one level below dixit's 0) -- previously there was no
# relation here at all to chase.
# ---------------------------------------------------------------------------

_INDIRECT_STATEMENT_ANSWER = {
    "reasoning": (
        "dixit is the independent main verb (root, transitive active). "
        "fuisse anchors the compound future-infinitive verbal expression "
        "('facturum...fuisse', indirect statement, transitive active), "
        "with facturum relating to it as auxiliary, se as its accusative "
        "subject, and its own relatedtoken1 -> dixit (relationship1 "
        "'indirect statement', matching its own syntactic type) as the "
        "verb that governs the indirect statement. enim is left unrelated "
        "(a postpositive particle, not covered)."
    ),
    "verbalunits": [
        {"id": "t3", "syntactic_type": "indirect statement", "semantic_type": "transitive active"},
        {"id": "t4", "syntactic_type": "independent", "semantic_type": "transitive active"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Facturum", "tokentype": "lexical", "lemma": "facio",
         "relatedtoken1": "t3", "relationship1": "auxiliary"},
        {"id": "t1", "token": "enim", "tokentype": "lexical", "lemma": "enim"},
        {"id": "t2", "token": "se", "tokentype": "lexical", "lemma": "se",
         "relatedtoken1": "t3", "relationship1": "subject"},
        {"id": "t3", "token": "fuisse", "tokentype": "lexical", "lemma": "sum",
         "verbalunitid": "t3", "relatedtoken1": "t4", "relationship1": "indirect statement"},
        {"id": "t4", "token": "dixit", "tokentype": "lexical", "lemma": "dico",
         "verbalunitid": "t4", "relatedtoken1": "root", "relationship1": "unit verb"},
        {"id": "t5", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "Tuum est, inquit, Servi regnum."
#   t0 Tuum  t1 est  t2 ,  t3 inquit  t4 ,  t5 Servi  t6 regnum  t7 .
#
# syntax_model.md's own worked example for the 'direct quote' syntactic
# type and relation: "the token inquit is a verbal unit classified
# syntactically as an independent clause, while the verb est occurs in
# directly quoted speech and is classified as direct quote." Reconstructed
# with plain commas rather than the source's nested quotation marks, since
# "Tokenization" only documents "." as a punctuation example and doesn't
# say whether quotation marks get their own token type.
# ---------------------------------------------------------------------------
 
_DIRECT_QUOTE_ANSWER = {
    "reasoning": (
        "est anchors a 'direct quote' verbal expression (linking verb), "
        "relating back to inquit (the framing verb) via 'direct quote'; "
        "Tuum is its predicate, regnum its subject (with Servi genitive, "
        "modifying regnum). inquit is the independent main verb (root, "
        "intransitive -- a verb of saying introducing direct speech, not "
        "taking a normal syntactic direct object)."
    ),
    "verbalunits": [
        {"id": "t1", "syntactic_type": "direct quote", "semantic_type": "linking verb"},
        {"id": "t3", "syntactic_type": "independent", "semantic_type": "intransitive"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Tuum", "tokentype": "lexical", "lemma": "tuus",
         "relatedtoken1": "t1", "relationship1": "predicate"},
        {"id": "t1", "token": "est", "tokentype": "lexical", "lemma": "sum",
         "verbalunitid": "t1", "relatedtoken1": "t3", "relationship1": "direct quote"},
        {"id": "t2", "token": ",", "tokentype": "punctuation"},
        {"id": "t3", "token": "inquit", "tokentype": "lexical", "lemma": "inquam",
         "verbalunitid": "t3", "relatedtoken1": "root", "relationship1": "unit verb"},
        {"id": "t4", "token": ",", "tokentype": "punctuation"},
        {"id": "t5", "token": "Servi", "tokentype": "lexical", "lemma": "Servius",
         "relatedtoken1": "t6", "relationship1": "genitive"},
        {"id": "t6", "token": "regnum", "tokentype": "lexical", "lemma": "regnum",
         "relatedtoken1": "t1", "relationship1": "subject"},
        {"id": "t7", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "Equidem, pace dixerim deum, eos nos iam populi Romani beneficio esse spero."
#   t0 Equidem  t1 ,  t2 pace  t3 dixerim  t4 deum  t5 ,  t6 eos  t7 nos
#   t8 iam  t9 populi  t10 Romani  t11 beneficio  t12 esse  t13 spero  t14 .
#
# syntax_model.md's own worked example for the 'aside' syntactic type and
# relation: "the verb spero is classified as independent, the infinitive
# esse is part of an indirect statement, and the entire phrase pace
# dixerim deum is an aside, anchored by the finite verbal expression
# dixerim of type aside." Reconstructed with commas rather than the
# source's em-dashes, for the same reason as the direct-quote fixture
# above. nos (an emphatic pronoun alongside eos, of uncertain construction)
# is left unrelated, per "Incomplete status".
#
# esse ALSO now has its own relatedtoken1 -> spero, relationship1 =
# "indirect statement" (the same governing-verb convention added to
# indirect_statement_facturum_fuisse_dixit above) -- worth having here
# specifically because this sentence has THREE verbal expressions
# (spero/dixerim/esse), so which one esse's governor is isn't obvious by
# elimination the way it would be with only two: esse belongs to spero's
# "I hope that..." construction, not to dixerim's parenthetical aside.
# ---------------------------------------------------------------------------

_ASIDE_ANSWER = {
    "reasoning": (
        "spero is the independent main verb (root, transitive active), "
        "modified by the adverbial equidem. dixerim anchors an 'aside' "
        "verbal expression (transitive active), relating back to spero via "
        "'aside'; pace ('by leave', ablative) relates to dixerim as "
        "ablative, with deum genitive, depending on pace. esse anchors an "
        "'indirect statement' verbal expression (linking verb), with eos as "
        "its accusative subject, iam adverbial and populi Romani beneficio "
        "('by the kindness of the Roman people') ablative, all modifying "
        "esse; populi is genitive, depending on beneficio, with Romani "
        "adjectival, modifying populi. nos is left unrelated. esse's own "
        "relatedtoken1 -> spero (relationship1 'indirect statement', "
        "matching its own syntactic type) identifies spero, not dixerim, "
        "as the verb governing the indirect statement -- 'I hope that...', "
        "not part of the aside."
    ),
    "verbalunits": [
        {"id": "t3", "syntactic_type": "aside", "semantic_type": "transitive active"},
        {"id": "t12", "syntactic_type": "indirect statement", "semantic_type": "linking verb"},
        {"id": "t13", "syntactic_type": "independent", "semantic_type": "transitive active"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Equidem", "tokentype": "lexical", "lemma": "equidem",
         "relatedtoken1": "t13", "relationship1": "adverbial"},
        {"id": "t1", "token": ",", "tokentype": "punctuation"},
        {"id": "t2", "token": "pace", "tokentype": "lexical", "lemma": "pax",
         "relatedtoken1": "t3", "relationship1": "ablative"},
        {"id": "t3", "token": "dixerim", "tokentype": "lexical", "lemma": "dico",
         "verbalunitid": "t3", "relatedtoken1": "t13", "relationship1": "aside"},
        {"id": "t4", "token": "deum", "tokentype": "lexical", "lemma": "deus",
         "relatedtoken1": "t2", "relationship1": "genitive"},
        {"id": "t5", "token": ",", "tokentype": "punctuation"},
        {"id": "t6", "token": "eos", "tokentype": "lexical", "lemma": "is",
         "relatedtoken1": "t12", "relationship1": "subject"},
        {"id": "t7", "token": "nos", "tokentype": "lexical", "lemma": "ego"},
        {"id": "t8", "token": "iam", "tokentype": "lexical", "lemma": "iam",
         "relatedtoken1": "t12", "relationship1": "adverbial"},
        {"id": "t9", "token": "populi", "tokentype": "lexical", "lemma": "populus",
         "relatedtoken1": "t11", "relationship1": "genitive"},
        {"id": "t10", "token": "Romani", "tokentype": "lexical", "lemma": "Romanus",
         "relatedtoken1": "t9", "relationship1": "adjectival"},
        {"id": "t11", "token": "beneficio", "tokentype": "lexical", "lemma": "beneficium",
         "relatedtoken1": "t12", "relationship1": "ablative"},
        {"id": "t12", "token": "esse", "tokentype": "lexical", "lemma": "sum",
         "verbalunitid": "t12", "relatedtoken1": "t13", "relationship1": "indirect statement"},
        {"id": "t13", "token": "spero", "tokentype": "lexical", "lemma": "spero",
         "verbalunitid": "t13", "relatedtoken1": "root", "relationship1": "unit verb"},
        {"id": "t14", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "Lucumo Demarati Corinthii filius erat."
#   t0 Lucumo  t1 Demarati  t2 Corinthii  t3 filius  t4 erat  t5 .
#
# syntax_model.md's own worked example for the *predicate* relation:
# "Lucumo is the subject of the linking verb erat, and filius is the
# predicate." Also covers *genitive* (Demarati depends on filius) and
# *adjectival* (Corinthii, "the Corinthian", agreeing with Demarati) in the
# same sentence -- close enough to syntax_model.md's separate, structurally
# identical genitive example ("hic filius erat regis") that a dedicated
# fixture for that one would be redundant; this sentence already exercises
# the same relation the same way, plus two more.
# ---------------------------------------------------------------------------
 
_PREDICATE_ANSWER = {
    "reasoning": (
        "erat is a linking verb (root), with Lucumo as its subject and "
        "filius as its predicate ('Lucumo was a/the son'); Demarati is "
        "genitive, depending on filius ('son of Demaratus'); Corinthii is "
        "adjectival, modifying Demarati ('of Demaratus the Corinthian')."
    ),
    "verbalunits": [
        {"id": "t4", "syntactic_type": "independent", "semantic_type": "linking verb"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Lucumo", "tokentype": "lexical", "lemma": "Lucumo",
         "relatedtoken1": "t4", "relationship1": "subject"},
        {"id": "t1", "token": "Demarati", "tokentype": "lexical", "lemma": "Demaratus",
         "relatedtoken1": "t3", "relationship1": "genitive"},
        {"id": "t2", "token": "Corinthii", "tokentype": "lexical", "lemma": "Corinthius",
         "relatedtoken1": "t1", "relationship1": "adjectival"},
        {"id": "t3", "token": "filius", "tokentype": "lexical", "lemma": "filius",
         "relatedtoken1": "t4", "relationship1": "predicate"},
        {"id": "t4", "token": "erat", "tokentype": "lexical", "lemma": "sum",
         "verbalunitid": "t4", "relatedtoken1": "root", "relationship1": "unit verb"},
        {"id": "t5", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "Latini, cum quibus ictum foedus erat, sustulerant animos."
#   t0 Latini  t1 ,  t2 cum  t3 quibus  t4 ictum  t5 foedus  t6 erat  t7 ,
#   t8 sustulerant  t9 animos  t10 .
#
# syntax_model.md's own worked table example for *relative pronoun* --
# closing a gap flagged since the very first gold examples were written --
# and for the relatedtoken2/relationship2 *overflow* pattern (quibus is
# simultaneously the relative pronoun linking back to Latini, AND cum's
# object of preposition). The doc's table doesn't show cum's own outward
# relation (leaves it blank) or foedus's subject relation at all -- it's
# explicitly a "partial extract" -- but both follow directly from the
# general prepositional-phrase and subject rules already used elsewhere in
# this file, so this fixture fills them in rather than reproducing the
# table's gaps.
# ---------------------------------------------------------------------------
 
_RELATIVE_PRONOUN_ANSWER = {
    "reasoning": (
        "quibus is the relative pronoun linking back to its antecedent "
        "Latini (relatedtoken1/relationship1), and simultaneously cum's "
        "object of preposition (relatedtoken2/relationship2, since "
        "relatedtoken1 is already used); cum itself is adverbial, "
        "modifying erat. ictum foedus erat is a dependent compound perfect "
        "passive verbal expression (transitive passive) anchored at erat, "
        "linked to quibus as its unit verb; foedus is its subject, ictum "
        "its auxiliary. sustulerant is the independent main verb "
        "(root, transitive active), with Latini as its subject and animos "
        "as its direct object."
    ),
    "verbalunits": [
        {"id": "t6", "syntactic_type": "dependent", "semantic_type": "transitive passive"},
        {"id": "t8", "syntactic_type": "independent", "semantic_type": "transitive active"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Latini", "tokentype": "lexical", "lemma": "Latini",
         "relatedtoken1": "t8", "relationship1": "subject"},
        {"id": "t1", "token": ",", "tokentype": "punctuation"},
        {"id": "t2", "token": "cum", "tokentype": "lexical", "lemma": "cum",
         "relatedtoken1": "t6", "relationship1": "adverbial"},
        {"id": "t3", "token": "quibus", "tokentype": "lexical", "lemma": "qui",
         "relatedtoken1": "t0", "relationship1": "relative pronoun",
         "relatedtoken2": "t2", "relationship2": "object of preposition"},
        {"id": "t4", "token": "ictum", "tokentype": "lexical", "lemma": "icio",
         "relatedtoken1": "t6", "relationship1": "auxiliary"},
        {"id": "t5", "token": "foedus", "tokentype": "lexical", "lemma": "foedus",
         "relatedtoken1": "t6", "relationship1": "subject"},
        {"id": "t6", "token": "erat", "tokentype": "lexical", "lemma": "sum",
         "verbalunitid": "t6", "relatedtoken1": "t3", "relationship1": "unit verb"},
        {"id": "t7", "token": ",", "tokentype": "punctuation"},
        {"id": "t8", "token": "sustulerant", "tokentype": "lexical", "lemma": "tollo",
         "verbalunitid": "t8", "relatedtoken1": "root", "relationship1": "unit verb"},
        {"id": "t9", "token": "animos", "tokentype": "lexical", "lemma": "animus",
         "relatedtoken1": "t8", "relationship1": "direct object"},
        {"id": "t10", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "Lucumo superfuit patri bonorum omnium heres."
#   t0 Lucumo  t1 superfuit  t2 patri  t3 bonorum  t4 omnium  t5 heres  t6 .
#
# syntax_model.md's own worked example for *adjectival* ("the adjective
# omnium will have the id of bonorum as its relation1... bonorum will be
# treated as a noun (see below)") and, via that "(see below)" pointer into
# the noun-relations section, for *genitive* (bonorum depends on heres,
# same general rule as the dedicated "hic filius erat regis" example) and
# *dative* (patri depends on the verb superfuit). heres itself (apposition
# to Lucumo) is left unrelated -- not covered.
# ---------------------------------------------------------------------------
 
_DATIVE_GENITIVE_ANSWER = {
    "reasoning": (
        "superfuit is the independent main verb (root, intransitive: "
        "'outlived', governing a dative rather than an accusative object); "
        "Lucumo is its subject, patri its dative complement. heres ('heir') "
        "is left unrelated (apposition to Lucumo, not covered); bonorum is "
        "genitive, depending on heres ('heir of the goods'); omnium is "
        "adjectival, modifying bonorum ('all the goods')."
    ),
    "verbalunits": [
        {"id": "t1", "syntactic_type": "independent", "semantic_type": "intransitive"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Lucumo", "tokentype": "lexical", "lemma": "Lucumo",
         "relatedtoken1": "t1", "relationship1": "subject"},
        {"id": "t1", "token": "superfuit", "tokentype": "lexical", "lemma": "supersum",
         "verbalunitid": "t1", "relatedtoken1": "root", "relationship1": "unit verb"},
        {"id": "t2", "token": "patri", "tokentype": "lexical", "lemma": "pater",
         "relatedtoken1": "t1", "relationship1": "dative"},
        {"id": "t3", "token": "bonorum", "tokentype": "lexical", "lemma": "bonus",
         "relatedtoken1": "t5", "relationship1": "genitive"},
        {"id": "t4", "token": "omnium", "tokentype": "lexical", "lemma": "omnis",
         "relatedtoken1": "t3", "relationship1": "adjectival"},
        {"id": "t5", "token": "heres", "tokentype": "lexical", "lemma": "heres"},
        {"id": "t6", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "Ad Ianiculum forte ventum erat."
#   t0 Ad  t1 Ianiculum  t2 forte  t3 ventum  t4 erat  t5 .
#
# syntax_model.md's own worked example for a bare *adverb* modifying a verb,
# and for *auxiliary* on an impersonal passive of an intransitive verb:
# "the adverb forte will take the id of erat for relation1 with
# relationship1 value adverbial. ventum will also be related to erat but
# with relationship1 value auxiliary." "ventum erat" (impersonal passive of
# venio, 'there had been a coming') has no subject to assign -- there's no
# accusative or nominative to promote into that role -- and no semantic_type
# value cleanly fits an impersonal passive of an underlyingly intransitive
# verb; "intransitive" is used here as the closest available value, per
# venio's own argument structure, not "transitive passive" (reserved
# elsewhere in this file for compound passives of transitive verbs like
# condo).
# ---------------------------------------------------------------------------
 
_ADVERB_AUXILIARY_ANSWER = {
    "reasoning": (
        "erat is the independent verb (root) of an impersonal passive "
        "construction ('ventum erat', 'there had been a coming'), with no "
        "subject; ventum relates to it as auxiliary. Ad is adverbial, "
        "modifying erat, governing Ianiculum as its object of preposition; "
        "forte is a bare adverb, also adverbial, modifying erat."
    ),
    "verbalunits": [
        {"id": "t4", "syntactic_type": "independent", "semantic_type": "intransitive"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Ad", "tokentype": "lexical", "lemma": "ad",
         "relatedtoken1": "t4", "relationship1": "adverbial"},
        {"id": "t1", "token": "Ianiculum", "tokentype": "lexical", "lemma": "Ianiculum",
         "relatedtoken1": "t0", "relationship1": "object of preposition"},
        {"id": "t2", "token": "forte", "tokentype": "lexical", "lemma": "forte",
         "relatedtoken1": "t4", "relationship1": "adverbial"},
        {"id": "t3", "token": "ventum", "tokentype": "lexical", "lemma": "venio",
         "relatedtoken1": "t4", "relationship1": "auxiliary"},
        {"id": "t4", "token": "erat", "tokentype": "lexical", "lemma": "sum",
         "verbalunitid": "t4", "relatedtoken1": "root", "relationship1": "unit verb"},
        {"id": "t5", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "Omnia ferro flammaque miscet."
#   t0 Omnia  t1 ferro  t2 flamma  t3 que  t4 miscet  t5 .
#
# syntax_model.md's own worked example for *ablative*: "the two ablative
# tokens ferro and flamma both relate to the verb token miscet... ablative
# for relationship1." flammaque splits into flamma (lexical) + que
# (enclitic), a second enclitic example alongside arma virumque cano.
# ---------------------------------------------------------------------------
 
_ABLATIVE_ANSWER = {
    "reasoning": (
        "miscet is the independent main verb (root, transitive active), "
        "with Omnia as its direct object; ferro and flamma are both "
        "ablative, relating to miscet ('mixes everything with fire and "
        "flame')."
    ),
    "verbalunits": [
        {"id": "t4", "syntactic_type": "independent", "semantic_type": "transitive active"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Omnia", "tokentype": "lexical", "lemma": "omnis",
         "relatedtoken1": "t4", "relationship1": "direct object"},
        {"id": "t1", "token": "ferro", "tokentype": "lexical", "lemma": "ferrum",
         "relatedtoken1": "t4", "relationship1": "ablative"},
        {"id": "t2", "token": "flamma", "tokentype": "lexical", "lemma": "flamma",
         "relatedtoken1": "t4", "relationship1": "ablative"},
        {"id": "t3", "token": "que", "tokentype": "enclitic"},
        {"id": "t4", "token": "miscet", "tokentype": "lexical", "lemma": "misceo",
         "verbalunitid": "t4", "relatedtoken1": "root", "relationship1": "unit verb"},
        {"id": "t5", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "Audeat deinde talia alius, nisi in hunc insigne iam documentum
#  mortalibus dedero."
#   t0 Audeat  t1 deinde  t2 talia  t3 alius  t4 ,  t5 nisi  t6 in  t7 hunc
#   t8 insigne  t9 iam  t10 documentum  t11 mortalibus  t12 dedero  t13 .
#
# syntax_model.md's own worked example for *dative*: "the dative noun
# mortalibus relates to the verb dedero... dative for relationship1."
# Reinforces subordinating conjunction/unit verb (nisi/dedero, parallel to
# cum/perlustrasset), subject/direct object, adverbial, object of
# preposition, and adjectival, all in one richer sentence.
# ---------------------------------------------------------------------------
 
_DATIVE_ANSWER = {
    "reasoning": (
        "Audeat is the independent main verb (root, transitive active, "
        "jussive 'let him dare'), with alius as its subject and talia as "
        "its direct object; deinde is adverbial, modifying Audeat. nisi is "
        "the subordinating conjunction linking the conditional clause to "
        "Audeat. Within that clause, dedero is the dependent verb "
        "(transitive active), linked to nisi as its unit verb; documentum "
        "is its direct object, insigne adjectival (modifying documentum), "
        "iam adverbial; in is adverbial, modifying dedero, governing hunc "
        "as its object of preposition; mortalibus is dative, relating to "
        "dedero."
    ),
    "verbalunits": [
        {"id": "t0", "syntactic_type": "independent", "semantic_type": "transitive active"},
        {"id": "t12", "syntactic_type": "dependent", "semantic_type": "transitive active"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Audeat", "tokentype": "lexical", "lemma": "audeo",
         "verbalunitid": "t0", "relatedtoken1": "root", "relationship1": "unit verb"},
        {"id": "t1", "token": "deinde", "tokentype": "lexical", "lemma": "deinde",
         "relatedtoken1": "t0", "relationship1": "adverbial"},
        {"id": "t2", "token": "talia", "tokentype": "lexical", "lemma": "talis",
         "relatedtoken1": "t0", "relationship1": "direct object"},
        {"id": "t3", "token": "alius", "tokentype": "lexical", "lemma": "alius",
         "relatedtoken1": "t0", "relationship1": "subject"},
        {"id": "t4", "token": ",", "tokentype": "punctuation"},
        {"id": "t5", "token": "nisi", "tokentype": "lexical", "lemma": "nisi",
         "relatedtoken1": "t0", "relationship1": "subordinating conjunction"},
        {"id": "t6", "token": "in", "tokentype": "lexical", "lemma": "in",
         "relatedtoken1": "t12", "relationship1": "adverbial"},
        {"id": "t7", "token": "hunc", "tokentype": "lexical", "lemma": "hic",
         "relatedtoken1": "t6", "relationship1": "object of preposition"},
        {"id": "t8", "token": "insigne", "tokentype": "lexical", "lemma": "insignis",
         "relatedtoken1": "t10", "relationship1": "adjectival"},
        {"id": "t9", "token": "iam", "tokentype": "lexical", "lemma": "iam",
         "relatedtoken1": "t12", "relationship1": "adverbial"},
        {"id": "t10", "token": "documentum", "tokentype": "lexical", "lemma": "documentum",
         "relatedtoken1": "t12", "relationship1": "direct object"},
        {"id": "t11", "token": "mortalibus", "tokentype": "lexical", "lemma": "mortalis",
         "relatedtoken1": "t12", "relationship1": "dative"},
        {"id": "t12", "token": "dedero", "tokentype": "lexical", "lemma": "do",
         "verbalunitid": "t12", "relatedtoken1": "t5", "relationship1": "unit verb"},
        {"id": "t13", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "Pugna ad Cannas fuit clara."
#   t0 Pugna  t1 ad  t2 Cannas  t3 fuit  t4 clara  t5 .
#
# syntax_model.md's own worked example for *attributive* (a prepositional
# phrase modifying a NOUN rather than a verb): "in the phrase pugna ad
# Cannas... ad will have as relation1 the id of pugna, and its
# relationship1 will be attributive." Closes the last remaining gap in
# RelationLabel coverage.
# ---------------------------------------------------------------------------
 
_ATTRIBUTIVE_ANSWER = {
    "reasoning": (
        "fuit is a linking verb (root), with Pugna as its subject and "
        "clara as its predicate; ad is attributive, modifying the noun "
        "Pugna ('the battle near Cannae'), governing Cannas as its object "
        "of preposition."
    ),
    "verbalunits": [
        {"id": "t3", "syntactic_type": "independent", "semantic_type": "linking verb"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Pugna", "tokentype": "lexical", "lemma": "pugna",
         "relatedtoken1": "t3", "relationship1": "subject"},
        {"id": "t1", "token": "ad", "tokentype": "lexical", "lemma": "ad",
         "relatedtoken1": "t0", "relationship1": "attributive"},
        {"id": "t2", "token": "Cannas", "tokentype": "lexical", "lemma": "Cannas",
         "relatedtoken1": "t1", "relationship1": "object of preposition"},
        {"id": "t3", "token": "fuit", "tokentype": "lexical", "lemma": "sum",
         "relatedtoken1": "root", "relationship1": "unit verb", "verbalunitid": "t3"},
        {"id": "t4", "token": "clara", "tokentype": "lexical", "lemma": "clarus",
         "relatedtoken1": "t3", "relationship1": "predicate"},
        {"id": "t5", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Aequa ratione imperat."
#   t0 Aequa  t1 ratione  t2 imperat  t3 .
#
# syntax_model.md's revised *enclitic* section's own worked example for
# context-dependent tokenization: "in the phrase aequa ratione imperat, the
# string ratione is a single lexical token (noun in the ablative singular)."
# Pairs with enclitic_context_ratione_interrogative_docet below, which
# tokenizes the identical surface string "ratione" differently (split into
# a lexical token plus an enclitic) because there the context is different --
# together the two fixtures exercise the point of the doc's example: the
# same string cannot be tokenized correctly without considering context.
# ---------------------------------------------------------------------------

_ENCLITIC_CONTEXT_ABLATIVE_ANSWER = {
    "reasoning": (
        "imperat is the independent main verb ('he commands/rules', "
        "intransitive), with the sentinel relation1 'root'. ratione is a "
        "single lexical token here -- the ablative singular of ratio, "
        "'by/with method' -- related to imperat as an ablative of manner; "
        "aequa ('fair, even-handed') is adjectival, modifying ratione."
    ),
    "verbalunits": [
        {"id": "t2", "syntactic_type": "independent", "semantic_type": "intransitive"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Aequa", "tokentype": "lexical", "lemma": "aequus",
         "relatedtoken1": "t1", "relationship1": "adjectival"},
        {"id": "t1", "token": "ratione", "tokentype": "lexical", "lemma": "ratio",
         "relatedtoken1": "t2", "relationship1": "ablative"},
        {"id": "t2", "token": "imperat", "tokentype": "lexical", "lemma": "impero",
         "verbalunitid": "t2", "relatedtoken1": "root", "relationship1": "unit verb"},
        {"id": "t3", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Ratione docet?"
#   t0 Ratio  t1 ne  t2 docet  t3 ?
#
# syntax_model.md's revised *enclitic* section's other half of the same
# worked example: "in the phrase ratione docet?, the string ratione
# represents the enclitic token ne (question words) with the lexical token
# ratio (noun in the nominative singular)." The identical surface string
# "ratione" as enclitic_context_ablative_aequa above tokenizes differently
# here -- split into lexical "Ratio" (capitalized, since it's the sentence-
# initial token) plus the interrogative enclitic "ne" -- because the
# nominative-subject-of-a-question reading applies instead of the ablative-
# of-manner reading. "ne" gets no relation of its own, matching the
# connective enclitic "que"'s convention elsewhere in these fixtures: the
# scheme has no documented relation type for an enclitic.
# ---------------------------------------------------------------------------

_ENCLITIC_CONTEXT_INTERROGATIVE_ANSWER = {
    "reasoning": (
        "docet is the independent main verb of a yes/no question ('does "
        "[he/she] teach?', transitive active -- its direct object is left "
        "implicit), with the sentinel relation1 'root'. Ratio -- split from "
        "the interrogative enclitic -ne, which attaches to the first word "
        "of the question -- is docet's subject."
    ),
    "verbalunits": [
        {"id": "t2", "syntactic_type": "independent", "semantic_type": "transitive active"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Ratio", "tokentype": "lexical", "lemma": "ratio",
         "relatedtoken1": "t2", "relationship1": "subject"},
        {"id": "t1", "token": "ne", "tokentype": "enclitic"},
        {"id": "t2", "token": "docet", "tokentype": "lexical", "lemma": "doceo",
         "verbalunitid": "t2", "relatedtoken1": "root", "relationship1": "unit verb"},
        {"id": "t3", "token": "?", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Quisque officium suum fecit."
#   t0 Quisque  t1 officium  t2 suum  t3 fecit  t4 .
#
# syntax_model.md's revised *enclitic* section's other worked example:
# tokenization "must also recognize the small number of frequently occurring
# words that have incorporated an original historic enclitic into a single
# lexical item such as quisque (and its compounds), or plerusque... forms
# such as quisque, cuique and quemque must all be treated a single lexical
# token." Quisque here is NOT split into qui + que -- unlike the connective
# enclitic in enclitic_arma_virumque_cano, this word's -que is not tokenized
# separately at all.
# ---------------------------------------------------------------------------

_ENCLITIC_INCORPORATED_QUISQUE_ANSWER = {
    "reasoning": (
        "fecit is the independent main verb (transitive active), with the "
        "sentinel relation1 'root'. Quisque ('each person') is a single "
        "lexical token -- not split into qui + que, since it has "
        "incorporated its historic enclitic into one indeclinable-looking "
        "lexical item -- and is fecit's subject; officium is its direct "
        "object; suum ('his own') is adjectival, modifying officium."
    ),
    "verbalunits": [
        {"id": "t3", "syntactic_type": "independent", "semantic_type": "transitive active"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Quisque", "tokentype": "lexical", "lemma": "quisque",
         "relatedtoken1": "t3", "relationship1": "subject"},
        {"id": "t1", "token": "officium", "tokentype": "lexical", "lemma": "officium",
         "relatedtoken1": "t3", "relationship1": "direct object"},
        {"id": "t2", "token": "suum", "tokentype": "lexical", "lemma": "suus",
         "relatedtoken1": "t1", "relationship1": "adjectival"},
        {"id": "t3", "token": "fecit", "tokentype": "lexical", "lemma": "facio",
         "verbalunitid": "t3", "relatedtoken1": "root", "relationship1": "unit verb"},
        {"id": "t4", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Ille noluit, Hermionenque ab Oreste adduxit."
#   t0 ille  t1 fidem  t2 suam  t3 infirmare  t4 noluit  t5 ,
#   t6 Hermionen  t7 que  t8 ab  t9 Oreste  t10 adduxit  t11 .
#
# syntax_model.md's own worked example for *coordinating conjunction*
# joining two VERBAL EXPRESSIONS, and specifically its word-order caveat:
# "in ille fidem suam infirmare noluit, Hermionenque ab Oreste adduxit, the
# two verbal expressions with noluit and adduxit are joined by que, even
# though the enclitic que is physically attached to Hermionen, the direct
# object of adduxit." So que's relations point to noluit and adduxit (the
# two verbs), NOT to Hermionen or anything else nearby.
#
# fidem, suam, and infirmare are deliberately left without relations here:
# infirmare is a bare complementary infinitive (not part of an indirect
# statement), so per the "Table of verbal expressions" section it isn't a
# verbal expression at all, and the scheme documents no relation for a
# nominal object of a non-indirect-statement infinitive (a real gap, same
# spirit as "enim" being left bare in indirect_statement_facturum_fuisse_
# dixit) -- so fidem is left unrelated too. suam would be adjectival to
# fidem in principle, but is likewise left unrelated here since it
# modifies a token (fidem) that itself isn't otherwise connected to
# anything in this graph; nothing about the "coordinating conjunction"
# revision requires resolving that gap.
# ---------------------------------------------------------------------------

_COORDINATING_CONJUNCTION_VERBS_ANSWER = {
    "reasoning": (
        "noluit and adduxit are both independent main verbs (roots), "
        "coordinated by que -- physically attached to Hermionen (adduxit's "
        "direct object) as 'Hermionenque', but que's own relations point "
        "to the two VERBS it joins, not to Hermionen. ille is noluit's "
        "subject; noluit itself takes no nominal object (its complement, "
        "infirmare, is a bare complementary infinitive, not an indirect- "
        "statement verbal expression, so it and its own object fidem are "
        "left unrelated, a documented gap). Hermionen is adduxit's direct "
        "object; ab Oreste ('away from Orestes') is an adverbial "
        "prepositional phrase modifying adduxit."
    ),
    "verbalunits": [
        {"id": "t4", "syntactic_type": "independent", "semantic_type": "intransitive"},
        {"id": "t10", "syntactic_type": "independent", "semantic_type": "transitive active"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Ille", "tokentype": "lexical", "lemma": "ille",
         "relatedtoken1": "t4", "relationship1": "subject"},
        {"id": "t1", "token": "fidem", "tokentype": "lexical", "lemma": "fides"},
        {"id": "t2", "token": "suam", "tokentype": "lexical", "lemma": "suus"},
        {"id": "t3", "token": "infirmare", "tokentype": "lexical", "lemma": "infirmo"},
        {"id": "t4", "token": "noluit", "tokentype": "lexical", "lemma": "nolo",
         "verbalunitid": "t4", "relatedtoken1": "root", "relationship1": "unit verb"},
        {"id": "t5", "token": ",", "tokentype": "punctuation"},
        {"id": "t6", "token": "Hermionen", "tokentype": "lexical", "lemma": "Hermione",
         "relatedtoken1": "t10", "relationship1": "direct object"},
        {"id": "t7", "token": "que", "tokentype": "enclitic",
         "relatedtoken1": "t4", "relationship1": "coordinating conjunction",
         "relatedtoken2": "t10", "relationship2": "coordinating conjunction"},
        {"id": "t8", "token": "ab", "tokentype": "lexical", "lemma": "ab",
         "relatedtoken1": "t10", "relationship1": "adverbial"},
        {"id": "t9", "token": "Oreste", "tokentype": "lexical", "lemma": "Orestes",
         "relatedtoken1": "t8", "relationship1": "object of preposition"},
        {"id": "t10", "token": "adduxit", "tokentype": "lexical", "lemma": "adduco",
         "verbalunitid": "t10", "relatedtoken1": "root", "relationship1": "unit verb"},
        {"id": "t11", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Sed re cognita, iussu Cereris Triptolemo regnum dedit."
#   t0 sed  t1 re  t2 cognita  t3 ,  t4 iussu  t5 Cereris  t6 Triptolemo
#   t7 regnum  t8 dedit  t9 .
#
# syntax_model.md's own worked example for a coordinating conjunction that
# opens a new sentence with no explicit preceding verb: "sed introduces the
# entire verbal expression with dedit, but we do not mark any implied
# relation to a preceding expression. sed will have the ID of dedit for
# relation1, with relationship1 as coordinating conjunction" -- so sed gets
# ONLY relatedtoken1/relationship1, no relatedtoken2/relationship2 at all
# (contrast the paired cases above, which always set both).
#
# Also folds in an ablative absolute ("re cognita", "the matter having
# been looked into") for good measure, reusing already-covered relations.
# ---------------------------------------------------------------------------

_COORDINATING_CONJUNCTION_SENTENCE_INITIAL_ANSWER = {
    "reasoning": (
        "dedit is the independent main verb (transitive active), root. "
        "sed is a coordinating conjunction introducing this whole "
        "sentence -- relatedtoken1 -> dedit only, since there's no "
        "explicit verb to its left to pair it with, and we don't invent an "
        "implied link to a preceding sentence. re cognita is an ablative "
        "absolute ('the matter having been looked into'): cognita relates "
        "to re as circumstantial participle, and re -- otherwise "
        "unconnected to the rest of the sentence -- relates back to dedit "
        "as ablative absolute. iussu ('by command') is ablative, "
        "modifying dedit; Cereris is genitive, depending on iussu; "
        "Triptolemo is dative, and regnum is the direct object, both of "
        "dedit."
    ),
    "verbalunits": [
        {"id": "t2", "syntactic_type": "dependent", "semantic_type": "transitive passive"},
        {"id": "t8", "syntactic_type": "independent", "semantic_type": "transitive active"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Sed", "tokentype": "lexical", "lemma": "sed",
         "relatedtoken1": "t8", "relationship1": "coordinating conjunction"},
        {"id": "t1", "token": "re", "tokentype": "lexical", "lemma": "res",
         "relatedtoken1": "t8", "relationship1": "ablative absolute"},
        {"id": "t2", "token": "cognita", "tokentype": "lexical", "lemma": "cognosco",
         "verbalunitid": "t2", "relatedtoken1": "t1", "relationship1": "circumstantial participle"},
        {"id": "t3", "token": ",", "tokentype": "punctuation"},
        {"id": "t4", "token": "iussu", "tokentype": "lexical", "lemma": "iussus",
         "relatedtoken1": "t8", "relationship1": "ablative"},
        {"id": "t5", "token": "Cereris", "tokentype": "lexical", "lemma": "Ceres",
         "relatedtoken1": "t4", "relationship1": "genitive"},
        {"id": "t6", "token": "Triptolemo", "tokentype": "lexical", "lemma": "Triptolemus",
         "relatedtoken1": "t8", "relationship1": "dative"},
        {"id": "t7", "token": "regnum", "tokentype": "lexical", "lemma": "regnum",
         "relatedtoken1": "t8", "relationship1": "direct object"},
        {"id": "t8", "token": "dedit", "tokentype": "lexical", "lemma": "do",
         "verbalunitid": "t8", "relatedtoken1": "root", "relationship1": "unit verb"},
        {"id": "t9", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Tu quoque, Brute, fili mi, et tu?"
#   t0 Tu  t1 quoque  t2 ,  t3 Brute  t4 ,  t5 fili  t6 mi  t7 ,
#   t8 et  t9 tu  t10 ?
#
# syntax_model.md's own worked example for the "et" ambiguity: "the word et
# can be used as a conjunction or adverbially ('even', 'also')! ... the
# token et is functioning as an adverb, not a conjunction and will have the
# last lexical token tu as its relation1, with the relationship1 value
# adverbial." A verbless exclamation (no finite verb at all -- verbalunits
# is empty here), so quoque, Brute, and fili all have no verb to attach to
# either and are left unrelated (direct address / apposition aren't
# documented relations -- see latin_syntax_dspy.py's "apposition ... isn't
# covered"); mi is still adjectival to fili, since that relation doesn't
# require a verb.
# ---------------------------------------------------------------------------

_COORDINATING_CONJUNCTION_ET_AS_ADVERB_ANSWER = {
    "reasoning": (
        "This exclamation has no finite verb at all (verbalunits is "
        "empty). et here is NOT a coordinating conjunction -- there's "
        "nothing for it to coordinate -- but the adverb 'even/also', "
        "relatedtoken1 -> tu (the last lexical token), relationship1 "
        "'adverbial', per syntax_model.md's own disambiguation note. Tu, "
        "quoque, Brute, and fili (direct address / apposition, not "
        "documented relations) are left unrelated; mi is adjectival, "
        "modifying fili."
    ),
    "verbalunits": [],
    "tokengraph": [
        {"id": "t0", "token": "Tu", "tokentype": "lexical", "lemma": "tu"},
        {"id": "t1", "token": "quoque", "tokentype": "lexical", "lemma": "quoque"},
        {"id": "t2", "token": ",", "tokentype": "punctuation"},
        {"id": "t3", "token": "Brute", "tokentype": "lexical", "lemma": "Brutus"},
        {"id": "t4", "token": ",", "tokentype": "punctuation"},
        {"id": "t5", "token": "fili", "tokentype": "lexical", "lemma": "filius"},
        {"id": "t6", "token": "mi", "tokentype": "lexical", "lemma": "meus",
         "relatedtoken1": "t5", "relationship1": "adjectival"},
        {"id": "t7", "token": ",", "tokentype": "punctuation"},
        {"id": "t8", "token": "et", "tokentype": "lexical", "lemma": "et",
         "relatedtoken1": "t9", "relationship1": "adverbial"},
        {"id": "t9", "token": "tu", "tokentype": "lexical", "lemma": "tu"},
        {"id": "t10", "token": "?", "tokentype": "punctuation"},
    ],
}
# ---------------------------------------------------------------------------
# "Taurum cum quo Pasiphae concubuit ex Creta insula Mycenis uiuum adduxit."
#   t0 Taurum  t1 cum  t2 quo  t3 Pasiphae  t4 concubuit  t5 ex  t6 Creta
#   t7 insula  t8 Mycenis  t9 uiuum  t10 adduxit  t11 .
#
# The user's own worked example for verbal_units.compute_subordination_
# depths() and rendering.tokengraph_to_depth_html(): two verbal expressions,
# anchored at concubuit (dependent, introduced by the relative pronoun quo)
# and adduxit (independent, root). Structurally identical to
# relative_pronoun_latini_cum_quibus above -- quo is simultaneously the
# relative pronoun linking back to its antecedent Taurum (relatedtoken1) and
# cum's object of preposition (relatedtoken2), and cum itself is adverbial,
# modifying concubuit -- reused here specifically because it's the
# depth/HTML-viz worked example, not because the relation shapes are new.
#
# insula is ex's object of preposition ("from the island..."), with Creta
# adjectival to it ("...of Crete", the same "genitive-ish noun treated as
# adjectival" convention predicate_lucumo_demarati_corinthii_filius uses for
# "Corinthii"); uiuum is adjectival to Taurum ("brought back alive"). Mycenis
# (locative-by-form "to Mycenae", a plurale-tantum place name) is left
# unrelated, the same "bare accusative/locative of place, not covered" gap
# Romam gets in participle_predicate_anco_regnante.
# ---------------------------------------------------------------------------

_DEPTH_TAURUM_CONCUBUIT_ANSWER = {
    "reasoning": (
        "adduxit is the independent main verb (root, transitive active), "
        "with Taurum as its direct object and uiuum adjectival to Taurum "
        "('brought back alive'); ex is adverbial, modifying adduxit, "
        "governing insula as its object of preposition, with Creta "
        "adjectival to insula ('the island of Crete'). Mycenis is left "
        "unrelated (locative-by-form place name, not covered). concubuit "
        "anchors a dependent verbal expression (intransitive: 'with whom "
        "Pasiphae lay'), linked to quo as its unit verb; quo is "
        "simultaneously the relative pronoun linking back to its "
        "antecedent Taurum and cum's object of preposition; cum is "
        "adverbial, modifying concubuit; Pasiphae is concubuit's subject."
    ),
    "verbalunits": [
        {"id": "t4", "syntactic_type": "dependent", "semantic_type": "intransitive"},
        {"id": "t10", "syntactic_type": "independent", "semantic_type": "transitive active"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Taurum", "tokentype": "lexical", "lemma": "taurus",
         "relatedtoken1": "t10", "relationship1": "direct object"},
        {"id": "t1", "token": "cum", "tokentype": "lexical", "lemma": "cum",
         "relatedtoken1": "t4", "relationship1": "adverbial"},
        {"id": "t2", "token": "quo", "tokentype": "lexical", "lemma": "qui",
         "relatedtoken1": "t0", "relationship1": "relative pronoun",
         "relatedtoken2": "t1", "relationship2": "object of preposition"},
        {"id": "t3", "token": "Pasiphae", "tokentype": "lexical", "lemma": "Pasiphae",
         "relatedtoken1": "t4", "relationship1": "subject"},
        {"id": "t4", "token": "concubuit", "tokentype": "lexical", "lemma": "concumbo",
         "verbalunitid": "t4", "relatedtoken1": "t2", "relationship1": "unit verb"},
        {"id": "t5", "token": "ex", "tokentype": "lexical", "lemma": "ex",
         "relatedtoken1": "t10", "relationship1": "adverbial"},
        {"id": "t6", "token": "Creta", "tokentype": "lexical", "lemma": "Creta",
         "relatedtoken1": "t7", "relationship1": "adjectival"},
        {"id": "t7", "token": "insula", "tokentype": "lexical", "lemma": "insula",
         "relatedtoken1": "t5", "relationship1": "object of preposition"},
        {"id": "t8", "token": "Mycenis", "tokentype": "lexical", "lemma": "Mycenae"},
        {"id": "t9", "token": "uiuum", "tokentype": "lexical", "lemma": "vivus",
         "relatedtoken1": "t0", "relationship1": "adjectival"},
        {"id": "t10", "token": "adduxit", "tokentype": "lexical", "lemma": "adduco",
         "verbalunitid": "t10", "relatedtoken1": "root", "relationship1": "unit verb"},
        {"id": "t11", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Cum sciret se peccavisse, doluit."
#   t0 Cum  t1 sciret  t2 se  t3 peccavisse  t4 ,  t5 doluit  t6 .
#
# A depth-TWO nesting fixture for compute_subordination_depths(): doluit is
# independent (depth 0); sciret is a dependent verb introduced by cum
# (depth 1, one level below doluit); peccavisse is an indirect-statement
# infinitive governed by sciret itself, not by doluit (depth 2, one level
# below sciret) -- exactly the "if the dependent clause introduces an
# indirect statement, that will have depth 2" case the depth feature was
# requested for, and the reason peccavisse's own relatedtoken1 has to point
# at sciret rather than at doluit.
# ---------------------------------------------------------------------------

_DEPTH_TWO_CUM_SCIRET_PECCAVISSE_ANSWER = {
    "reasoning": (
        "doluit is the independent main verb (root, intransitive). sciret "
        "anchors a dependent verbal expression (transitive active: 'since "
        "he knew...'), linked to cum as its unit verb; cum is the "
        "subordinating conjunction, relating back to doluit. peccavisse "
        "anchors an indirect-statement verbal expression (intransitive: "
        "'that he had sinned'), with se as its accusative subject, and its "
        "own relatedtoken1 -> sciret (relationship1 'indirect statement', "
        "matching its own syntactic type) identifying sciret -- not doluit "
        "-- as the verb governing this indirect statement, since it's "
        "sciret's object, nested one level deeper than sciret's own "
        "cum-clause."
    ),
    "verbalunits": [
        {"id": "t1", "syntactic_type": "dependent", "semantic_type": "transitive active"},
        {"id": "t3", "syntactic_type": "indirect statement", "semantic_type": "intransitive"},
        {"id": "t5", "syntactic_type": "independent", "semantic_type": "intransitive"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Cum", "tokentype": "lexical", "lemma": "cum",
         "relatedtoken1": "t5", "relationship1": "subordinating conjunction"},
        {"id": "t1", "token": "sciret", "tokentype": "lexical", "lemma": "scio",
         "verbalunitid": "t1", "relatedtoken1": "t0", "relationship1": "unit verb"},
        {"id": "t2", "token": "se", "tokentype": "lexical", "lemma": "se",
         "relatedtoken1": "t3", "relationship1": "subject"},
        {"id": "t3", "token": "peccavisse", "tokentype": "lexical", "lemma": "pecco",
         "verbalunitid": "t3", "relatedtoken1": "t1", "relationship1": "indirect statement"},
        {"id": "t4", "token": ",", "tokentype": "punctuation"},
        {"id": "t5", "token": "doluit", "tokentype": "lexical", "lemma": "doleo",
         "verbalunitid": "t5", "relatedtoken1": "root", "relationship1": "unit verb"},
        {"id": "t6", "token": ".", "tokentype": "punctuation"},
    ],
}

 
 
GOLD_EXAMPLES = [
    GoldExample(
        slug="unit_verb_hercules_cum",
        passage="Hercules cum gregem perlustrasset, pergit ad proximam speluncam.",
        tags=[
            "unit verb",
            "subordinating conjunction",
            "subject",
            "direct object",
            "adverbial",
            "object of preposition",
        ],
        canned_answer=_HERCULES_ANSWER,
    ),
    GoldExample(
        slug="enclitic_arma_virumque_cano",
        passage="arma virumque cano.",
        tags=["enclitic", "direct object", "coordinating conjunction (pair of nouns)"],
        canned_answer=_ENCLITIC_ANSWER,
    ),
    GoldExample(
        slug="praenomen_abbreviation_m_agrippa_cos",
        passage="M. Agrippa L. f. cos. tertium fecit.",
        tags=["praenomen", "abbreviation", "subject", "adverbial"],
        canned_answer=_PRAENOMEN_ABBREVIATION_ANSWER,
    ),
    GoldExample(
        slug="numeral_hiberna_aberant_xxv",
        passage="Hiberna aberant ab eo milia passuum XXV.",
        tags=["numeral", "subject", "adverbial", "object of preposition"],
        canned_answer=_NUMERAL_ANSWER,
    ),
    GoldExample(
        slug="syntactic_type_legit_cresceret",
        passage="principes Albanorum in patres, ut ea quoque pars rei publicae cresceret, legit.",
        tags=[
            "independent",
            "dependent",
            "transitive active",
            "intransitive",
            "unit verb",
            "subordinating conjunction",
            "subject",
            "direct object",
            "adverbial",
            "object of preposition",
        ],
        canned_answer=_SYNTACTIC_TYPE_ANSWER,
    ),
    GoldExample(
        slug="semantic_type_transitive_passive_urbs_condita",
        passage="urbs a Romulo condita est.",
        tags=["transitive passive", "agent", "subject", "object of preposition"],
        canned_answer=_TRANSITIVE_PASSIVE_ANSWER,
    ),
    GoldExample(
        slug="semantic_type_linking_verb_etruria_vicina",
        passage="Etruria erat vicina.",
        tags=["linking verb", "subject", "predicate"],
        canned_answer=_LINKING_VERB_ANSWER,
    ),
    GoldExample(
        slug="participle_attributive_gloria_est_consentiens",
        passage="gloria est consentiens laus bonorum.",
        tags=["linking verb", "predicate", "genitive", "adjectival",
              "participle (attributive, NOT a verbal expression)"],
        canned_answer=_PARTICIPLE_ATTRIBUTIVE_ANSWER,
    ),
    GoldExample(
        slug="participle_predicate_anco_regnante",
        passage="Anco regnante Lucumo Romam commigravit.",
        tags=["circumstantial participle", "ablative absolute", "subject",
              "intransitive", "dependent",
              "participle (predicate, IS a verbal expression)"],
        canned_answer=_PARTICIPLE_PREDICATE_ANSWER,
    ),
    GoldExample(
        slug="circumstantial_participle_eum_advenientem",
        passage="Eum advenientem laeti omnes accepere.",
        tags=["circumstantial participle", "direct object", "adjectival",
              "subject", "unit verb", "intransitive", "transitive active",
              "dependent",
              "participle (predicate, agreeing noun keeps its own relation)"],
        canned_answer=_CIRCUMSTANTIAL_PARTICIPLE_ANSWER,
    ),
    GoldExample(
        slug="indirect_statement_facturum_fuisse_dixit",
        passage="Facturum enim se fuisse dixit.",
        tags=["indirect statement", "auxiliary", "subject", "unit verb",
              "transitive active"],
        canned_answer=_INDIRECT_STATEMENT_ANSWER,
    ),
    GoldExample(
        slug="direct_quote_tuum_est_inquit",
        passage="Tuum est, inquit, Servi regnum.",
        tags=["direct quote", "predicate", "genitive", "subject", "unit verb",
              "linking verb", "intransitive"],
        canned_answer=_DIRECT_QUOTE_ANSWER,
    ),
    GoldExample(
        slug="aside_equidem_pace_dixerim",
        passage="Equidem, pace dixerim deum, eos nos iam populi Romani beneficio esse spero.",
        tags=["aside", "ablative", "genitive", "adjectival", "adverbial",
              "subject", "indirect statement", "unit verb",
              "transitive active", "linking verb"],
        canned_answer=_ASIDE_ANSWER,
    ),
    GoldExample(
        slug="predicate_lucumo_demarati_corinthii_filius",
        passage="Lucumo Demarati Corinthii filius erat.",
        tags=["predicate", "genitive", "adjectival", "subject", "linking verb"],
        canned_answer=_PREDICATE_ANSWER,
    ),
    GoldExample(
        slug="relative_pronoun_latini_cum_quibus",
        passage="Latini, cum quibus ictum foedus erat, sustulerant animos.",
        tags=["relative pronoun", "object of preposition", "auxiliary", "subject",
              "direct object", "unit verb", "adverbial", "transitive passive",
              "relatedtoken2/relationship2 overflow"],
        canned_answer=_RELATIVE_PRONOUN_ANSWER,
    ),
    GoldExample(
        slug="dative_genitive_lucumo_superfuit",
        passage="Lucumo superfuit patri bonorum omnium heres.",
        tags=["dative", "genitive", "adjectival", "subject", "intransitive"],
        canned_answer=_DATIVE_GENITIVE_ANSWER,
    ),
    GoldExample(
        slug="adverb_auxiliary_ad_ianiculum_ventum",
        passage="Ad Ianiculum forte ventum erat.",
        tags=["adverbial", "auxiliary", "object of preposition", "intransitive"],
        canned_answer=_ADVERB_AUXILIARY_ANSWER,
    ),
    GoldExample(
        slug="ablative_omnia_ferro_flammaque_miscet",
        passage="Omnia ferro flammaque miscet.",
        tags=["ablative", "direct object", "enclitic"],
        canned_answer=_ABLATIVE_ANSWER,
    ),
    GoldExample(
        slug="dative_audeat_nisi_dedero_mortalibus",
        passage="Audeat deinde talia alius, nisi in hunc insigne iam documentum mortalibus dedero.",
        tags=["dative", "subordinating conjunction", "unit verb", "subject",
              "direct object", "adverbial", "object of preposition", "adjectival"],
        canned_answer=_DATIVE_ANSWER,
    ),
    GoldExample(
        slug="attributive_pugna_ad_cannas",
        passage="Pugna ad Cannas fuit clara.",
        tags=["attributive", "object of preposition", "predicate", "linking verb", "subject"],
        canned_answer=_ATTRIBUTIVE_ANSWER,
    ),
    GoldExample(
        slug="enclitic_context_ablative_aequa_ratione",
        passage="Aequa ratione imperat.",
        tags=["enclitic (context-dependent tokenization, non-split case)",
              "ablative", "adjectival", "intransitive"],
        canned_answer=_ENCLITIC_CONTEXT_ABLATIVE_ANSWER,
    ),
    GoldExample(
        slug="enclitic_context_interrogative_ratione_docet",
        passage="Ratione docet?",
        tags=["enclitic (context-dependent tokenization, split case)",
              "subject", "transitive active"],
        canned_answer=_ENCLITIC_CONTEXT_INTERROGATIVE_ANSWER,
    ),
    GoldExample(
        slug="enclitic_incorporated_quisque_officium",
        passage="Quisque officium suum fecit.",
        tags=["enclitic (historically incorporated, never split)",
              "subject", "direct object", "adjectival", "transitive active"],
        canned_answer=_ENCLITIC_INCORPORATED_QUISQUE_ANSWER,
    ),
    GoldExample(
        slug="coordinating_conjunction_verbs_ille_hermionenque",
        passage="Ille fidem suam infirmare noluit, Hermionenque ab Oreste adduxit.",
        tags=["coordinating conjunction (pair of verbal expressions, "
              "word-order mismatch)", "subject", "direct object",
              "adverbial", "object of preposition", "intransitive",
              "transitive active"],
        canned_answer=_COORDINATING_CONJUNCTION_VERBS_ANSWER,
    ),
    GoldExample(
        slug="coordinating_conjunction_sentence_initial_sed_dedit",
        passage="Sed re cognita, iussu Cereris Triptolemo regnum dedit.",
        tags=["coordinating conjunction (sentence-initial, one-sided)",
              "circumstantial participle", "ablative absolute", "ablative",
              "genitive", "dative", "direct object", "dependent",
              "transitive passive", "transitive active"],
        canned_answer=_COORDINATING_CONJUNCTION_SENTENCE_INITIAL_ANSWER,
    ),
    GoldExample(
        slug="coordinating_conjunction_et_as_adverb_tu_brute",
        passage="Tu quoque, Brute, fili mi, et tu?",
        tags=["coordinating conjunction (disambiguation: et as adverb, "
              "not conjunction)", "adjectival"],
        canned_answer=_COORDINATING_CONJUNCTION_ET_AS_ADVERB_ANSWER,
    ),
    GoldExample(
        slug="depth_taurum_cum_quo_concubuit",
        passage="Taurum cum quo Pasiphae concubuit ex Creta insula Mycenis uiuum adduxit.",
        tags=["unit verb", "relative pronoun", "object of preposition",
              "adverbial", "subject", "direct object", "adjectival",
              "dependent", "depth of subordination (1 level)"],
        canned_answer=_DEPTH_TAURUM_CONCUBUIT_ANSWER,
    ),
    GoldExample(
        slug="depth_two_cum_sciret_peccavisse_doluit",
        passage="Cum sciret se peccavisse, doluit.",
        tags=["subordinating conjunction", "unit verb", "subject",
              "indirect statement", "dependent",
              "depth of subordination (2 levels)"],
        canned_answer=_DEPTH_TWO_CUM_SCIRET_PECCAVISSE_ANSWER,
    ),
    # RelationLabel coverage is complete -- every documented relation has at
    # least one tagged example, including the relatedtoken2/relationship2
    # overflow pattern, "coordinating conjunction" (which uses relation1 AND
    # relation2 for two ends of the same relation, not as an overflow slot --
    # see enclitic_arma_virumque_cano for the paired-nouns case, the two new
    # coordinating_conjunction_* fixtures above for the paired-verbs,
    # sentence-initial, and et-as-adverb cases), and the newest additions
    # (circumstantial participle, ablative absolute, direct quote, aside).
    # VerbalExpression.syntactic_type coverage is also complete: independent,
    # dependent, direct quote, aside, and indirect statement all have a
    # tagged example. TokenAnalysis.tokentype coverage is also complete,
    # including "abbreviation" (see praenomen_abbreviation_m_agrippa_cos) and
    # the enclitic-tokenization nuances syntax_model.md's tokenization
    # section documents: a context-dependent split ("ratione") and a word
    # that has incorporated its historic enclitic and must never be split
    # ("quisque" and its compounds). Still open (see test_coverage.py for the
    # authoritative list): gerunds and gerundives (syntax_model.md's own
    # "TBA" section) have no gold example yet, since the scheme doesn't
    # document how to analyze them.
]
 