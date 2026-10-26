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
# A dependent clause introduced by a subordinating word: perlustrasset ->
# cum ('unit verb'), cum -> pergit ('subordinating word'). proximam is
# 'adjectival' to speluncam (every non-punctuation token now has a
# relation).
# ---------------------------------------------------------------------------
 
_HERCULES_ANSWER = {
    "reasoning": (
        "pergit is the independent main verb ('unit verb' -> root); Hercules "
        "is its subject. perlustrasset is the verb of the dependent "
        "cum-clause and relates to cum as 'unit verb'; cum relates to pergit "
        "as 'subordinating word'. gregem is the direct object of "
        "perlustrasset. ad heads an adverbial phrase modifying pergit, with "
        "speluncam as its object; proximam is adjectival to speluncam."
    ),
    "verbalunits": [
        {"id": "t3", "syntactic_type": "dependent"},
        {"id": "t5", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Hercules", "tokentype": "lexical", "lemma": "Hercules",
         "relations": [{"related": "t5", "relationship": "subject"}]},
        {"id": "t1", "token": "cum", "tokentype": "lexical", "lemma": "cum",
         "relations": [{"related": "t5", "relationship": "subordinating word"}]},
        {"id": "t2", "token": "gregem", "tokentype": "lexical", "lemma": "grex",
         "relations": [{"related": "t3", "relationship": "direct object"}]},
        {"id": "t3", "token": "perlustrasset", "tokentype": "lexical", "lemma": "perlustro", "verbalunitid": "t3",
         "relations": [{"related": "t1", "relationship": "unit verb"}]},
        {"id": "t4", "token": ",", "tokentype": "punctuation"},
        {"id": "t5", "token": "pergit", "tokentype": "lexical", "lemma": "pergo", "verbalunitid": "t5",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t6", "token": "ad", "tokentype": "lexical", "lemma": "ad",
         "relations": [{"related": "t5", "relationship": "adverbial"}]},
        {"id": "t7", "token": "proximam", "tokentype": "lexical", "lemma": "proximus",
         "relations": [{"related": "t8", "relationship": "adjectival"}]},
        {"id": "t8", "token": "speluncam", "tokentype": "lexical", "lemma": "spelunca",
         "relations": [{"related": "t6", "relationship": "object of preposition"}]},
        {"id": "t9", "token": ".", "tokentype": "punctuation"},
    ],
}
 
# ---------------------------------------------------------------------------
# "arma virumque cano."
#   t0 arma  t1 virum  t2 que  t3 cano  t4 .
#
# the scheme docs' own worked example for the *enclitic* token type: "the
# enclitic que in the phrase arma virumque cano." virumque splits into
# virum (lexical) + que (enclitic). cano is also the scheme docs' own
# worked example for the "root" convention: "cano is an independent verb
# with relation1 value root, and relationship1 value unit verb."
#
# que is ALSO the scheme docs' own worked example for *coordinating
# conjunction* joining a pair of nouns: "in arma virumque cano, the
# conjunction que will have the ids of arma and virum for relation1 and
# relation2, and coordinating conjunction for both relationship1 and
# relationship2." (Previously que was left with no relation at all --
# "the scheme has no documented relation type for a connective enclitic" --
# that was true before this revision added "coordinating word".)
# ---------------------------------------------------------------------------

_ENCLITIC_ANSWER = {
    "reasoning": (
        "cano is the independent main verb (transitive active, 'I sing'), "
        "with the sentinel relation1 'root'; arma and virum -- joined by "
        "the enclitic -que ('and') -- are both its direct objects, and que "
        "itself is a coordinating conjunction relating the pair of them to "
        "each other (-> arma, -> virum)."
    ),
    "verbalunits": [
        {"id": "t3", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "arma", "tokentype": "lexical", "lemma": "arma",
         "relations": [{"related": "t3", "relationship": "direct object"}]},
        {"id": "t1", "token": "virum", "tokentype": "lexical", "lemma": "vir",
         "relations": [{"related": "t3", "relationship": "direct object"}]},
        {"id": "t2", "token": "que", "tokentype": "enclitic",
         "relations": [{"related": "t0", "relationship": "coordinating word"}, {"related": "t1", "relationship": "coordinating word"}]},
        {"id": "t3", "token": "cano", "tokentype": "lexical", "lemma": "cano", "verbalunitid": "t3",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t4", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "M. Agrippa L. f. cos. tertium fecit."
#   t0 M.  t1 Agrippa  t2 L.  t3 f.  t4 cos.  t5 tertium  t6 fecit  t7 .
#
# The worked example for a praenomen used with and without a nomen
# (quarto/concepts/syntactic-analysis.qmd, 'Praenomen'): M. -> Agrippa
# ('praenomen'). L. stands alone (the father's name in the filiation
# formula L(ucii) f(ilius)), so it is treated like any substantive:
# 'genitive' -> f. The abbreviations f. and cos. are nominatives in
# apposition to Agrippa, and tertium is 'adverbial' to cos. (consul for the
# third time).
# ---------------------------------------------------------------------------

_PRAENOMEN_ABBREVIATION_ANSWER = {
    "reasoning": (
        "fecit is the independent main verb, with Agrippa as its subject (its "
        "object, the building, is left implicit as usual in a dedicatory "
        "inscription). M. is the praenomen of Agrippa. L. has no nomen of its "
        "own -- it is the father's name, L(ucii), a genitive depending on "
        "f(ilius). f. and cos. (co(n)s(ul)) are both in apposition to "
        "Agrippa, and tertium ('for the third time') is adverbial to cos."
    ),
    "verbalunits": [
        {"id": "t6", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "M.", "tokentype": "praenomen",
         "relations": [{"related": "t1", "relationship": "praenomen"}]},
        {"id": "t1", "token": "Agrippa", "tokentype": "lexical", "lemma": "Agrippa",
         "relations": [{"related": "t6", "relationship": "subject"}]},
        {"id": "t2", "token": "L.", "tokentype": "praenomen",
         "relations": [{"related": "t3", "relationship": "genitive"}]},
        {"id": "t3", "token": "f.", "tokentype": "abbreviation",
         "relations": [{"related": "t1", "relationship": "apposition"}]},
        {"id": "t4", "token": "cos.", "tokentype": "abbreviation",
         "relations": [{"related": "t1", "relationship": "apposition"}]},
        {"id": "t5", "token": "tertium", "tokentype": "lexical", "lemma": "tertium",
         "relations": [{"related": "t4", "relationship": "adverbial"}]},
        {"id": "t6", "token": "fecit", "tokentype": "lexical", "lemma": "facio", "verbalunitid": "t6",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t7", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "Hiberna aberant ab eo milia passuum XXV."
#   t0 Hiberna  t1 aberant  t2 ab  t3 eo  t4 milia  t5 passuum  t6 XXV  t7 .
#
# The worked example for the 'numeral' token type: XXV is written with
# numerals. milia is an accusative (of extent) with aberant, passuum a
# genitive with milia, and XXV 'adjectival' to milia.
# ---------------------------------------------------------------------------

_NUMERAL_ANSWER = {
    "reasoning": (
        "aberant is the independent main verb, with hiberna as its subject. "
        "ab heads an adverbial phrase with eo as its object. milia is an "
        "accusative of extent with aberant; passuum is a genitive depending "
        "on milia, and the numeral XXV (viginti quinque) is adjectival to "
        "milia."
    ),
    "verbalunits": [
        {"id": "t1", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Hiberna", "tokentype": "lexical", "lemma": "hiberna",
         "relations": [{"related": "t1", "relationship": "subject"}]},
        {"id": "t1", "token": "aberant", "tokentype": "lexical", "lemma": "absum", "verbalunitid": "t1",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t2", "token": "ab", "tokentype": "lexical", "lemma": "ab",
         "relations": [{"related": "t1", "relationship": "adverbial"}]},
        {"id": "t3", "token": "eo", "tokentype": "lexical", "lemma": "is",
         "relations": [{"related": "t2", "relationship": "object of preposition"}]},
        {"id": "t4", "token": "milia", "tokentype": "lexical", "lemma": "mille",
         "relations": [{"related": "t1", "relationship": "accusative"}]},
        {"id": "t5", "token": "passuum", "tokentype": "lexical", "lemma": "passus",
         "relations": [{"related": "t4", "relationship": "genitive"}]},
        {"id": "t6", "token": "XXV", "tokentype": "numeral",
         "relations": [{"related": "t4", "relationship": "adjectival"}]},
        {"id": "t7", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# the scheme docs' tokenization section clarifies that 'numeral' is only
# for a number written NUMERICALLY (Roman or Arabic) -- a number spelled
# out as an ordinary word (e.g. "decem", 'ten') is 'lexical' instead, even
# though it's semantically a number. the scheme docs' own worked example
# is "fratres Joseph decem" (all three tokens lexical) -- itself drawn
# from the real Vulgate Genesis 42:3 ("Descendentes igitur fratres Joseph
# decem, ut emerent frumenta in Aegypto..."). This fixture reuses that
# same phrase with a simple verb of its own ("venerunt") rather than the
# original's more complex purpose clause, to keep this fixture minimal and
# focused on the numeral-vs-lexical distinction alone.
# ---------------------------------------------------------------------------

_LEXICAL_NUMERAL_FRATRES_JOSEPH_DECEM_ANSWER = {
    "reasoning": (
        "venerunt is the independent main verb (intransitive, 'they "
        "came'), with the sentinel relatedtoken1 'root'; Fratres is its "
        "subject. Joseph, an indeclinable Hebrew name here in genitive "
        "function ('brothers OF Joseph'), depends on Fratres via "
        "'genitive'. decem ('ten') is spelled out as an ordinary word, "
        "not written numerically, so per the scheme docs' own "
        "clarification it's tokentype 'lexical' -- NOT 'numeral' -- and "
        "modifies Fratres via 'adjectival', the same relation an "
        "ordinary adjective quantifying a noun would use."
    ),
    "verbalunits": [
        {"id": "t3", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Fratres", "tokentype": "lexical", "lemma": "frater",
         "relations": [{"related": "t3", "relationship": "subject"}]},
        {"id": "t1", "token": "Joseph", "tokentype": "lexical", "lemma": "Joseph",
         "relations": [{"related": "t0", "relationship": "genitive"}]},
        {"id": "t2", "token": "decem", "tokentype": "lexical", "lemma": "decem",
         "relations": [{"related": "t0", "relationship": "adjectival"}]},
        {"id": "t3", "token": "venerunt", "tokentype": "lexical", "lemma": "venio", "verbalunitid": "t3",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t4", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Fratres Joseph XII venerunt." -- a direct parallel to
# lexical_numeral_fratres_joseph_decem immediately above, swapping "decem"
# (lexical, spelled-out "ten") for "XII" (numeral, written numerically) at
# the exact same position/relation. This is the regression fixture for the
# bug the user reported: a numeral token with a real relation (here
# "adjectival" -> Fratres, same as decem's) was colored correctly in the
# Mermaid diagram but left uncolored in tokengraph_to_html()/
# tokengraph_to_depth_html() before the fix, because _tokens_to_html()'s
# tokentype-eligibility check omitted "numeral". Deliberately NOT the
# user's own bug-report sentence ("nati sunt Jacob filii XII.") -- that
# sentence uses an unprecedented deponent-verb perfect construction with no
# other fixture anywhere in this file, and "Jacob" is genitive-vs-dative
# ambiguous (an indeclinable Hebrew name) -- building an unprecedented,
# ambiguous analysis into an asserted-correct gold fixture would carry
# correctness risk unrelated to the rendering bug actually being tested.
# ---------------------------------------------------------------------------

_NUMERAL_RELATION_FRATRES_JOSEPH_XII_ANSWER = {
    "reasoning": (
        "venerunt is the independent main verb (intransitive, 'they "
        "came'), with the sentinel relatedtoken1 'root'; Fratres is its "
        "subject. Joseph, an indeclinable Hebrew name here in genitive "
        "function ('brothers OF Joseph'), depends on Fratres via "
        "'genitive'. XII ('twelve') is written numerically, so per "
        "the scheme docs' own clarification it's tokentype 'numeral' -- "
        "NOT 'lexical' -- but still modifies Fratres via 'adjectival', "
        "the same relation decem (spelled out) or an ordinary adjective "
        "quantifying a noun would use."
    ),
    "verbalunits": [
        {"id": "t3", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Fratres", "tokentype": "lexical", "lemma": "frater",
         "relations": [{"related": "t3", "relationship": "subject"}]},
        {"id": "t1", "token": "Joseph", "tokentype": "lexical", "lemma": "Joseph",
         "relations": [{"related": "t0", "relationship": "genitive"}]},
        {"id": "t2", "token": "XII", "tokentype": "numeral",
         "relations": [{"related": "t0", "relationship": "adjectival"}]},
        {"id": "t3", "token": "venerunt", "tokentype": "lexical", "lemma": "venio", "verbalunitid": "t3",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t4", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "principes Albanorum in patres, ut ea quoque pars rei publicae cresceret, legit."
#   t0 principes  t1 Albanorum  t2 in     t3 patres    t4 ,
#   t5 ut         t6 ea         t7 quoque t8 pars      t9 rei
#   t10 publicae  t11 cresceret t12 ,     t13 legit    t14 .
#
# The worked example for 'independent' vs 'dependent'
# (quarto/concepts/verbalunits.qmd): legit is independent, cresceret
# dependent (introduced by ut). Every word now has a relation: Albanorum is
# a genitive with principes; ea is adjectival to pars and quoque adverbial
# to ea; rei is a genitive with pars and publicae adjectival to rei.
# ---------------------------------------------------------------------------
 
_SYNTACTIC_TYPE_ANSWER = {
    "reasoning": (
        "legit is the independent main verb, with principes as its direct "
        "object; Albanorum is a genitive depending on principes, and in "
        "patres is an adverbial phrase. cresceret is the verb of the "
        "dependent ut-clause (unit verb -> ut; ut -> legit as subordinating "
        "word), with pars as its subject. ea is adjectival to pars and quoque "
        "('too') emphasizes ea. rei is a genitive with pars, and publicae is "
        "adjectival to rei."
    ),
    "verbalunits": [
        {"id": "t11", "syntactic_type": "dependent"},
        {"id": "t13", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "principes", "tokentype": "lexical", "lemma": "princeps",
         "relations": [{"related": "t13", "relationship": "direct object"}]},
        {"id": "t1", "token": "Albanorum", "tokentype": "lexical", "lemma": "Albanus",
         "relations": [{"related": "t0", "relationship": "genitive"}]},
        {"id": "t2", "token": "in", "tokentype": "lexical", "lemma": "in",
         "relations": [{"related": "t13", "relationship": "adverbial"}]},
        {"id": "t3", "token": "patres", "tokentype": "lexical", "lemma": "pater",
         "relations": [{"related": "t2", "relationship": "object of preposition"}]},
        {"id": "t4", "token": ",", "tokentype": "punctuation"},
        {"id": "t5", "token": "ut", "tokentype": "lexical", "lemma": "ut",
         "relations": [{"related": "t13", "relationship": "subordinating word"}]},
        {"id": "t6", "token": "ea", "tokentype": "lexical", "lemma": "is",
         "relations": [{"related": "t8", "relationship": "adjectival"}]},
        {"id": "t7", "token": "quoque", "tokentype": "lexical", "lemma": "quoque",
         "relations": [{"related": "t6", "relationship": "adverbial"}]},
        {"id": "t8", "token": "pars", "tokentype": "lexical", "lemma": "pars",
         "relations": [{"related": "t11", "relationship": "subject"}]},
        {"id": "t9", "token": "rei", "tokentype": "lexical", "lemma": "res",
         "relations": [{"related": "t8", "relationship": "genitive"}]},
        {"id": "t10", "token": "publicae", "tokentype": "lexical", "lemma": "publicus",
         "relations": [{"related": "t9", "relationship": "adjectival"}]},
        {"id": "t11", "token": "cresceret", "tokentype": "lexical", "lemma": "cresco", "verbalunitid": "t11",
         "relations": [{"related": "t5", "relationship": "unit verb"}]},
        {"id": "t12", "token": ",", "tokentype": "punctuation"},
        {"id": "t13", "token": "legit", "tokentype": "lexical", "lemma": "lego", "verbalunitid": "t13",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t14", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "urbs a Romulo condita est."
#   t0 urbs  t1 a  t2 Romulo  t3 condita  t4 est  t5 .
#
# Originally the worked example for the retired *transitive passive*
# semantic type (hence the slug). Also the worked example for the
# 'agent-ablative' relation (formerly 'agent') (a/ab plus an
# ablative introduces the agent of a passive verb) AND, once the scheme docs (quarto/concepts/)
# spelled out the *auxiliary* relation, its own worked example for that too:
# "if urbs a Romulo condita est is tokenized ... est has for its relation1
# the value t3 (condita), and for relationship1, auxiliary." Per the
# compound-perfect-passive rule ("the participle or infinitive itself
# anchors the verbal expression"), the verbal expression and every relation
# into it (subject, agent) anchor on condita (t3), not est (t4) -- est
# instead relates to condita as its auxiliary, and condita (being
# independent) gets the "root" sentinel.
# ---------------------------------------------------------------------------

_TRANSITIVE_PASSIVE_ANSWER = {
    "reasoning": (
        "condita est is a compound perfect passive verbal expression, "
        "anchored at the id of condita (the participle) per the "
        "compound-form rule, with condita carrying the sentinel relation1 "
        "'root' as an independent verb and est relating to condita as its "
        "auxiliary; urbs is its subject; a introduces the agent of the "
        "passive verb, with Romulo as a's object of preposition."
    ),
    "verbalunits": [
        {"id": "t3", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "urbs", "tokentype": "lexical", "lemma": "urbs",
         "relations": [{"related": "t3", "relationship": "subject"}]},
        {"id": "t1", "token": "a", "tokentype": "lexical", "lemma": "a",
         "relations": [{"related": "t3", "relationship": "agent-ablative"}]},
        {"id": "t2", "token": "Romulo", "tokentype": "lexical", "lemma": "Romulus",
         "relations": [{"related": "t1", "relationship": "object of preposition"}]},
        {"id": "t3", "token": "condita", "tokentype": "lexical", "lemma": "condo", "verbalunitid": "t3",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t4", "token": "est", "tokentype": "lexical", "lemma": "sum",
         "relations": [{"related": "t3", "relationship": "auxiliary"}]},
        {"id": "t5", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "Etruria erat vicina."
#   t0 Etruria  t1 erat  t2 vicina  t3 .
#
# Originally the worked example for the retired *linking verb* semantic
# type (hence the slug). vicina is erat's predicate adjective;
# it originally got no relation (the scheme didn't yet cover predicate
# complements when this fixture was first written) -- now that
# the scheme docs' "predicate" relation covers exactly this case, vicina
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
        {"id": "t1", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Etruria", "tokentype": "lexical", "lemma": "Etruria",
         "relations": [{"related": "t1", "relationship": "subject"}]},
        {"id": "t1", "token": "erat", "tokentype": "lexical", "lemma": "sum", "verbalunitid": "t1",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t2", "token": "vicina", "tokentype": "lexical", "lemma": "vicinus",
         "relations": [{"related": "t1", "relationship": "predicate"}]},
        {"id": "t3", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "gloria est consentiens laus bonorum."
#   t0 gloria  t1 est  t2 consentiens  t3 laus  t4 bonorum  t5 .
#
# the scheme docs' own worked example for a participle used *attributively*
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
        {"id": "t1", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "gloria", "tokentype": "lexical", "lemma": "gloria",
         "relations": [{"related": "t1", "relationship": "subject"}]},
        {"id": "t1", "token": "est", "tokentype": "lexical", "lemma": "sum", "verbalunitid": "t1",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t2", "token": "consentiens", "tokentype": "lexical", "lemma": "consentio",
         "relations": [{"related": "t3", "relationship": "adjectival"}]},
        {"id": "t3", "token": "laus", "tokentype": "lexical", "lemma": "laus",
         "relations": [{"related": "t1", "relationship": "predicate"}]},
        {"id": "t4", "token": "bonorum", "tokentype": "lexical", "lemma": "bonus",
         "relations": [{"related": "t3", "relationship": "genitive"}]},
        {"id": "t5", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "Anco regnante Lucumo Romam commigravit."
#   t0 Anco  t1 regnante  t2 Lucumo  t3 Romam  t4 commigravit  t5 .
#
# The worked example for a circumstantial participle in an ablative
# absolute: regnante anchors a 'circumstantial participle' verbal
# expression and relates to Anco; Anco relates to commigravit as 'ablative
# absolute'. Romam is an accusative (of place to which) with commigravit.
# ---------------------------------------------------------------------------
 
_PARTICIPLE_PREDICATE_ANSWER = {
    "reasoning": (
        "commigravit is the independent main verb, with Lucumo as its subject "
        "and Romam as an accusative of place to which. regnante is a "
        "circumstantial participle ('while Ancus was reigning') anchoring its "
        "own verbal expression; it relates to Anco, which stands in an "
        "ablative absolute relation to commigravit."
    ),
    "verbalunits": [
        {"id": "t1", "syntactic_type": "circumstantial participle"},
        {"id": "t4", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Anco", "tokentype": "lexical", "lemma": "Ancus",
         "relations": [{"related": "t4", "relationship": "ablative absolute"}]},
        {"id": "t1", "token": "regnante", "tokentype": "lexical", "lemma": "regno", "verbalunitid": "t1",
         "relations": [{"related": "t0", "relationship": "circumstantial participle"}]},
        {"id": "t2", "token": "Lucumo", "tokentype": "lexical", "lemma": "Lucumo",
         "relations": [{"related": "t4", "relationship": "subject"}]},
        {"id": "t3", "token": "Romam", "tokentype": "lexical", "lemma": "Roma",
         "relations": [{"related": "t4", "relationship": "accusative"}]},
        {"id": "t4", "token": "commigravit", "tokentype": "lexical", "lemma": "commigro", "verbalunitid": "t4",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t5", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "Eum advenientem laeti omnes accepere."
#   t0 Eum  t1 advenientem  t2 laeti  t3 omnes  t4 accepere  t5 .
#
# A circumstantial participle whose substantive also has a normal role in
# the clause: advenientem -> eum ('circumstantial participle'), and eum is
# the direct object of accepere.
# ---------------------------------------------------------------------------
 
_CIRCUMSTANTIAL_PARTICIPLE_ANSWER = {
    "reasoning": (
        "accepere is the independent main verb, with omnes as its subject "
        "(laeti adjectival to omnes) and eum as its direct object. "
        "advenientem is a circumstantial participle ('as he arrived') "
        "anchoring its own verbal expression and relating to eum, which keeps "
        "its normal role as direct object."
    ),
    "verbalunits": [
        {"id": "t1", "syntactic_type": "circumstantial participle"},
        {"id": "t4", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Eum", "tokentype": "lexical", "lemma": "is",
         "relations": [{"related": "t4", "relationship": "direct object"}]},
        {"id": "t1", "token": "advenientem", "tokentype": "lexical", "lemma": "advenio", "verbalunitid": "t1",
         "relations": [{"related": "t0", "relationship": "circumstantial participle"}]},
        {"id": "t2", "token": "laeti", "tokentype": "lexical", "lemma": "laetus",
         "relations": [{"related": "t3", "relationship": "adjectival"}]},
        {"id": "t3", "token": "omnes", "tokentype": "lexical", "lemma": "omnis",
         "relations": [{"related": "t4", "relationship": "subject"}]},
        {"id": "t4", "token": "accepere", "tokentype": "lexical", "lemma": "accipio", "verbalunitid": "t4",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t5", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "Facturum enim se fuisse dixit."
#   t0 Facturum  t1 enim  t2 se  t3 fuisse  t4 dixit  t5 .
#
# The worked example for a compound future infinitive in indirect statement
# (quarto/concepts/verbalunits.qmd): facturum anchors the 'indirect
# statement' verbal expression and fuisse is its auxiliary. enim, a
# connective linking the sentence to what precedes, is a 'coordinating
# word' -> dixit.
# ---------------------------------------------------------------------------

_INDIRECT_STATEMENT_ANSWER = {
    "reasoning": (
        "dixit is the independent main verb. facturum fuisse is a compound "
        "infinitive anchored on facturum, which relates to dixit as 'indirect "
        "statement'; fuisse is its auxiliary and se its accusative subject. "
        "enim connects the sentence to the preceding one and relates to dixit "
        "as 'coordinating word'."
    ),
    "verbalunits": [
        {"id": "t0", "syntactic_type": "indirect statement"},
        {"id": "t4", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Facturum", "tokentype": "lexical", "lemma": "facio", "verbalunitid": "t0",
         "relations": [{"related": "t4", "relationship": "indirect statement"}]},
        {"id": "t1", "token": "enim", "tokentype": "lexical", "lemma": "enim",
         "relations": [{"related": "t4", "relationship": "coordinating word"}]},
        {"id": "t2", "token": "se", "tokentype": "lexical", "lemma": "se",
         "relations": [{"related": "t0", "relationship": "subject"}]},
        {"id": "t3", "token": "fuisse", "tokentype": "lexical", "lemma": "sum",
         "relations": [{"related": "t0", "relationship": "auxiliary"}]},
        {"id": "t4", "token": "dixit", "tokentype": "lexical", "lemma": "dico", "verbalunitid": "t4",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t5", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "Tuum est, inquit, Servi regnum."
#   t0 Tuum  t1 est  t2 ,  t3 inquit  t4 ,  t5 Servi  t6 regnum  t7 .
#
# the scheme docs' own worked example for the 'direct quote' syntactic
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
        {"id": "t1", "syntactic_type": "direct quote"},
        {"id": "t3", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Tuum", "tokentype": "lexical", "lemma": "tuus",
         "relations": [{"related": "t1", "relationship": "predicate"}]},
        {"id": "t1", "token": "est", "tokentype": "lexical", "lemma": "sum", "verbalunitid": "t1",
         "relations": [{"related": "t3", "relationship": "direct quote"}]},
        {"id": "t2", "token": ",", "tokentype": "punctuation"},
        {"id": "t3", "token": "inquit", "tokentype": "lexical", "lemma": "inquam", "verbalunitid": "t3",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t4", "token": ",", "tokentype": "punctuation"},
        {"id": "t5", "token": "Servi", "tokentype": "lexical", "lemma": "Servius",
         "relations": [{"related": "t6", "relationship": "genitive"}]},
        {"id": "t6", "token": "regnum", "tokentype": "lexical", "lemma": "regnum",
         "relations": [{"related": "t1", "relationship": "subject"}]},
        {"id": "t7", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "Equidem, pace dixerim deum, eos nos iam populi Romani beneficio esse spero."
#   t0 Equidem  t1 ,  t2 pace  t3 dixerim  t4 deum  t5 ,  t6 eos  t7 nos
#   t8 iam  t9 populi  t10 Romani  t11 beneficio  t12 esse  t13 spero  t14 .
#
# The worked example for 'aside' (quarto/concepts/verbalunits.qmd): dixerim
# interrupts the sentence and relates to spero as 'aside'. In the indirect
# statement, nos is the subject of esse and eos its predicate ('that we are
# those...'); the earlier fixture left nos unrelated. Judgment call: eos as
# subject and nos as predicate is also grammatically possible, but the
# sense favors nos as subject.
# ---------------------------------------------------------------------------

_ASIDE_ANSWER = {
    "reasoning": (
        "spero is the independent main verb. dixerim anchors an aside ('pace "
        "dixerim deum') relating to spero, with pace as an ablative and deum "
        "a genitive with pace. esse is an indirect statement after spero; nos "
        "is its subject and eos its predicate ('that we are now those "
        "[who]...'). iam is adverbial to esse, and beneficio an ablative with "
        "esse, with populi Romani a genitive depending on it. Close call: the "
        "roles of eos and nos could be reversed grammatically; the sense "
        "favors nos as subject."
    ),
    "verbalunits": [
        {"id": "t3", "syntactic_type": "aside"},
        {"id": "t12", "syntactic_type": "indirect statement"},
        {"id": "t13", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Equidem", "tokentype": "lexical", "lemma": "equidem",
         "relations": [{"related": "t13", "relationship": "adverbial"}]},
        {"id": "t1", "token": ",", "tokentype": "punctuation"},
        {"id": "t2", "token": "pace", "tokentype": "lexical", "lemma": "pax",
         "relations": [{"related": "t3", "relationship": "ablative"}]},
        {"id": "t3", "token": "dixerim", "tokentype": "lexical", "lemma": "dico", "verbalunitid": "t3",
         "relations": [{"related": "t13", "relationship": "aside"}]},
        {"id": "t4", "token": "deum", "tokentype": "lexical", "lemma": "deus",
         "relations": [{"related": "t2", "relationship": "genitive"}]},
        {"id": "t5", "token": ",", "tokentype": "punctuation"},
        {"id": "t6", "token": "eos", "tokentype": "lexical", "lemma": "is",
         "relations": [{"related": "t12", "relationship": "predicate"}]},
        {"id": "t7", "token": "nos", "tokentype": "lexical", "lemma": "ego",
         "relations": [{"related": "t12", "relationship": "subject"}]},
        {"id": "t8", "token": "iam", "tokentype": "lexical", "lemma": "iam",
         "relations": [{"related": "t12", "relationship": "adverbial"}]},
        {"id": "t9", "token": "populi", "tokentype": "lexical", "lemma": "populus",
         "relations": [{"related": "t11", "relationship": "genitive"}]},
        {"id": "t10", "token": "Romani", "tokentype": "lexical", "lemma": "Romanus",
         "relations": [{"related": "t9", "relationship": "adjectival"}]},
        {"id": "t11", "token": "beneficio", "tokentype": "lexical", "lemma": "beneficium",
         "relations": [{"related": "t12", "relationship": "ablative"}]},
        {"id": "t12", "token": "esse", "tokentype": "lexical", "lemma": "sum", "verbalunitid": "t12",
         "relations": [{"related": "t13", "relationship": "indirect statement"}]},
        {"id": "t13", "token": "spero", "tokentype": "lexical", "lemma": "spero", "verbalunitid": "t13",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t14", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "Lucumo Demarati Corinthii filius erat."
#   t0 Lucumo  t1 Demarati  t2 Corinthii  t3 filius  t4 erat  t5 .
#
# the scheme docs' own worked example for the *predicate* relation:
# "Lucumo is the subject of the linking verb erat, and filius is the
# predicate." Also covers *genitive* (Demarati depends on filius) and
# *adjectival* (Corinthii, "the Corinthian", agreeing with Demarati) in the
# same sentence -- close enough to the scheme docs' separate, structurally
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
        {"id": "t4", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Lucumo", "tokentype": "lexical", "lemma": "Lucumo",
         "relations": [{"related": "t4", "relationship": "subject"}]},
        {"id": "t1", "token": "Demarati", "tokentype": "lexical", "lemma": "Demaratus",
         "relations": [{"related": "t3", "relationship": "genitive"}]},
        {"id": "t2", "token": "Corinthii", "tokentype": "lexical", "lemma": "Corinthius",
         "relations": [{"related": "t1", "relationship": "adjectival"}]},
        {"id": "t3", "token": "filius", "tokentype": "lexical", "lemma": "filius",
         "relations": [{"related": "t4", "relationship": "predicate"}]},
        {"id": "t4", "token": "erat", "tokentype": "lexical", "lemma": "sum", "verbalunitid": "t4",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t5", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "Latini, cum quibus ictum foedus erat, sustulerant animos."
#   t0 Latini  t1 ,  t2 cum  t3 quibus  t4 ictum  t5 foedus  t6 erat  t7 ,
#   t8 sustulerant  t9 animos  t10 .
#
# the scheme docs' own worked table example for *relative pronoun* --
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
        "modifying ictum. ictum foedus erat is a dependent compound perfect "
        "passive verbal expression (transitive passive) anchored at ictum, "
        "linked to quibus as its unit verb; foedus is its subject, erat "
        "relates to ictum as its auxiliary. sustulerant is the independent "
        "main verb (root, transitive active), with Latini as its subject "
        "and animos as its direct object."
    ),
    "verbalunits": [
        {"id": "t4", "syntactic_type": "dependent"},
        {"id": "t8", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Latini", "tokentype": "lexical", "lemma": "Latini",
         "relations": [{"related": "t8", "relationship": "subject"}]},
        {"id": "t1", "token": ",", "tokentype": "punctuation"},
        {"id": "t2", "token": "cum", "tokentype": "lexical", "lemma": "cum",
         "relations": [{"related": "t4", "relationship": "adverbial"}]},
        {"id": "t3", "token": "quibus", "tokentype": "lexical", "lemma": "qui",
         "relations": [{"related": "t0", "relationship": "relative pronoun"}, {"related": "t2", "relationship": "object of preposition"}]},
        {"id": "t4", "token": "ictum", "tokentype": "lexical", "lemma": "icio", "verbalunitid": "t4",
         "relations": [{"related": "t3", "relationship": "unit verb"}]},
        {"id": "t5", "token": "foedus", "tokentype": "lexical", "lemma": "foedus",
         "relations": [{"related": "t4", "relationship": "subject"}]},
        {"id": "t6", "token": "erat", "tokentype": "lexical", "lemma": "sum",
         "relations": [{"related": "t4", "relationship": "auxiliary"}]},
        {"id": "t7", "token": ",", "tokentype": "punctuation"},
        {"id": "t8", "token": "sustulerant", "tokentype": "lexical", "lemma": "tollo", "verbalunitid": "t8",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t9", "token": "animos", "tokentype": "lexical", "lemma": "animus",
         "relations": [{"related": "t8", "relationship": "direct object"}]},
        {"id": "t10", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "Lucumo superfuit patri bonorum omnium heres."
#   t0 Lucumo  t1 superfuit  t2 patri  t3 bonorum  t4 omnium  t5 heres  t6 .
#
# heres is a 'predicate' of role or state with superfuit (use 2 in
# quarto/concepts/syntactic-analysis.qmd), not a target in the A-A-T model.
# bonorum (adjective used as a substantive) is a genitive with heres, and
# omnium adjectival to bonorum.
# ---------------------------------------------------------------------------
 
_DATIVE_GENITIVE_ANSWER = {
    "reasoning": (
        "superfuit is the independent main verb, with Lucumo as its subject "
        "and patri as a dative. heres gives the role in which Lucumo survived "
        "('as heir') and is a predicate of superfuit. bonorum ('goods', an "
        "adjective used as a substantive) is a genitive depending on heres, "
        "and omnium is adjectival to bonorum."
    ),
    "verbalunits": [
        {"id": "t1", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Lucumo", "tokentype": "lexical", "lemma": "Lucumo",
         "relations": [{"related": "t1", "relationship": "subject"}]},
        {"id": "t1", "token": "superfuit", "tokentype": "lexical", "lemma": "supersum", "verbalunitid": "t1",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t2", "token": "patri", "tokentype": "lexical", "lemma": "pater",
         "relations": [{"related": "t1", "relationship": "dative"}]},
        {"id": "t3", "token": "bonorum", "tokentype": "lexical", "lemma": "bonus",
         "relations": [{"related": "t5", "relationship": "genitive"}]},
        {"id": "t4", "token": "omnium", "tokentype": "lexical", "lemma": "omnis",
         "relations": [{"related": "t3", "relationship": "adjectival"}]},
        {"id": "t5", "token": "heres", "tokentype": "lexical", "lemma": "heres",
         "relations": [{"related": "t1", "relationship": "predicate"}]},
        {"id": "t6", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "Ad Ianiculum forte ventum erat."
#   t0 Ad  t1 Ianiculum  t2 forte  t3 ventum  t4 erat  t5 .
#
# the scheme docs' own worked example for a bare *adverb* modifying a verb,
# and for *auxiliary* on an impersonal passive of an intransitive verb:
# "the adverb forte will take the id of ventum for relation1 with
# relationship1 value adverbial. (erat will be related to ventum but with
# relationship1 value auxiliary)." "ventum erat" (impersonal passive of
# venio, 'there had been a coming') has no subject to assign -- there's no
# accusative or nominative to promote into that role.
# ---------------------------------------------------------------------------

_ADVERB_AUXILIARY_ANSWER = {
    "reasoning": (
        "ventum is the independent verb (root) of an impersonal passive "
        "construction ('ventum erat', 'there had been a coming'), with no "
        "subject; erat relates to it as auxiliary. Ad is adverbial, "
        "modifying ventum, governing Ianiculum as its object of preposition; "
        "forte is a bare adverb, also adverbial, modifying ventum."
    ),
    "verbalunits": [
        {"id": "t3", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Ad", "tokentype": "lexical", "lemma": "ad",
         "relations": [{"related": "t3", "relationship": "adverbial"}]},
        {"id": "t1", "token": "Ianiculum", "tokentype": "lexical", "lemma": "Ianiculum",
         "relations": [{"related": "t0", "relationship": "object of preposition"}]},
        {"id": "t2", "token": "forte", "tokentype": "lexical", "lemma": "forte",
         "relations": [{"related": "t3", "relationship": "adverbial"}]},
        {"id": "t3", "token": "ventum", "tokentype": "lexical", "lemma": "venio", "verbalunitid": "t3",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t4", "token": "erat", "tokentype": "lexical", "lemma": "sum",
         "relations": [{"related": "t3", "relationship": "auxiliary"}]},
        {"id": "t5", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "Omnia ferro flammaque miscet."
#   t0 Omnia  t1 ferro  t2 flamma  t3 que  t4 miscet  t5 .
#
# Two ablatives with miscet, joined by the enclitic que, which relates to
# both as 'coordinating word'.
# ---------------------------------------------------------------------------
 
_ABLATIVE_ANSWER = {
    "reasoning": (
        "miscet is the independent main verb, with omnia as its direct "
        "object. ferro and flamma are both ablatives with miscet, joined by "
        "the enclitic que, which relates to each of them as a coordinating "
        "word."
    ),
    "verbalunits": [
        {"id": "t4", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Omnia", "tokentype": "lexical", "lemma": "omnis",
         "relations": [{"related": "t4", "relationship": "direct object"}]},
        {"id": "t1", "token": "ferro", "tokentype": "lexical", "lemma": "ferrum",
         "relations": [{"related": "t4", "relationship": "ablative"}]},
        {"id": "t2", "token": "flamma", "tokentype": "lexical", "lemma": "flamma",
         "relations": [{"related": "t4", "relationship": "ablative"}]},
        {"id": "t3", "token": "que", "tokentype": "enclitic",
         "relations": [{"related": "t1", "relationship": "coordinating word"}, {"related": "t2", "relationship": "coordinating word"}]},
        {"id": "t4", "token": "miscet", "tokentype": "lexical", "lemma": "misceo", "verbalunitid": "t4",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t5", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "Audeat deinde talia alius, nisi in hunc insigne iam documentum
#  mortalibus dedero."
#   t0 Audeat  t1 deinde  t2 talia  t3 alius  t4 ,  t5 nisi  t6 in  t7 hunc
#   t8 insigne  t9 iam  t10 documentum  t11 mortalibus  t12 dedero  t13 .
#
# the scheme docs' own worked example for *dative*: "the dative noun
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
        {"id": "t0", "syntactic_type": "independent"},
        {"id": "t12", "syntactic_type": "dependent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Audeat", "tokentype": "lexical", "lemma": "audeo", "verbalunitid": "t0",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t1", "token": "deinde", "tokentype": "lexical", "lemma": "deinde",
         "relations": [{"related": "t0", "relationship": "adverbial"}]},
        {"id": "t2", "token": "talia", "tokentype": "lexical", "lemma": "talis",
         "relations": [{"related": "t0", "relationship": "direct object"}]},
        {"id": "t3", "token": "alius", "tokentype": "lexical", "lemma": "alius",
         "relations": [{"related": "t0", "relationship": "subject"}]},
        {"id": "t4", "token": ",", "tokentype": "punctuation"},
        {"id": "t5", "token": "nisi", "tokentype": "lexical", "lemma": "nisi",
         "relations": [{"related": "t0", "relationship": "subordinating word"}]},
        {"id": "t6", "token": "in", "tokentype": "lexical", "lemma": "in",
         "relations": [{"related": "t12", "relationship": "adverbial"}]},
        {"id": "t7", "token": "hunc", "tokentype": "lexical", "lemma": "hic",
         "relations": [{"related": "t6", "relationship": "object of preposition"}]},
        {"id": "t8", "token": "insigne", "tokentype": "lexical", "lemma": "insignis",
         "relations": [{"related": "t10", "relationship": "adjectival"}]},
        {"id": "t9", "token": "iam", "tokentype": "lexical", "lemma": "iam",
         "relations": [{"related": "t12", "relationship": "adverbial"}]},
        {"id": "t10", "token": "documentum", "tokentype": "lexical", "lemma": "documentum",
         "relations": [{"related": "t12", "relationship": "direct object"}]},
        {"id": "t11", "token": "mortalibus", "tokentype": "lexical", "lemma": "mortalis",
         "relations": [{"related": "t12", "relationship": "dative"}]},
        {"id": "t12", "token": "dedero", "tokentype": "lexical", "lemma": "do", "verbalunitid": "t12",
         "relations": [{"related": "t5", "relationship": "unit verb"}]},
        {"id": "t13", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "Pugna ad Cannas fuit clara."
#   t0 Pugna  t1 ad  t2 Cannas  t3 fuit  t4 clara  t5 .
#
# the scheme docs' own worked example for *attributive* (a prepositional
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
        {"id": "t3", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Pugna", "tokentype": "lexical", "lemma": "pugna",
         "relations": [{"related": "t3", "relationship": "subject"}]},
        {"id": "t1", "token": "ad", "tokentype": "lexical", "lemma": "ad",
         "relations": [{"related": "t0", "relationship": "adjectival"}]},
        {"id": "t2", "token": "Cannas", "tokentype": "lexical", "lemma": "Cannas",
         "relations": [{"related": "t1", "relationship": "object of preposition"}]},
        {"id": "t3", "token": "fuit", "tokentype": "lexical", "lemma": "sum", "verbalunitid": "t3",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t4", "token": "clara", "tokentype": "lexical", "lemma": "clarus",
         "relations": [{"related": "t3", "relationship": "predicate"}]},
        {"id": "t5", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Aequa ratione imperat."
#   t0 Aequa  t1 ratione  t2 imperat  t3 .
#
# the scheme docs' revised *enclitic* section's own worked example for
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
        {"id": "t2", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Aequa", "tokentype": "lexical", "lemma": "aequus",
         "relations": [{"related": "t1", "relationship": "adjectival"}]},
        {"id": "t1", "token": "ratione", "tokentype": "lexical", "lemma": "ratio",
         "relations": [{"related": "t2", "relationship": "ablative"}]},
        {"id": "t2", "token": "imperat", "tokentype": "lexical", "lemma": "impero", "verbalunitid": "t2",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t3", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Ratione docet?"
#   t0 Ratio  t1 ne  t2 docet  t3 ?
#
# The context-sensitive enclitic: here ratione is ratio + the interrogative
# enclitic ne. ne is 'adverbial' to docet (marking the question).
# ---------------------------------------------------------------------------

_ENCLITIC_CONTEXT_INTERROGATIVE_ANSWER = {
    "reasoning": (
        "docet is the independent main verb, and ratio (with the "
        "interrogative enclitic -ne attached) is its subject. ne marks the "
        "sentence as a question and is adverbial to docet."
    ),
    "verbalunits": [
        {"id": "t2", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Ratio", "tokentype": "lexical", "lemma": "ratio",
         "relations": [{"related": "t2", "relationship": "subject"}]},
        {"id": "t1", "token": "ne", "tokentype": "enclitic",
         "relations": [{"related": "t2", "relationship": "adverbial"}]},
        {"id": "t2", "token": "docet", "tokentype": "lexical", "lemma": "doceo", "verbalunitid": "t2",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t3", "token": "?", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Quisque officium suum fecit."
#   t0 Quisque  t1 officium  t2 suum  t3 fecit  t4 .
#
# the scheme docs' revised *enclitic* section's other worked example:
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
        {"id": "t3", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Quisque", "tokentype": "lexical", "lemma": "quisque",
         "relations": [{"related": "t3", "relationship": "subject"}]},
        {"id": "t1", "token": "officium", "tokentype": "lexical", "lemma": "officium",
         "relations": [{"related": "t3", "relationship": "direct object"}]},
        {"id": "t2", "token": "suum", "tokentype": "lexical", "lemma": "suus",
         "relations": [{"related": "t1", "relationship": "adjectival"}]},
        {"id": "t3", "token": "fecit", "tokentype": "lexical", "lemma": "facio", "verbalunitid": "t3",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t4", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Ille noluit, Hermionenque ab Oreste adduxit."
#   t0 ille  t1 fidem  t2 suam  t3 infirmare  t4 noluit  t5 ,
#   t6 Hermionen  t7 que  t8 ab  t9 Oreste  t10 adduxit  t11 .
#
# que joins two verbal expressions (noluit, adduxit) even though it is
# attached to Hermionen. infirmare is a complementary infinitive with
# noluit, fidem its direct object and suam adjectival to fidem.
# ---------------------------------------------------------------------------

_COORDINATING_CONJUNCTION_VERBS_ANSWER = {
    "reasoning": (
        "noluit and adduxit are two independent verbs joined by the enclitic "
        "que, which relates to both verbs even though it is written on "
        "Hermionen, the direct object of adduxit. Ille is the subject of "
        "noluit; infirmare is a complementary infinitive with noluit, with "
        "fidem as its direct object and suam adjectival to fidem. ab Oreste "
        "is an adverbial phrase with adduxit."
    ),
    "verbalunits": [
        {"id": "t4", "syntactic_type": "independent"},
        {"id": "t10", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Ille", "tokentype": "lexical", "lemma": "ille",
         "relations": [{"related": "t4", "relationship": "subject"}]},
        {"id": "t1", "token": "fidem", "tokentype": "lexical", "lemma": "fides",
         "relations": [{"related": "t3", "relationship": "direct object"}]},
        {"id": "t2", "token": "suam", "tokentype": "lexical", "lemma": "suus",
         "relations": [{"related": "t1", "relationship": "adjectival"}]},
        {"id": "t3", "token": "infirmare", "tokentype": "lexical", "lemma": "infirmo",
         "relations": [{"related": "t4", "relationship": "complementary infinitive"}]},
        {"id": "t4", "token": "noluit", "tokentype": "lexical", "lemma": "nolo", "verbalunitid": "t4",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t5", "token": ",", "tokentype": "punctuation"},
        {"id": "t6", "token": "Hermionen", "tokentype": "lexical", "lemma": "Hermione",
         "relations": [{"related": "t10", "relationship": "direct object"}]},
        {"id": "t7", "token": "que", "tokentype": "enclitic",
         "relations": [{"related": "t4", "relationship": "coordinating word"}, {"related": "t10", "relationship": "coordinating word"}]},
        {"id": "t8", "token": "ab", "tokentype": "lexical", "lemma": "ab",
         "relations": [{"related": "t10", "relationship": "adverbial"}]},
        {"id": "t9", "token": "Oreste", "tokentype": "lexical", "lemma": "Orestes",
         "relations": [{"related": "t8", "relationship": "object of preposition"}]},
        {"id": "t10", "token": "adduxit", "tokentype": "lexical", "lemma": "adduco", "verbalunitid": "t10",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t11", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Sed re cognita, iussu Cereris Triptolemo regnum dedit."
#   t0 sed  t1 re  t2 cognita  t3 ,  t4 iussu  t5 Cereris  t6 Triptolemo
#   t7 regnum  t8 dedit  t9 .
#
# A connective opening a sentence: sed relates only to dedit ('coordinating
# word'). re cognita is an ablative absolute: cognita anchors a
# 'circumstantial participle' verbal expression.
# ---------------------------------------------------------------------------

_COORDINATING_CONJUNCTION_SENTENCE_INITIAL_ANSWER = {
    "reasoning": (
        "dedit is the independent main verb, with regnum as its direct object "
        "and Triptolemo as a dative. sed connects the sentence to what "
        "precedes and relates only to dedit. cognita is a circumstantial "
        "participle relating to re, which stands in an ablative absolute "
        "relation to dedit. iussu is an ablative with dedit, and Cereris a "
        "genitive with iussu."
    ),
    "verbalunits": [
        {"id": "t2", "syntactic_type": "circumstantial participle"},
        {"id": "t8", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Sed", "tokentype": "lexical", "lemma": "sed",
         "relations": [{"related": "t8", "relationship": "coordinating word"}]},
        {"id": "t1", "token": "re", "tokentype": "lexical", "lemma": "res",
         "relations": [{"related": "t8", "relationship": "ablative absolute"}]},
        {"id": "t2", "token": "cognita", "tokentype": "lexical", "lemma": "cognosco", "verbalunitid": "t2",
         "relations": [{"related": "t1", "relationship": "circumstantial participle"}]},
        {"id": "t3", "token": ",", "tokentype": "punctuation"},
        {"id": "t4", "token": "iussu", "tokentype": "lexical", "lemma": "iussus",
         "relations": [{"related": "t8", "relationship": "ablative"}]},
        {"id": "t5", "token": "Cereris", "tokentype": "lexical", "lemma": "Ceres",
         "relations": [{"related": "t4", "relationship": "genitive"}]},
        {"id": "t6", "token": "Triptolemo", "tokentype": "lexical", "lemma": "Triptolemus",
         "relations": [{"related": "t8", "relationship": "dative"}]},
        {"id": "t7", "token": "regnum", "tokentype": "lexical", "lemma": "regnum",
         "relations": [{"related": "t8", "relationship": "direct object"}]},
        {"id": "t8", "token": "dedit", "tokentype": "lexical", "lemma": "do", "verbalunitid": "t8",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t9", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Tu quoque, Brute, fili mi, et tu?"
#   t0 Tu  t1 quoque  t2 ,  t3 Brute  t4 ,  t5 fili  t6 mi  t7 ,
#   t8 et  t9 tu  t10 ?
#
# et used adverbially ('even, also'): 'adverbial' -> tu. The sentence has
# no verb, so the scheme gives no verbal expression and no relation for Tu,
# Brute or tu (see notes/model_switch_questions.md). quoque is adverbial to
# Tu; fili is in apposition to Brute; mi adjectival to fili.
# ---------------------------------------------------------------------------

_COORDINATING_CONJUNCTION_ET_AS_ADVERB_ANSWER = {
    "reasoning": (
        "This verbless exclamation has no verbal expression. et means 'even' "
        "here and is adverbial to the final tu. quoque is adverbial to Tu, "
        "fili is in apposition to the vocative Brute, and mi is adjectival to "
        "fili. Tu, Brute and tu have no verb to relate to; this is a genuine "
        "gap, not an oversight."
    ),
    "verbalunits": [
    ],
    "tokengraph": [
        {"id": "t0", "token": "Tu", "tokentype": "lexical", "lemma": "tu"},
        {"id": "t1", "token": "quoque", "tokentype": "lexical", "lemma": "quoque",
         "relations": [{"related": "t0", "relationship": "adverbial"}]},
        {"id": "t2", "token": ",", "tokentype": "punctuation"},
        {"id": "t3", "token": "Brute", "tokentype": "lexical", "lemma": "Brutus"},
        {"id": "t4", "token": ",", "tokentype": "punctuation"},
        {"id": "t5", "token": "fili", "tokentype": "lexical", "lemma": "filius",
         "relations": [{"related": "t3", "relationship": "apposition"}]},
        {"id": "t6", "token": "mi", "tokentype": "lexical", "lemma": "meus",
         "relations": [{"related": "t5", "relationship": "adjectival"}]},
        {"id": "t7", "token": ",", "tokentype": "punctuation"},
        {"id": "t8", "token": "et", "tokentype": "lexical", "lemma": "et",
         "relations": [{"related": "t9", "relationship": "adverbial"}]},
        {"id": "t9", "token": "tu", "tokentype": "lexical", "lemma": "tu"},
        {"id": "t10", "token": "?", "tokentype": "punctuation"},
    ],
}
# ---------------------------------------------------------------------------
# "Taurum cum quo Pasiphae concubuit ex Creta insula Mycenis uiuum adduxit."
#   t0 Taurum  t1 cum  t2 quo  t3 Pasiphae  t4 concubuit  t5 ex  t6 Creta
#   t7 insula  t8 Mycenis  t9 uiuum  t10 adduxit  t11 .
#
# Mycenis (place, ablative/locative by form) is an 'ablative' with adduxit;
# the earlier fixture left it unrelated.
# ---------------------------------------------------------------------------

_DEPTH_TAURUM_CONCUBUIT_ANSWER = {
    "reasoning": (
        "adduxit is the independent main verb, with Taurum as its direct "
        "object and uiuum adjectival to Taurum. quo is a relative pronoun "
        "with antecedent Taurum, and also the object of the preposition cum; "
        "concubuit relates to quo as 'unit verb', with Pasiphae as its "
        "subject, and cum is adverbial to concubuit. ex Creta insula is an "
        "adverbial phrase with adduxit, and Mycenis an ablative of place with "
        "adduxit."
    ),
    "verbalunits": [
        {"id": "t4", "syntactic_type": "dependent"},
        {"id": "t10", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Taurum", "tokentype": "lexical", "lemma": "taurus",
         "relations": [{"related": "t10", "relationship": "direct object"}]},
        {"id": "t1", "token": "cum", "tokentype": "lexical", "lemma": "cum",
         "relations": [{"related": "t4", "relationship": "adverbial"}]},
        {"id": "t2", "token": "quo", "tokentype": "lexical", "lemma": "qui",
         "relations": [{"related": "t0", "relationship": "relative pronoun"}, {"related": "t1", "relationship": "object of preposition"}]},
        {"id": "t3", "token": "Pasiphae", "tokentype": "lexical", "lemma": "Pasiphae",
         "relations": [{"related": "t4", "relationship": "subject"}]},
        {"id": "t4", "token": "concubuit", "tokentype": "lexical", "lemma": "concumbo", "verbalunitid": "t4",
         "relations": [{"related": "t2", "relationship": "unit verb"}]},
        {"id": "t5", "token": "ex", "tokentype": "lexical", "lemma": "ex",
         "relations": [{"related": "t10", "relationship": "adverbial"}]},
        {"id": "t6", "token": "Creta", "tokentype": "lexical", "lemma": "Creta",
         "relations": [{"related": "t7", "relationship": "adjectival"}]},
        {"id": "t7", "token": "insula", "tokentype": "lexical", "lemma": "insula",
         "relations": [{"related": "t5", "relationship": "object of preposition"}]},
        {"id": "t8", "token": "Mycenis", "tokentype": "lexical", "lemma": "Mycenae",
         "relations": [{"related": "t10", "relationship": "ablative"}]},
        {"id": "t9", "token": "uiuum", "tokentype": "lexical", "lemma": "vivus",
         "relations": [{"related": "t0", "relationship": "adjectival"}]},
        {"id": "t10", "token": "adduxit", "tokentype": "lexical", "lemma": "adduco", "verbalunitid": "t10",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
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
        "own -> sciret (relationship1 'indirect statement', "
        "matching its own syntactic type) identifying sciret -- not doluit "
        "-- as the verb governing this indirect statement, since it's "
        "sciret's object, nested one level deeper than sciret's own "
        "cum-clause."
    ),
    "verbalunits": [
        {"id": "t1", "syntactic_type": "dependent"},
        {"id": "t3", "syntactic_type": "indirect statement"},
        {"id": "t5", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Cum", "tokentype": "lexical", "lemma": "cum",
         "relations": [{"related": "t5", "relationship": "subordinating word"}]},
        {"id": "t1", "token": "sciret", "tokentype": "lexical", "lemma": "scio", "verbalunitid": "t1",
         "relations": [{"related": "t0", "relationship": "unit verb"}]},
        {"id": "t2", "token": "se", "tokentype": "lexical", "lemma": "se",
         "relations": [{"related": "t3", "relationship": "subject"}]},
        {"id": "t3", "token": "peccavisse", "tokentype": "lexical", "lemma": "pecco", "verbalunitid": "t3",
         "relations": [{"related": "t1", "relationship": "indirect statement"}]},
        {"id": "t4", "token": ",", "tokentype": "punctuation"},
        {"id": "t5", "token": "doluit", "tokentype": "lexical", "lemma": "doleo", "verbalunitid": "t5",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t6", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Ille moriens, cum sciret sagittas hydrae Lernaeae felle tinctas, sanguinem
#  suum exceptum Deianirae dedit et id philtrum esse dixit."
#   t0 Ille  t1 moriens  t2 ,  t3 cum  t4 sciret  t5 sagittas  t6 hydrae
#   t7 Lernaeae  t8 felle  t9 tinctas  t10 ,  t11 sanguinem  t12 suum
#   t13 exceptum  t14 Deianirae  t15 dedit  t16 et  t17 id  t18 philtrum
#   t19 esse  t20 dixit  t21 .
#
# dedit and dixit are coordinated independent verbs; dixit also governs an
# indirect statement. All three participles -- moriens, tinctas and
# exceptum -- are circumstantial participles
# (quarto/concepts/verbalunits.qmd, which uses this very sentence);
# exceptum was adjectival in the earlier fixture.
# ---------------------------------------------------------------------------

_COORDINATING_CONJUNCTION_DEDIT_ET_DIXIT_ANSWER = {
    "reasoning": (
        "dedit and dixit are independent verbs joined by et, which relates to "
        "both. Ille is the subject of dedit; sanguinem is its direct object "
        "(suum adjectival to it) and Deianirae a dative. moriens, tinctas and "
        "exceptum are all circumstantial participles, preferring the "
        "circumstantial reading as the scheme directs: moriens relates to "
        "Ille, tinctas to sagittas, exceptum to sanguinem. sciret is the verb "
        "of a dependent cum-clause, with sagittas as its direct object; felle "
        "is an ablative with tinctas, with hydrae Lernaeae depending on it. "
        "dixit governs the indirect statement esse, with id as subject and "
        "philtrum as predicate."
    ),
    "verbalunits": [
        {"id": "t1", "syntactic_type": "circumstantial participle"},
        {"id": "t4", "syntactic_type": "dependent"},
        {"id": "t9", "syntactic_type": "circumstantial participle"},
        {"id": "t13", "syntactic_type": "circumstantial participle"},
        {"id": "t15", "syntactic_type": "independent"},
        {"id": "t19", "syntactic_type": "indirect statement"},
        {"id": "t20", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Ille", "tokentype": "lexical", "lemma": "ille",
         "relations": [{"related": "t15", "relationship": "subject"}]},
        {"id": "t1", "token": "moriens", "tokentype": "lexical", "lemma": "morior", "verbalunitid": "t1",
         "relations": [{"related": "t0", "relationship": "circumstantial participle"}]},
        {"id": "t2", "token": ",", "tokentype": "punctuation"},
        {"id": "t3", "token": "cum", "tokentype": "lexical", "lemma": "cum",
         "relations": [{"related": "t15", "relationship": "subordinating word"}]},
        {"id": "t4", "token": "sciret", "tokentype": "lexical", "lemma": "scio", "verbalunitid": "t4",
         "relations": [{"related": "t3", "relationship": "unit verb"}]},
        {"id": "t5", "token": "sagittas", "tokentype": "lexical", "lemma": "sagitta",
         "relations": [{"related": "t4", "relationship": "direct object"}]},
        {"id": "t6", "token": "hydrae", "tokentype": "lexical", "lemma": "hydra",
         "relations": [{"related": "t8", "relationship": "genitive"}]},
        {"id": "t7", "token": "Lernaeae", "tokentype": "lexical", "lemma": "Lernaeus",
         "relations": [{"related": "t6", "relationship": "adjectival"}]},
        {"id": "t8", "token": "felle", "tokentype": "lexical", "lemma": "fel",
         "relations": [{"related": "t9", "relationship": "ablative"}]},
        {"id": "t9", "token": "tinctas", "tokentype": "lexical", "lemma": "tingo", "verbalunitid": "t9",
         "relations": [{"related": "t5", "relationship": "circumstantial participle"}]},
        {"id": "t10", "token": ",", "tokentype": "punctuation"},
        {"id": "t11", "token": "sanguinem", "tokentype": "lexical", "lemma": "sanguis",
         "relations": [{"related": "t15", "relationship": "direct object"}]},
        {"id": "t12", "token": "suum", "tokentype": "lexical", "lemma": "suus",
         "relations": [{"related": "t11", "relationship": "adjectival"}]},
        {"id": "t13", "token": "exceptum", "tokentype": "lexical", "lemma": "excipio", "verbalunitid": "t13",
         "relations": [{"related": "t11", "relationship": "circumstantial participle"}]},
        {"id": "t14", "token": "Deianirae", "tokentype": "lexical", "lemma": "Deianira",
         "relations": [{"related": "t15", "relationship": "dative"}]},
        {"id": "t15", "token": "dedit", "tokentype": "lexical", "lemma": "do", "verbalunitid": "t15",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t16", "token": "et", "tokentype": "lexical", "lemma": "et",
         "relations": [{"related": "t15", "relationship": "coordinating word"}, {"related": "t20", "relationship": "coordinating word"}]},
        {"id": "t17", "token": "id", "tokentype": "lexical", "lemma": "is",
         "relations": [{"related": "t19", "relationship": "subject"}]},
        {"id": "t18", "token": "philtrum", "tokentype": "lexical", "lemma": "philtrum",
         "relations": [{"related": "t19", "relationship": "predicate"}]},
        {"id": "t19", "token": "esse", "tokentype": "lexical", "lemma": "sum", "verbalunitid": "t19",
         "relations": [{"related": "t20", "relationship": "indirect statement"}]},
        {"id": "t20", "token": "dixit", "tokentype": "lexical", "lemma": "dico", "verbalunitid": "t20",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t21", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Tarquinius et assiduitate et varietate et magnificentia omnes antecessit."
#   t0 Tarquinius  t1 et  t2 assiduitate  t3 et  t4 varietate  t5 et
#   t6 magnificentia  t7 omnes  t8 antecessit  t9 .
#
# the scheme docs' own worked example for a SERIES of repeated coordinating
# conjunctions (polysyndeton, "et...et...et"), adapted from its "...omnes
# antecessit" example: three ablatives of respect, each introduced by its
# own "et", rather than a single conjunction joining just two conjuncts.
# This is the "et A et B et C" shape (an INTRODUCTORY connector before the
# very first item too, not just between items) -- see
# coordinating_conjunction_verbs_ille_hermionenque and
# enclitic_arma_virumque_cano above for the ordinary pairwise case. The
# first et (introductory, before assiduitate) has no preceding item to pair
# with, so it takes ONLY -> assiduitate (the first item),
# relationship1 'coordinating word', with relatedtoken2 left unset;
# the second et takes -> assiduitate (the preceding item),
# -> varietate (the following item); the third et takes
# -> varietate, -> magnificentia -- the ordinary
# preceding-item/following-item shape, same as a two-item pairwise
# conjunction, for every connector after the introductory one. relatedtoken2
# never points at another connector under this scheme. Each ablative also
# keeps its own ordinary "ablative" relation straight to antecessit,
# independent of the conjunction chain.
# ---------------------------------------------------------------------------

_COORDINATING_CONJUNCTION_SERIES_ANSWER = {
    "reasoning": (
        "antecessit is the independent main verb ('surpassed', transitive "
        "active), with Tarquinius as its subject and omnes as its direct "
        "object. assiduitate, varietate, and magnificentia are three "
        "ablatives of respect, each depending directly on antecessit "
        "('surpassed all in assiduity, variety, and magnificence'), "
        "introduced by a repeated series connector (polysyndeton) in the "
        "'et A et B et C' shape: the first et is introductory (before the "
        "first item, assiduitate), so it takes only -> "
        "assiduitate, with no relatedtoken2; the second et takes "
        "-> assiduitate (preceding item), -> "
        "varietate (following item); the third et takes -> "
        "varietate, -> magnificentia -- the ordinary "
        "preceding-item/following-item pairwise shape, relationship1 and "
        "relationship2 both 'coordinating word' throughout."
    ),
    "verbalunits": [
        {"id": "t8", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Tarquinius", "tokentype": "lexical", "lemma": "Tarquinius",
         "relations": [{"related": "t8", "relationship": "subject"}]},
        {"id": "t1", "token": "et", "tokentype": "lexical", "lemma": "et",
         "relations": [{"related": "t2", "relationship": "coordinating word"}]},
        {"id": "t2", "token": "assiduitate", "tokentype": "lexical", "lemma": "assiduitas",
         "relations": [{"related": "t8", "relationship": "ablative"}]},
        {"id": "t3", "token": "et", "tokentype": "lexical", "lemma": "et",
         "relations": [{"related": "t2", "relationship": "coordinating word"}, {"related": "t4", "relationship": "coordinating word"}]},
        {"id": "t4", "token": "varietate", "tokentype": "lexical", "lemma": "varietas",
         "relations": [{"related": "t8", "relationship": "ablative"}]},
        {"id": "t5", "token": "et", "tokentype": "lexical", "lemma": "et",
         "relations": [{"related": "t4", "relationship": "coordinating word"}, {"related": "t6", "relationship": "coordinating word"}]},
        {"id": "t6", "token": "magnificentia", "tokentype": "lexical", "lemma": "magnificentia",
         "relations": [{"related": "t8", "relationship": "ablative"}]},
        {"id": "t7", "token": "omnes", "tokentype": "lexical", "lemma": "omnis",
         "relations": [{"related": "t8", "relationship": "direct object"}]},
        {"id": "t8", "token": "antecessit", "tokentype": "lexical", "lemma": "antecedo", "verbalunitid": "t8",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t9", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Theseus audit quanta calamitate ciuitas afficeretur."
#   t0 Theseus  t1 audit  t2 quanta  t3 calamitate  t4 ciuitas
#   t5 afficeretur  t6 .
#
# the scheme docs' own worked example for indirect questions, added when
# the doc was revised to say indirect questions are treated as a kind of
# dependent clause: the interrogative word (here "quanta") introduces the
# dependent clause exactly the way a subordinating conjunction does, and is
# in fact given that very relationship label ("subordinating word")
# rather than a dedicated one of its own -- reusing it needs no new
# RelationLabel value and no change to assign_verbal_units()'s or
# compute_subordination_depths()'s chase logic, since both are already
# label-agnostic and only follow relations ids. quanta
# also agrees adjectivally with calamitate ("how great [a] calamity"), so
# it carries that as a secondary relation (relatedtoken2/relationship2),
# the same overflow pattern relative_pronoun_latini_cum_quibus uses for a
# relative pronoun with a second grammatical role of its own.
# ---------------------------------------------------------------------------

_INDIRECT_QUESTION_THESEUS_AUDIT_ANSWER = {
    "reasoning": (
        "audit is the independent main verb (transitive active, 'hears'), "
        "with the sentinel relatedtoken1 'root'; Theseus is its subject. "
        "The rest of the sentence is an indirect question -- 'how great a "
        "calamity the state was afflicted with' -- treated as a dependent "
        "clause: quanta, the interrogative adjective introducing it, has "
        "-> audit (relationship1 'subordinating word', "
        "the same reuse a plain subordinating conjunction like 'cum' would "
        "get), and also -> calamitate (relationship2 "
        "'adjectival'), since quanta agrees with and modifies calamitate "
        "within its own clause. afficeretur, the dependent verb this "
        "interrogative introduces, has -> quanta "
        "(relationship1 'unit verb'), exactly like any other dependent "
        "verb pointing back at its subordinating word. calamitate is "
        "ablative depending on afficeretur; ciuitas is afficeretur's "
        "subject."
    ),
    "verbalunits": [
        {"id": "t1", "syntactic_type": "independent"},
        {"id": "t5", "syntactic_type": "dependent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Theseus", "tokentype": "lexical", "lemma": "Theseus",
         "relations": [{"related": "t1", "relationship": "subject"}]},
        {"id": "t1", "token": "audit", "tokentype": "lexical", "lemma": "audio", "verbalunitid": "t1",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t2", "token": "quanta", "tokentype": "lexical", "lemma": "quantus",
         "relations": [{"related": "t1", "relationship": "subordinating word"}, {"related": "t3", "relationship": "adjectival"}]},
        {"id": "t3", "token": "calamitate", "tokentype": "lexical", "lemma": "calamitas",
         "relations": [{"related": "t5", "relationship": "ablative"}]},
        {"id": "t4", "token": "ciuitas", "tokentype": "lexical", "lemma": "civitas",
         "relations": [{"related": "t5", "relationship": "subject"}]},
        {"id": "t5", "token": "afficeretur", "tokentype": "lexical", "lemma": "afficio", "verbalunitid": "t5",
         "relations": [{"related": "t2", "relationship": "unit verb"}]},
        {"id": "t6", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Neptunus et Aegeus Pandionis filius in fano Mineruae cum Aethra Pitthei
#  filia una nocte concubuerunt."
#   t0 Neptunus  t1 et  t2 Aegeus  t3 Pandionis  t4 filius  t5 in  t6 fano
#   t7 Mineruae  t8 cum  t9 Aethra  t10 Pitthei  t11 filia  t12 una
#   t13 nocte  t14 concubuerunt  t15 .
#
# the scheme docs' own worked example for the new "apposition" relation:
# filius is in apposition to Aegeus, and filia is in apposition to Aethra,
# each taking the id of the noun it's apposed to for relatedtoken1 and
# 'apposition' for relationship1 -- while the genitives Pandionis and
# Pitthei depend not on Aegeus/Aethra but on the appositives themselves
# (filius/filia), unaffected by the apposition relation. Also exercises a
# coordinating conjunction joining a pair of (compound) subjects, and two
# prepositional phrases in an adverbial relation to the verb.
# ---------------------------------------------------------------------------

_APPOSITION_NEPTUNUS_AEGEUS_ANSWER = {
    "reasoning": (
        "concubuerunt is the independent main verb (intransitive, 'lay "
        "together'), with the sentinel relatedtoken1 'root'. Neptunus and "
        "Aegeus are its compound subject, coordinated by et (relatedtoken1 "
        "-> Neptunus, -> Aegeus, both relationship "
        "'coordinating word'); filius is in apposition to Aegeus "
        "('Aegeus, son of Pandion'), -> Aegeus, relationship1 "
        "'apposition', and Pandionis is a genitive depending on filius (not "
        "on Aegeus). 'in fano Mineruae' is a prepositional phrase modifying "
        "the verb (adverbial): in -> concubuerunt, fano -> in (object of "
        "preposition), Mineruae genitive depending on fano. 'cum Aethra "
        "Pitthei filia' is likewise adverbial: cum -> concubuerunt, Aethra "
        "-> cum (object of preposition); filia is in apposition to Aethra "
        "('Aethra, daughter of Pittheus'), -> Aethra, "
        "relationship1 'apposition', and Pitthei is a genitive depending on "
        "filia (not on Aethra). una is adjectival, modifying nocte, which "
        "is ablative (time when), depending on concubuerunt."
    ),
    "verbalunits": [
        {"id": "t14", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Neptunus", "tokentype": "lexical", "lemma": "Neptunus",
         "relations": [{"related": "t14", "relationship": "subject"}]},
        {"id": "t1", "token": "et", "tokentype": "lexical", "lemma": "et",
         "relations": [{"related": "t0", "relationship": "coordinating word"}, {"related": "t2", "relationship": "coordinating word"}]},
        {"id": "t2", "token": "Aegeus", "tokentype": "lexical", "lemma": "Aegeus",
         "relations": [{"related": "t14", "relationship": "subject"}]},
        {"id": "t3", "token": "Pandionis", "tokentype": "lexical", "lemma": "Pandion",
         "relations": [{"related": "t4", "relationship": "genitive"}]},
        {"id": "t4", "token": "filius", "tokentype": "lexical", "lemma": "filius",
         "relations": [{"related": "t2", "relationship": "apposition"}]},
        {"id": "t5", "token": "in", "tokentype": "lexical", "lemma": "in",
         "relations": [{"related": "t14", "relationship": "adverbial"}]},
        {"id": "t6", "token": "fano", "tokentype": "lexical", "lemma": "fanum",
         "relations": [{"related": "t5", "relationship": "object of preposition"}]},
        {"id": "t7", "token": "Mineruae", "tokentype": "lexical", "lemma": "Minerva",
         "relations": [{"related": "t6", "relationship": "genitive"}]},
        {"id": "t8", "token": "cum", "tokentype": "lexical", "lemma": "cum",
         "relations": [{"related": "t14", "relationship": "adverbial"}]},
        {"id": "t9", "token": "Aethra", "tokentype": "lexical", "lemma": "Aethra",
         "relations": [{"related": "t8", "relationship": "object of preposition"}]},
        {"id": "t10", "token": "Pitthei", "tokentype": "lexical", "lemma": "Pittheus",
         "relations": [{"related": "t11", "relationship": "genitive"}]},
        {"id": "t11", "token": "filia", "tokentype": "lexical", "lemma": "filia",
         "relations": [{"related": "t9", "relationship": "apposition"}]},
        {"id": "t12", "token": "una", "tokentype": "lexical", "lemma": "unus",
         "relations": [{"related": "t13", "relationship": "adjectival"}]},
        {"id": "t13", "token": "nocte", "tokentype": "lexical", "lemma": "nox",
         "relations": [{"related": "t14", "relationship": "ablative"}]},
        {"id": "t14", "token": "concubuerunt", "tokentype": "lexical", "lemma": "concumbo", "verbalunitid": "t14",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t15", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Amphion autem cum templum Apollinis expugnare vellet, ab Apolline
#  sagittis est interfectus."
#   t0 Amphion  t1 autem  t2 cum  t3 templum  t4 Apollinis  t5 expugnare
#   t6 vellet  t7 ,  t8 ab  t9 Apolline  t10 sagittis  t11 est
#   t12 interfectus  t13 .
#
# expugnare is a complementary infinitive with vellet. autem, a connective
# linking the sentence to what precedes, is a 'coordinating word' ->
# interfectus.
# ---------------------------------------------------------------------------

_COMPLEMENTARY_INFINITIVE_AMPHION_ANSWER = {
    "reasoning": (
        "est interfectus is a compound perfect passive anchored on "
        "interfectus, the independent main verb, with est as its auxiliary "
        "and Amphion as its subject; ab Apolline gives the agent (ab -> "
        "interfectus as 'agent-ablative'), and sagittis is an ablative. autem "
        "connects the sentence to the preceding one. vellet is the verb of a "
        "dependent cum-clause; expugnare is a complementary infinitive with "
        "vellet, with templum as its direct object and Apollinis a genitive."
    ),
    "verbalunits": [
        {"id": "t6", "syntactic_type": "dependent"},
        {"id": "t12", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Amphion", "tokentype": "lexical", "lemma": "Amphion",
         "relations": [{"related": "t12", "relationship": "subject"}]},
        {"id": "t1", "token": "autem", "tokentype": "lexical", "lemma": "autem",
         "relations": [{"related": "t12", "relationship": "coordinating word"}]},
        {"id": "t2", "token": "cum", "tokentype": "lexical", "lemma": "cum",
         "relations": [{"related": "t12", "relationship": "subordinating word"}]},
        {"id": "t3", "token": "templum", "tokentype": "lexical", "lemma": "templum",
         "relations": [{"related": "t5", "relationship": "direct object"}]},
        {"id": "t4", "token": "Apollinis", "tokentype": "lexical", "lemma": "Apollo",
         "relations": [{"related": "t3", "relationship": "genitive"}]},
        {"id": "t5", "token": "expugnare", "tokentype": "lexical", "lemma": "expugno",
         "relations": [{"related": "t6", "relationship": "complementary infinitive"}]},
        {"id": "t6", "token": "vellet", "tokentype": "lexical", "lemma": "volo", "verbalunitid": "t6",
         "relations": [{"related": "t2", "relationship": "unit verb"}]},
        {"id": "t7", "token": ",", "tokentype": "punctuation"},
        {"id": "t8", "token": "ab", "tokentype": "lexical", "lemma": "ab",
         "relations": [{"related": "t12", "relationship": "agent-ablative"}]},
        {"id": "t9", "token": "Apolline", "tokentype": "lexical", "lemma": "Apollo",
         "relations": [{"related": "t8", "relationship": "object of preposition"}]},
        {"id": "t10", "token": "sagittis", "tokentype": "lexical", "lemma": "sagitta",
         "relations": [{"related": "t12", "relationship": "ablative"}]},
        {"id": "t11", "token": "est", "tokentype": "lexical", "lemma": "sum",
         "relations": [{"related": "t12", "relationship": "auxiliary"}]},
        {"id": "t12", "token": "interfectus", "tokentype": "lexical", "lemma": "interficio", "verbalunitid": "t12",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t13", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Dolere malum est."
#   t0 Dolere  t1 malum  t2 est  t3 .
#
# the scheme docs' own worked example for an infinitive used as an
# ordinary noun (here, the subject of a linking verb) rather than anchoring
# an indirect statement or completing another verb: dolere takes the plain
# 'subject' relation, exactly as any noun subject would, and is NOT itself
# a verbal expression -- only est is.
# ---------------------------------------------------------------------------

_INFINITIVE_AS_SUBJECT_DOLERE_MALUM_ANSWER = {
    "reasoning": (
        "est is a linking verb (copula), with the sentinel relatedtoken1 "
        "'root'. dolere, an infinitive used as an ordinary noun (not part "
        "of an indirect statement), is its subject -- -> "
        "est, relationship1 'subject', the same relation any noun subject "
        "would get, and dolere gets no `verbalunits` entry of its own. "
        "malum is the predicate adjective agreeing with est's subject."
    ),
    "verbalunits": [
        {"id": "t2", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Dolere", "tokentype": "lexical", "lemma": "doleo",
         "relations": [{"related": "t2", "relationship": "subject"}]},
        {"id": "t1", "token": "malum", "tokentype": "lexical", "lemma": "malus",
         "relations": [{"related": "t2", "relationship": "predicate"}]},
        {"id": "t2", "token": "est", "tokentype": "lexical", "lemma": "sum", "verbalunitid": "t2",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t3", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Metapontus exiit ad Dianam Metapontinam ad sacrum faciendum."
#   t0 Metapontus  t1 exiit  t2 ad  t3 Dianam  t4 Metapontinam  t5 ad
#   t6 sacrum  t7 faciendum  t8 .
#
# Every gerundive is a verbal expression (quarto/concepts/verbalunits.qmd):
# attributive faciendum anchors a 'gerundive' verbal expression and relates
# to sacrum as 'gerundive'. (The earlier scheme treated it as a plain
# adjective.)
# ---------------------------------------------------------------------------

_GERUNDIVE_METAPONTUS_SACRUM_FACIENDUM_ANSWER = {
    "reasoning": (
        "exiit is the independent main verb, with Metapontus as its subject. "
        "ad Dianam Metapontinam and ad sacrum faciendum are adverbial phrases "
        "with exiit. faciendum is a gerundive in attributive position with "
        "sacrum, so it anchors its own 'gerundive' verbal expression and "
        "relates to sacrum as 'gerundive'."
    ),
    "verbalunits": [
        {"id": "t1", "syntactic_type": "independent"},
        {"id": "t7", "syntactic_type": "gerundive"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Metapontus", "tokentype": "lexical", "lemma": "Metapontus",
         "relations": [{"related": "t1", "relationship": "subject"}]},
        {"id": "t1", "token": "exiit", "tokentype": "lexical", "lemma": "exeo", "verbalunitid": "t1",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t2", "token": "ad", "tokentype": "lexical", "lemma": "ad",
         "relations": [{"related": "t1", "relationship": "adverbial"}]},
        {"id": "t3", "token": "Dianam", "tokentype": "lexical", "lemma": "Diana",
         "relations": [{"related": "t2", "relationship": "object of preposition"}]},
        {"id": "t4", "token": "Metapontinam", "tokentype": "lexical", "lemma": "Metapontinus",
         "relations": [{"related": "t3", "relationship": "adjectival"}]},
        {"id": "t5", "token": "ad", "tokentype": "lexical", "lemma": "ad",
         "relations": [{"related": "t1", "relationship": "adverbial"}]},
        {"id": "t6", "token": "sacrum", "tokentype": "lexical", "lemma": "sacrum",
         "relations": [{"related": "t5", "relationship": "object of preposition"}]},
        {"id": "t7", "token": "faciendum", "tokentype": "lexical", "lemma": "facio", "verbalunitid": "t7",
         "relations": [{"related": "t6", "relationship": "gerundive"}]},
        {"id": "t8", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Ars bene disserendi magna est."
#   t0 Ars  t1 bene  t2 disserendi  t3 magna  t4 est  t5 .
#
# the scheme docs' own worked example for a gerund embedded in a full
# sentence (the doc's own example, "ars bene disserendi", is a bare phrase
# with no verb at all, so this fixture supplies "magna est" to make it a
# complete, analyzable sentence): disserendi is a genitive noun depending
# on ars, exactly like any other noun in the genitive -- no new relation
# label. bene, an adverb, modifies disserendi the same way it would modify
# a finite verb or infinitive, demonstrating that a gerund can still take
# its own adverb.
# ---------------------------------------------------------------------------

_GERUND_ARS_BENE_DISSERENDI_ANSWER = {
    "reasoning": (
        "est is a linking verb (copula), with the sentinel relatedtoken1 "
        "'root', joining its subject Ars to the predicate adjective magna. "
        "disserendi, a gerund, is a genitive noun depending on Ars "
        "(-> Ars, relationship1 'genitive') -- the same "
        "relation any other genitive noun would get. bene, the adverb "
        "modifying disserendi, has -> disserendi, "
        "relationship1 'adverbial', showing the gerund can take its own "
        "adverb like a finite verb or infinitive would."
    ),
    "verbalunits": [
        {"id": "t4", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Ars", "tokentype": "lexical", "lemma": "ars",
         "relations": [{"related": "t4", "relationship": "subject"}]},
        {"id": "t1", "token": "bene", "tokentype": "lexical", "lemma": "bene",
         "relations": [{"related": "t2", "relationship": "adverbial"}]},
        {"id": "t2", "token": "disserendi", "tokentype": "lexical", "lemma": "dissero",
         "relations": [{"related": "t0", "relationship": "genitive"}]},
        {"id": "t3", "token": "magna", "tokentype": "lexical", "lemma": "magnus",
         "relations": [{"related": "t4", "relationship": "predicate"}]},
        {"id": "t4", "token": "est", "tokentype": "lexical", "lemma": "sum", "verbalunitid": "t4",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t5", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Omnia praeclara rara."
#   t0 Omnia  t1 praeclara  t2 rara  t2_implied [implied sum]  t3 .
#
# An implied form of sum in a bare predicate construction: the implied
# token (t2_implied, lemma sum) anchors an independent verbal expression.
# Following the table in quarto/concepts/syntactic-analysis.qmd, praeclara
# ('splendid things') is the subject and omnia is adjectival to it.
# ---------------------------------------------------------------------------

_IMPLIED_SUM_OMNIA_PRAECLARA_ANSWER = {
    "reasoning": (
        "There is no verb: an implied form of sum (t2_implied) is the "
        "independent main verb, relating to root. praeclara ('splendid "
        "things') is its subject, with omnia adjectival to it, and rara is "
        "its predicate."
    ),
    "verbalunits": [
        {"id": "t2_implied", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Omnia", "tokentype": "lexical", "lemma": "omnis",
         "relations": [{"related": "t1", "relationship": "adjectival"}]},
        {"id": "t1", "token": "praeclara", "tokentype": "lexical", "lemma": "praeclarus",
         "relations": [{"related": "t2_implied", "relationship": "subject"}]},
        {"id": "t2", "token": "rara", "tokentype": "lexical", "lemma": "rarus",
         "relations": [{"related": "t2_implied", "relationship": "predicate"}]},
        {"id": "t2_implied", "token": None, "tokentype": "implied sum", "lemma": "sum", "verbalunitid": "t2_implied",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t3", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "inde P. Valerius iterum T. Lucretius consules facti."
#   t0 inde  t1 P.  t2 Valerius  t3 iterum  t4 T.  t5 Lucretius  t6 consules
#   t7 facti  t7_implied [implied sum]  t8 .
#
# An omitted auxiliary of a perfect passive: facti anchors the verbal
# expression, and the implied sum (t7_implied) relates to it as
# 'auxiliary'. consules is a predicate with the passive of a verb of making
# (use 4 in quarto/concepts/syntactic-analysis.qmd).
# ---------------------------------------------------------------------------

_IMPLIED_SUM_CONSULES_FACTI_ANSWER = {
    "reasoning": (
        "facti (sunt) is a perfect passive with its auxiliary omitted: facti "
        "anchors the independent verbal expression, and an implied sum "
        "(t7_implied) relates to it as auxiliary. Valerius and Lucretius are "
        "its subjects (each with its praenomen), consules its predicate, and "
        "inde and iterum adverbial."
    ),
    "verbalunits": [
        {"id": "t7", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "inde", "tokentype": "lexical", "lemma": "inde",
         "relations": [{"related": "t7", "relationship": "adverbial"}]},
        {"id": "t1", "token": "P.", "tokentype": "praenomen",
         "relations": [{"related": "t2", "relationship": "praenomen"}]},
        {"id": "t2", "token": "Valerius", "tokentype": "lexical", "lemma": "Valerius",
         "relations": [{"related": "t7", "relationship": "subject"}]},
        {"id": "t3", "token": "iterum", "tokentype": "lexical", "lemma": "iterum",
         "relations": [{"related": "t7", "relationship": "adverbial"}]},
        {"id": "t4", "token": "T.", "tokentype": "praenomen",
         "relations": [{"related": "t5", "relationship": "praenomen"}]},
        {"id": "t5", "token": "Lucretius", "tokentype": "lexical", "lemma": "Lucretius",
         "relations": [{"related": "t7", "relationship": "subject"}]},
        {"id": "t6", "token": "consules", "tokentype": "lexical", "lemma": "consul",
         "relations": [{"related": "t7", "relationship": "predicate"}]},
        {"id": "t7", "token": "facti", "tokentype": "lexical", "lemma": "facio", "verbalunitid": "t7",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t7_implied", "token": None, "tokentype": "implied sum", "lemma": "sum",
         "relations": [{"related": "t7", "relationship": "auxiliary"}]},
        {"id": "t8", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "P. Valerius anno post Agrippa Menenio P. Postumio consulibus moritur."
#   t0 P.  t1 Valerius  t2 anno  t3 post  t4 Agrippa  t5 Menenio  t6 P.
#   t7 Postumio  t8 consulibus  t8_implied [implied sum]  t9 moritur  t10 .
#
# There is no present participle of sum, so the ablative absolute 'Agrippa
# Menenio P. Postumio consulibus' implies one: t8_implied (lemma sum)
# anchors a 'circumstantial participle' verbal expression and relates to
# each of the two consuls' names (Menenio, Postumio) as 'circumstantial
# participle'; both names relate to moritur as 'ablative absolute', and
# consulibus is the predicate of the implied participle. Agrippa is a
# praenomen (unabbreviated) with Menenio (quarto/concepts/tokens.qmd). The
# page does not give a graph for this example; this structure is a judgment
# call (see notes/model_switch_questions.md).
# ---------------------------------------------------------------------------

_IMPLIED_PARTICIPLE_OF_SUM_CONSULIBUS_ANSWER = {
    "reasoning": (
        "moritur is the independent main verb, with Valerius as its subject; "
        "anno is an ablative and post adverbial. 'Agrippa Menenio P. Postumio "
        "consulibus' is an ablative absolute with an implied participle of "
        "sum (t8_implied), a circumstantial participle relating to each of "
        "the consuls' names, Menenio and Postumio; both names stand in an "
        "ablative absolute relation to moritur, and consulibus is the "
        "predicate of the implied participle. Agrippa is the praenomen of "
        "Menenio, and P. of Postumio."
    ),
    "verbalunits": [
        {"id": "t9", "syntactic_type": "independent"},
        {"id": "t8_implied", "syntactic_type": "circumstantial participle"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "P.", "tokentype": "praenomen",
         "relations": [{"related": "t1", "relationship": "praenomen"}]},
        {"id": "t1", "token": "Valerius", "tokentype": "lexical", "lemma": "Valerius",
         "relations": [{"related": "t9", "relationship": "subject"}]},
        {"id": "t2", "token": "anno", "tokentype": "lexical", "lemma": "annus",
         "relations": [{"related": "t9", "relationship": "ablative"}]},
        {"id": "t3", "token": "post", "tokentype": "lexical", "lemma": "post",
         "relations": [{"related": "t9", "relationship": "adverbial"}]},
        {"id": "t4", "token": "Agrippa", "tokentype": "praenomen", "lemma": "Agrippa",
         "relations": [{"related": "t5", "relationship": "praenomen"}]},
        {"id": "t5", "token": "Menenio", "tokentype": "lexical", "lemma": "Menenius",
         "relations": [{"related": "t9", "relationship": "ablative absolute"}]},
        {"id": "t6", "token": "P.", "tokentype": "praenomen",
         "relations": [{"related": "t7", "relationship": "praenomen"}]},
        {"id": "t7", "token": "Postumio", "tokentype": "lexical", "lemma": "Postumius",
         "relations": [{"related": "t9", "relationship": "ablative absolute"}]},
        {"id": "t8", "token": "consulibus", "tokentype": "lexical", "lemma": "consul",
         "relations": [{"related": "t8_implied", "relationship": "predicate"}]},
        {"id": "t8_implied", "token": None, "tokentype": "implied sum", "lemma": "sum", "verbalunitid": "t8_implied",
         "relations": [{"related": "t5", "relationship": "circumstantial participle"}, {"related": "t7", "relationship": "circumstantial participle"}]},
        {"id": "t9", "token": "moritur", "tokentype": "lexical", "lemma": "morior", "verbalunitid": "t9",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t10", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Recordatus somniorum ait ad eos."
#   t0_implied [implied subject]  t0 Recordatus  t1 somniorum  t2 ait
#   t3 ad  t4 eos  t5 .
#
# An implied substantive: Recordatus agrees with the unexpressed subject of
# ait, so an implied substantive (t0_implied) is the subject of ait, and
# Recordatus (a 'circumstantial participle' verbal expression) relates to
# it.
# ---------------------------------------------------------------------------

_IMPLIED_SUBJECT_RECORDATUS_SOMNIORUM_ANSWER = {
    "reasoning": (
        "ait is the independent main verb. Its subject is unexpressed, but "
        "the circumstantial participle Recordatus needs a substantive to "
        "agree with, so an implied substantive (t0_implied) stands for the "
        "subject of ait. Recordatus relates to it as circumstantial "
        "participle, with somniorum as a genitive. ad eos is an adverbial "
        "phrase with ait."
    ),
    "verbalunits": [
        {"id": "t0", "syntactic_type": "circumstantial participle"},
        {"id": "t2", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0_implied", "token": None, "tokentype": "implied substantive",
         "relations": [{"related": "t2", "relationship": "subject"}]},
        {"id": "t0", "token": "Recordatus", "tokentype": "lexical", "lemma": "recordor", "verbalunitid": "t0",
         "relations": [{"related": "t0_implied", "relationship": "circumstantial participle"}]},
        {"id": "t1", "token": "somniorum", "tokentype": "lexical", "lemma": "somnium",
         "relations": [{"related": "t0", "relationship": "genitive"}]},
        {"id": "t2", "token": "ait", "tokentype": "lexical", "lemma": "aio", "verbalunitid": "t2",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t3", "token": "ad", "tokentype": "lexical", "lemma": "ad",
         "relations": [{"related": "t2", "relationship": "adverbial"}]},
        {"id": "t4", "token": "eos", "tokentype": "lexical", "lemma": "is",
         "relations": [{"related": "t3", "relationship": "object of preposition"}]},
        {"id": "t5", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "nimium Tarquinios regno adsuesse; initium a Prisco factum esse;
#  regnasse dein Ser. Tullium."
#   t0_implied [continued discourse]  t0 nimium  t1 Tarquinios  t2 regno  t3 adsuesse
#   t4 ;  t5 initium  t6 a  t7 Prisco  t8 factum  t9 esse  t10 ;
#   t11 regnasse  t12 dein  t13 Ser.  t14 Tullium  t15 .
#
# the scheme docs' own worked example for continuation of indirect
# discourse: three coordinate indirect-statement verbal expressions
# (adsuesse, factum [esse], regnasse) sharing ONE governing verb of
# speaking/thinking that is never written at all in this excerpt -- so a
# single new implied token (t0_implied) is added, and each verbal
# expression's 'indirect statement' relation points at it, exactly as if
# the governing verb had been repeated for each one. factum esse is a
# compound perfect-passive infinitive: per the compound-verb rule, the
# PARTICIPLE factum anchors and carries the 'indirect statement' relation
# to t0_implied, while esse (the accompanying infinitive of sum) relates
# to factum via 'auxiliary'. Named t0_implied per SentenceAnalysis's naming
# rule for a word that would precede every real token in the sentence, and
# placed first in tokengraph accordingly. (the scheme docs' own excerpt
# elides "esse" from "factum [esse]" too -- a SEPARATE elided-present-of-
# sum case, layered on top of the one this fixture is about -- so "esse" is
# spelled out here to keep this fixture focused on the shared-governing-
# verb construction alone; see implied_sum_consules_facti for that other
# elision on its own.)
# ---------------------------------------------------------------------------

_CONTINUATION_INDIRECT_DISCOURSE_ANSWER = {
    "reasoning": (
        "No verb of speaking or thinking appears anywhere in this excerpt, "
        "but all three clauses are grammatically indirect statements "
        "depending on one understood governing verb, per the scheme docs' "
        "continuation-of-indirect-discourse rule -- a new implied token "
        "(t0_implied, token=None) is added, independent and transitive "
        "active, and each infinitive's 'indirect statement' relation "
        "points at it. adsuesse (intransitive, 'became accustomed') has "
        "Tarquinios as its accusative subject and regno as a dative "
        "depending on it; factum, with esse as its auxiliary ('was made'), "
        "anchors a transitive passive verbal expression, with initium as "
        "subject and 'a Prisco' as the agent phrase; regnasse "
        "(intransitive, 'had reigned') has Tullium as its accusative "
        "subject and dein adverbial. Ser. relates to Tullium, the lexical "
        "name it abbreviates, via 'praenomen'."
    ),
    "verbalunits": [
        {"id": "t0_implied", "syntactic_type": "independent"},
        {"id": "t3", "syntactic_type": "indirect statement"},
        {"id": "t8", "syntactic_type": "indirect statement"},
        {"id": "t11", "syntactic_type": "indirect statement"},
    ],
    "tokengraph": [
        {"id": "t0_implied", "token": None, "tokentype": "implied verb", "verbalunitid": "t0_implied",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t0", "token": "nimium", "tokentype": "lexical", "lemma": "nimium",
         "relations": [{"related": "t3", "relationship": "adverbial"}]},
        {"id": "t1", "token": "Tarquinios", "tokentype": "lexical", "lemma": "Tarquinius",
         "relations": [{"related": "t3", "relationship": "subject"}]},
        {"id": "t2", "token": "regno", "tokentype": "lexical", "lemma": "regnum",
         "relations": [{"related": "t3", "relationship": "dative"}]},
        {"id": "t3", "token": "adsuesse", "tokentype": "lexical", "lemma": "adsuesco", "verbalunitid": "t3",
         "relations": [{"related": "t0_implied", "relationship": "indirect statement"}]},
        {"id": "t4", "token": ";", "tokentype": "punctuation"},
        {"id": "t5", "token": "initium", "tokentype": "lexical", "lemma": "initium",
         "relations": [{"related": "t8", "relationship": "subject"}]},
        {"id": "t6", "token": "a", "tokentype": "lexical", "lemma": "a",
         "relations": [{"related": "t8", "relationship": "agent-ablative"}]},
        {"id": "t7", "token": "Prisco", "tokentype": "lexical", "lemma": "Priscus",
         "relations": [{"related": "t6", "relationship": "object of preposition"}]},
        {"id": "t8", "token": "factum", "tokentype": "lexical", "lemma": "facio", "verbalunitid": "t8",
         "relations": [{"related": "t0_implied", "relationship": "indirect statement"}]},
        {"id": "t9", "token": "esse", "tokentype": "lexical", "lemma": "sum",
         "relations": [{"related": "t8", "relationship": "auxiliary"}]},
        {"id": "t10", "token": ";", "tokentype": "punctuation"},
        {"id": "t11", "token": "regnasse", "tokentype": "lexical", "lemma": "regno", "verbalunitid": "t11",
         "relations": [{"related": "t0_implied", "relationship": "indirect statement"}]},
        {"id": "t12", "token": "dein", "tokentype": "lexical", "lemma": "dein",
         "relations": [{"related": "t11", "relationship": "adverbial"}]},
        {"id": "t13", "token": "Ser.", "tokentype": "praenomen",
         "relations": [{"related": "t14", "relationship": "praenomen"}]},
        {"id": "t14", "token": "Tullium", "tokentype": "lexical", "lemma": "Tullius",
         "relations": [{"related": "t11", "relationship": "subject"}]},
        {"id": "t15", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Sex. Tarquinius inscio Collatino cum comite uno Collatiam venit."
#   t0 Sex.  t1 Tarquinius  t2 inscio  t3 Collatino  t4 cum  t5 comite
#   t6 uno  t7 Collatiam  t8 venit  t9 .
#
# Sex. -> Tarquinius ('praenomen'). inscio Collatino is an ablative
# absolute with an implied participle of sum (t3_implied): Collatino ->
# venit 'ablative absolute', the implied participle -> Collatino, and
# inscio is its predicate (treated like consulibus in
# implied_participle_of_sum_consulibus; the earlier fixture had inscio
# adjectival). Collatiam is an accusative of place to which.
# ---------------------------------------------------------------------------

_PRAENOMEN_SEX_TARQUINIUS_ANSWER = {
    "reasoning": (
        "venit is the independent main verb, with Tarquinius as its subject "
        "(Sex. his praenomen) and Collatiam as an accusative of place to "
        "which. inscio Collatino is an ablative absolute with an implied "
        "participle of sum (t3_implied), a circumstantial participle relating "
        "to Collatino; Collatino stands in an ablative absolute relation to "
        "venit, and inscio is the predicate of the implied participle "
        "('Collatinus being unaware'). cum comite uno is an adverbial phrase "
        "with venit."
    ),
    "verbalunits": [
        {"id": "t8", "syntactic_type": "independent"},
        {"id": "t3_implied", "syntactic_type": "circumstantial participle"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Sex.", "tokentype": "praenomen",
         "relations": [{"related": "t1", "relationship": "praenomen"}]},
        {"id": "t1", "token": "Tarquinius", "tokentype": "lexical", "lemma": "Tarquinius",
         "relations": [{"related": "t8", "relationship": "subject"}]},
        {"id": "t2", "token": "inscio", "tokentype": "lexical", "lemma": "inscius",
         "relations": [{"related": "t3_implied", "relationship": "predicate"}]},
        {"id": "t3", "token": "Collatino", "tokentype": "lexical", "lemma": "Collatinus",
         "relations": [{"related": "t8", "relationship": "ablative absolute"}]},
        {"id": "t3_implied", "token": None, "tokentype": "implied sum", "lemma": "sum", "verbalunitid": "t3_implied",
         "relations": [{"related": "t3", "relationship": "circumstantial participle"}]},
        {"id": "t4", "token": "cum", "tokentype": "lexical", "lemma": "cum",
         "relations": [{"related": "t8", "relationship": "adverbial"}]},
        {"id": "t5", "token": "comite", "tokentype": "lexical", "lemma": "comes",
         "relations": [{"related": "t4", "relationship": "object of preposition"}]},
        {"id": "t6", "token": "uno", "tokentype": "lexical", "lemma": "unus",
         "relations": [{"related": "t5", "relationship": "adjectival"}]},
        {"id": "t7", "token": "Collatiam", "tokentype": "lexical", "lemma": "Collatia",
         "relations": [{"related": "t8", "relationship": "accusative"}]},
        {"id": "t8", "token": "venit", "tokentype": "lexical", "lemma": "venio", "verbalunitid": "t8",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t9", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Romam venit."
#   t0 Romam  t1 venit  t2 .
#
# the scheme docs' own first worked example for the new 'accusative'
# relation label (Noun relations section): a bare accusative of place to
# which relates to the verb it modifies, even though that verb (venit) is
# intransitive and this accusative is NOT its direct object.
# ---------------------------------------------------------------------------

_ACCUSATIVE_ROMAM_VENIT_ANSWER = {
    "reasoning": (
        "venit is the independent main verb ('he/she/it came', "
        "intransitive -- subject left implicit, third person), with the "
        "sentinel relatedtoken1 'root'. Romam, a bare accusative of place "
        "to which ('to Rome'), relates to venit via 'accusative' -- not "
        "'direct object', since venit is intransitive."
    ),
    "verbalunits": [
        {"id": "t1", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Romam", "tokentype": "lexical", "lemma": "Roma",
         "relations": [{"related": "t1", "relationship": "accusative"}]},
        {"id": "t1", "token": "venit", "tokentype": "lexical", "lemma": "venio", "verbalunitid": "t1",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t2", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Duo milia passuum iter fecerunt."
#   t0 Duo  t1 milia  t2 passuum  t3 iter  t4 fecerunt  t5 .
#
# the scheme docs' own second worked example for 'accusative': an
# accusative-of-extent phrase can also qualify another NOUN rather than a
# verb -- "duo milia passuum" ('two thousand paces') qualifies iter, so
# milia relates to iter (not to fecerunt) via 'accusative'.
# ---------------------------------------------------------------------------

_ACCUSATIVE_MILIA_PASSUUM_ITER_ANSWER = {
    "reasoning": (
        "fecerunt is the independent main verb ('they made/marched', "
        "transitive active -- subject 'they' left implicit), with the "
        "sentinel relatedtoken1 'root'; iter ('a march/journey') is its "
        "direct object. 'duo milia passuum' ('two thousand paces') "
        "qualifies iter, not fecerunt: milia relates to iter via "
        "'accusative'; duo is adjectival to milia ('two'); passuum is "
        "genitive, depending on milia ('of paces')."
    ),
    "verbalunits": [
        {"id": "t4", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Duo", "tokentype": "lexical", "lemma": "duo",
         "relations": [{"related": "t1", "relationship": "adjectival"}]},
        {"id": "t1", "token": "milia", "tokentype": "lexical", "lemma": "mille",
         "relations": [{"related": "t3", "relationship": "accusative"}]},
        {"id": "t2", "token": "passuum", "tokentype": "lexical", "lemma": "passus",
         "relations": [{"related": "t1", "relationship": "genitive"}]},
        {"id": "t3", "token": "iter", "tokentype": "lexical", "lemma": "iter",
         "relations": [{"related": "t4", "relationship": "direct object"}]},
        {"id": "t4", "token": "fecerunt", "tokentype": "lexical", "lemma": "facio", "verbalunitid": "t4",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t5", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Collatinus negat verbis opus esse."
#   t0 Collatinus  t1 negat  t2 verbis  t3 opus  t4 esse  t5 .
#
# the scheme docs' own worked example for the idiomatic 'opus est' + "
# ablative construction (Noun relations section, 'ablative'): the ablative
# token relates to "opus" itself, not to the verb "esse"/"est".
# ---------------------------------------------------------------------------

_ABLATIVE_OPUS_EST_VERBIS_ANSWER = {
    "reasoning": (
        "negat is the independent main verb ('he denies', transitive "
        "active), with the sentinel relatedtoken1 'root'; Collatinus is "
        "its subject. 'verbis opus esse' ('that there was need of words') "
        "is an indirect statement governed by negat: esse (linking verb) "
        "has -> negat, relationship1 'indirect statement'. "
        "In the idiomatic 'opus est' construction, the ablative verbis "
        "relates to opus itself, not to esse: verbis has -> "
        "opus, relationship1 'ablative'; opus is the predicate, relating "
        "to esse."
    ),
    "verbalunits": [
        {"id": "t1", "syntactic_type": "independent"},
        {"id": "t4", "syntactic_type": "indirect statement"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Collatinus", "tokentype": "lexical", "lemma": "Collatinus",
         "relations": [{"related": "t1", "relationship": "subject"}]},
        {"id": "t1", "token": "negat", "tokentype": "lexical", "lemma": "nego", "verbalunitid": "t1",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t2", "token": "verbis", "tokentype": "lexical", "lemma": "verbum",
         "relations": [{"related": "t3", "relationship": "ablative"}]},
        {"id": "t3", "token": "opus", "tokentype": "lexical", "lemma": "opus",
         "relations": [{"related": "t4", "relationship": "predicate"}]},
        {"id": "t4", "token": "esse", "tokentype": "lexical", "lemma": "sum", "verbalunitid": "t4",
         "relations": [{"related": "t1", "relationship": "indirect statement"}]},
        {"id": "t5", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "vocative" -- the scheme docs' newest noun-relation label: a noun in the
# vocative case always relates to a VERB (unlike "genitive"/"dative"/
# "ablative"/"accusative", which can also relate to another noun), via
# -> the verb's id, relationship "vocative". the scheme docs'
# own worked example is "Non est ita, domine, sed servi tui venerunt ut
# emerent cibos." (domine -> est); this fixture keeps the same vocative
# noun ("domine") and target verb ("venit") but in a minimal two-content-
# word sentence, matching the minimal style of accusative_romam_venit
# above rather than reproducing that full multi-clause sentence.
# ---------------------------------------------------------------------------

_VOCATIVE_DOMINE_VENIT_ANSWER = {
    "reasoning": (
        "venit is the independent main verb ('he/she/it comes', "
        "intransitive -- subject left implicit, third person), with the "
        "sentinel relatedtoken1 'root'. Domine, a noun in the vocative "
        "directly addressing someone, relates to venit via 'vocative' -- "
        "the scheme docs' newest relation label, reserved for a noun in "
        "the vocative case (always linked to a verb, never to another "
        "noun)."
    ),
    "verbalunits": [
        {"id": "t2", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Domine", "tokentype": "lexical", "lemma": "dominus",
         "relations": [{"related": "t2", "relationship": "vocative"}]},
        {"id": "t1", "token": ",", "tokentype": "punctuation"},
        {"id": "t2", "token": "venit", "tokentype": "lexical", "lemma": "venio", "verbalunitid": "t2",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t3", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Precor eam videam."
#   t0 Precor  t1 eam  t2 videam  t3 .
#
# The worked example for 'parataxis' in quarto/concepts/verbalunits.qmd and
# syntactic-analysis.qmd: a subjunctive governed, without any subordinating
# word, by a verb of wishing/praying. videam is its own verbal expression
# (syntactic_type 'parataxis') and relates to Precor via 'parataxis'.
# ---------------------------------------------------------------------------

_PARATAXIS_PRECOR_ANSWER = {
    "reasoning": (
        "Precor (a deponent, 'I pray') is the independent main verb. videam "
        "is a subjunctive governed by precor with no subordinating word at "
        "all, so its verbal expression is 'parataxis' and it relates to "
        "Precor as 'parataxis'. eam is the direct object of videam."
    ),
    "verbalunits": [
        {"id": "t0", "syntactic_type": "independent"},
        {"id": "t2", "syntactic_type": "parataxis"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Precor", "tokentype": "lexical", "lemma": "precor", "verbalunitid": "t0",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t1", "token": "eam", "tokentype": "lexical", "lemma": "is",
         "relations": [{"related": "t2", "relationship": "direct object"}]},
        {"id": "t2", "token": "videam", "tokentype": "lexical", "lemma": "video", "verbalunitid": "t2",
         "relations": [{"related": "t0", "relationship": "parataxis"}]},
        {"id": "t3", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Caesari omnia uno tempore erant agenda."
#   t0 Caesari  t1 omnia  t2 uno  t3 tempore  t4 erant  t5 agenda  t6 .
#
# The worked example for 'agent-dative' in quarto/concepts/
# syntactic-analysis.qmd: a gerundive + sum (passive periphrastic) is a
# compound form anchored on the gerundive, and its agent is a dative.
# ---------------------------------------------------------------------------

_AGENT_DATIVE_CAESARI_AGENDA_ANSWER = {
    "reasoning": (
        "erant agenda is a passive periphrastic (gerundive + sum): the "
        "gerundive agenda anchors an independent verbal expression and erant "
        "is its auxiliary. omnia is the grammatical subject. Caesari is a "
        "dative of agent with the gerundive, related as 'agent-dative'. "
        "tempore is an ablative (of time) with agenda, modified by uno."
    ),
    "verbalunits": [
        {"id": "t5", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Caesari", "tokentype": "lexical", "lemma": "Caesar",
         "relations": [{"related": "t5", "relationship": "agent-dative"}]},
        {"id": "t1", "token": "omnia", "tokentype": "lexical", "lemma": "omnis",
         "relations": [{"related": "t5", "relationship": "subject"}]},
        {"id": "t2", "token": "uno", "tokentype": "lexical", "lemma": "unus",
         "relations": [{"related": "t3", "relationship": "adjectival"}]},
        {"id": "t3", "token": "tempore", "tokentype": "lexical", "lemma": "tempus",
         "relations": [{"related": "t5", "relationship": "ablative"}]},
        {"id": "t4", "token": "erant", "tokentype": "lexical", "lemma": "sum",
         "relations": [{"related": "t5", "relationship": "auxiliary"}]},
        {"id": "t5", "token": "agenda", "tokentype": "lexical", "lemma": "ago", "verbalunitid": "t5",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t6", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Ciceronem consulem creaverunt."
#   t0 Ciceronem  t1 consulem  t2 creaverunt  t3 .
#
# Use 3 of 'predicate' (quarto/concepts/syntactic-analysis.qmd): after a
# verb of naming/making, a substantive describing the direct object
# relates to that object, not to the verb.
# ---------------------------------------------------------------------------

_PREDICATE_OBJECT_CICERONEM_CONSULEM_ANSWER = {
    "reasoning": (
        "creaverunt is the independent main verb. Ciceronem is its direct "
        "object; consulem describes that object after a verb of "
        "making/electing, so it is a 'predicate' related to the direct object "
        "Ciceronem, not to the verb."
    ),
    "verbalunits": [
        {"id": "t2", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Ciceronem", "tokentype": "lexical", "lemma": "Cicero",
         "relations": [{"related": "t2", "relationship": "direct object"}]},
        {"id": "t1", "token": "consulem", "tokentype": "lexical", "lemma": "consul",
         "relations": [{"related": "t0", "relationship": "predicate"}]},
        {"id": "t2", "token": "creaverunt", "tokentype": "lexical", "lemma": "creo", "verbalunitid": "t2",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t3", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Cicero consul creatus est."
#   t0 Cicero  t1 consul  t2 creatus  t3 est  t4 .
#
# Use 4 of 'predicate' (quarto/concepts/syntactic-analysis.qmd): in the
# passive of a verb of naming/making, the predicate relates to the passive
# verb.
# ---------------------------------------------------------------------------

_PREDICATE_PASSIVE_CICERO_CONSUL_ANSWER = {
    "reasoning": (
        "creatus est is a perfect passive anchored on the participle creatus, "
        "with est as its auxiliary. Cicero is the subject. consul is the "
        "predicate of the passive verb of making (the passive of 'Ciceronem "
        "consulem creaverunt'), related to creatus as 'predicate'."
    ),
    "verbalunits": [
        {"id": "t2", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Cicero", "tokentype": "lexical", "lemma": "Cicero",
         "relations": [{"related": "t2", "relationship": "subject"}]},
        {"id": "t1", "token": "consul", "tokentype": "lexical", "lemma": "consul",
         "relations": [{"related": "t2", "relationship": "predicate"}]},
        {"id": "t2", "token": "creatus", "tokentype": "lexical", "lemma": "creo", "verbalunitid": "t2",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t3", "token": "est", "tokentype": "lexical", "lemma": "sum",
         "relations": [{"related": "t2", "relationship": "auxiliary"}]},
        {"id": "t4", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Quem dii amant adulescens moritur."
#   t0 Quem  t1 dii  t2 amant  t3 adulescens  t4 moritur  t5 .
#
# The worked example for an 'implied substantive' with a relative pronoun
# (quarto/concepts/tokens.qmd and syntactic-analysis.qmd): the unexpressed
# antecedent of quem is also the subject of moritur. The implied token
# would stand before the first real token, so it takes the first token's
# id plus '_implied'.
# ---------------------------------------------------------------------------

_IMPLIED_SUBSTANTIVE_QUEM_DII_AMANT_ANSWER = {
    "reasoning": (
        "moritur is the independent main verb; its subject is unexpressed, "
        "but the relative pronoun quem needs an antecedent, so an implied "
        "substantive (t0_implied) stands for it: it is the subject of moritur "
        "and the antecedent of quem. quem is also the direct object of amant, "
        "the dependent verb of the relative clause, whose subject is dii. "
        "adulescens is a predicate of state with moritur ('dies young')."
    ),
    "verbalunits": [
        {"id": "t2", "syntactic_type": "dependent"},
        {"id": "t4", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0_implied", "token": None, "tokentype": "implied substantive",
         "relations": [{"related": "t4", "relationship": "subject"}]},
        {"id": "t0", "token": "Quem", "tokentype": "lexical", "lemma": "qui",
         "relations": [{"related": "t0_implied", "relationship": "relative pronoun"}, {"related": "t2", "relationship": "direct object"}]},
        {"id": "t1", "token": "dii", "tokentype": "lexical", "lemma": "deus",
         "relations": [{"related": "t2", "relationship": "subject"}]},
        {"id": "t2", "token": "amant", "tokentype": "lexical", "lemma": "amo", "verbalunitid": "t2",
         "relations": [{"related": "t0", "relationship": "unit verb"}]},
        {"id": "t3", "token": "adulescens", "tokentype": "lexical", "lemma": "adulescens",
         "relations": [{"related": "t4", "relationship": "predicate"}]},
        {"id": "t4", "token": "moritur", "tokentype": "lexical", "lemma": "morior", "verbalunitid": "t4",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t5", "token": ".", "tokentype": "punctuation"},
    ],
}


# ---------------------------------------------------------------------------
# "Carthago delenda est."
#   t0 Carthago  t1 delenda  t2 est  t3 .
#
# A gerundive + sum (passive periphrastic) is a compound form anchored on
# the gerundive (quarto/concepts/verbalunits.qmd); its syntactic type comes
# from its context ('independent' here), not 'gerundive'.
# ---------------------------------------------------------------------------

_PASSIVE_PERIPHRASTIC_CARTHAGO_DELENDA_ANSWER = {
    "reasoning": (
        "delenda est is a passive periphrastic: the gerundive delenda anchors "
        "the verbal expression (independent, since this is a main clause), "
        "est is its auxiliary, and Carthago is its subject."
    ),
    "verbalunits": [
        {"id": "t1", "syntactic_type": "independent"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Carthago", "tokentype": "lexical", "lemma": "Carthago",
         "relations": [{"related": "t1", "relationship": "subject"}]},
        {"id": "t1", "token": "delenda", "tokentype": "lexical", "lemma": "deleo", "verbalunitid": "t1",
         "relations": [{"related": "root", "relationship": "unit verb"}]},
        {"id": "t2", "token": "est", "tokentype": "lexical", "lemma": "sum",
         "relations": [{"related": "t1", "relationship": "auxiliary"}]},
        {"id": "t3", "token": ".", "tokentype": "punctuation"},
    ],
}


GOLD_EXAMPLES = [
    GoldExample(
        slug="unit_verb_hercules_cum",
        passage="Hercules cum gregem perlustrasset, pergit ad proximam speluncam.",
        tags=[
            "unit verb",
            "subordinating word",
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
        tags=["numeral", "subject", "adverbial", "object of preposition", "accusative"],
        canned_answer=_NUMERAL_ANSWER,
    ),
    GoldExample(
        slug="lexical_numeral_fratres_joseph_decem",
        passage="Fratres Joseph decem venerunt.",
        tags=["numeral vs lexical (word-form number stays lexical)", "genitive", "adjectival", "subject", "unit verb", "independent"],
        canned_answer=_LEXICAL_NUMERAL_FRATRES_JOSEPH_DECEM_ANSWER,
    ),
    GoldExample(
        slug="numeral_relation_fratres_joseph_xii",
        passage="Fratres Joseph XII venerunt.",
        tags=["numeral", "genitive", "adjectival", "subject", "unit verb", "independent"],
        canned_answer=_NUMERAL_RELATION_FRATRES_JOSEPH_XII_ANSWER,
    ),
    GoldExample(
        slug="syntactic_type_legit_cresceret",
        passage="principes Albanorum in patres, ut ea quoque pars rei publicae cresceret, legit.",
        tags=["independent", "dependent", "unit verb", "subordinating word", "subject", "direct object", "adverbial", "object of preposition"],
        canned_answer=_SYNTACTIC_TYPE_ANSWER,
    ),
    GoldExample(
        slug="semantic_type_transitive_passive_urbs_condita",
        passage="urbs a Romulo condita est.",
        tags=["agent-ablative", "subject", "object of preposition"],
        canned_answer=_TRANSITIVE_PASSIVE_ANSWER,
    ),
    GoldExample(
        slug="semantic_type_linking_verb_etruria_vicina",
        passage="Etruria erat vicina.",
        tags=["subject", "predicate"],
        canned_answer=_LINKING_VERB_ANSWER,
    ),
    GoldExample(
        slug="participle_attributive_gloria_est_consentiens",
        passage="gloria est consentiens laus bonorum.",
        tags=["predicate", "genitive", "adjectival", "participle (attributive, NOT a verbal expression)"],
        canned_answer=_PARTICIPLE_ATTRIBUTIVE_ANSWER,
    ),
    GoldExample(
        slug="participle_predicate_anco_regnante",
        passage="Anco regnante Lucumo Romam commigravit.",
        tags=["circumstantial participle", "ablative absolute", "subject", "dependent", "participle (predicate, IS a verbal expression)"],
        canned_answer=_PARTICIPLE_PREDICATE_ANSWER,
    ),
    GoldExample(
        slug="circumstantial_participle_eum_advenientem",
        passage="Eum advenientem laeti omnes accepere.",
        tags=["circumstantial participle", "direct object", "adjectival", "subject", "unit verb", "dependent", "participle (predicate, agreeing noun keeps its own relation)"],
        canned_answer=_CIRCUMSTANTIAL_PARTICIPLE_ANSWER,
    ),
    GoldExample(
        slug="indirect_statement_facturum_fuisse_dixit",
        passage="Facturum enim se fuisse dixit.",
        tags=["indirect statement", "auxiliary", "subject", "unit verb"],
        canned_answer=_INDIRECT_STATEMENT_ANSWER,
    ),
    GoldExample(
        slug="direct_quote_tuum_est_inquit",
        passage="Tuum est, inquit, Servi regnum.",
        tags=["direct quote", "predicate", "genitive", "subject", "unit verb"],
        canned_answer=_DIRECT_QUOTE_ANSWER,
    ),
    GoldExample(
        slug="aside_equidem_pace_dixerim",
        passage="Equidem, pace dixerim deum, eos nos iam populi Romani beneficio esse spero.",
        tags=["aside", "ablative", "genitive", "adjectival", "adverbial", "subject", "indirect statement", "unit verb"],
        canned_answer=_ASIDE_ANSWER,
    ),
    GoldExample(
        slug="predicate_lucumo_demarati_corinthii_filius",
        passage="Lucumo Demarati Corinthii filius erat.",
        tags=["predicate", "genitive", "adjectival", "subject"],
        canned_answer=_PREDICATE_ANSWER,
    ),
    GoldExample(
        slug="relative_pronoun_latini_cum_quibus",
        passage="Latini, cum quibus ictum foedus erat, sustulerant animos.",
        tags=["relative pronoun", "object of preposition", "auxiliary", "subject", "direct object", "unit verb", "adverbial", "relatedtoken2/relationship2 overflow"],
        canned_answer=_RELATIVE_PRONOUN_ANSWER,
    ),
    GoldExample(
        slug="dative_genitive_lucumo_superfuit",
        passage="Lucumo superfuit patri bonorum omnium heres.",
        tags=["dative", "genitive", "adjectival", "subject"],
        canned_answer=_DATIVE_GENITIVE_ANSWER,
    ),
    GoldExample(
        slug="adverb_auxiliary_ad_ianiculum_ventum",
        passage="Ad Ianiculum forte ventum erat.",
        tags=["adverbial", "auxiliary", "object of preposition"],
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
        tags=["dative", "subordinating word", "unit verb", "subject",
              "direct object", "adverbial", "object of preposition", "adjectival"],
        canned_answer=_DATIVE_ANSWER,
    ),
    GoldExample(
        slug="attributive_pugna_ad_cannas",
        passage="Pugna ad Cannas fuit clara.",
        tags=["adjectival", "object of preposition", "predicate", "subject"],
        canned_answer=_ATTRIBUTIVE_ANSWER,
    ),
    GoldExample(
        slug="enclitic_context_ablative_aequa_ratione",
        passage="Aequa ratione imperat.",
        tags=["enclitic (context-dependent tokenization, non-split case)", "ablative", "adjectival"],
        canned_answer=_ENCLITIC_CONTEXT_ABLATIVE_ANSWER,
    ),
    GoldExample(
        slug="enclitic_context_interrogative_ratione_docet",
        passage="Ratione docet?",
        tags=["enclitic (context-dependent tokenization, split case)", "subject"],
        canned_answer=_ENCLITIC_CONTEXT_INTERROGATIVE_ANSWER,
    ),
    GoldExample(
        slug="enclitic_incorporated_quisque_officium",
        passage="Quisque officium suum fecit.",
        tags=["enclitic (historically incorporated, never split)", "subject", "direct object", "adjectival"],
        canned_answer=_ENCLITIC_INCORPORATED_QUISQUE_ANSWER,
    ),
    GoldExample(
        slug="coordinating_conjunction_verbs_ille_hermionenque",
        passage="Ille fidem suam infirmare noluit, Hermionenque ab Oreste adduxit.",
        tags=["coordinating conjunction (pair of verbal expressions, word-order mismatch)", "subject", "direct object", "adverbial", "object of preposition"],
        canned_answer=_COORDINATING_CONJUNCTION_VERBS_ANSWER,
    ),
    GoldExample(
        slug="coordinating_conjunction_sentence_initial_sed_dedit",
        passage="Sed re cognita, iussu Cereris Triptolemo regnum dedit.",
        tags=["coordinating conjunction (sentence-initial, one-sided)", "circumstantial participle", "ablative absolute", "ablative", "genitive", "dative", "direct object", "dependent"],
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
        tags=["subordinating word", "unit verb", "subject",
              "indirect statement", "dependent",
              "depth of subordination (2 levels)"],
        canned_answer=_DEPTH_TWO_CUM_SCIRET_PECCAVISSE_ANSWER,
    ),
    GoldExample(
        slug="coordinating_conjunction_dedit_et_dixit_esse",
        passage="Ille moriens, cum sciret sagittas hydrae Lernaeae felle tinctas, sanguinem suum exceptum Deianirae dedit et id philtrum esse dixit.",
        tags=["coordinating conjunction (pair of independent verbs, second "
              "also governs an indirect statement)", "circumstantial "
              "participle (prefer over attributive when uncertain)",
              "subordinating word", "unit verb",
              "indirect statement", "subject", "direct object", "dative",
              "genitive", "ablative", "adjectival", "predicate",
              "dependent", "independent", "depth of subordination (2 levels)"],
        canned_answer=_COORDINATING_CONJUNCTION_DEDIT_ET_DIXIT_ANSWER,
    ),
    GoldExample(
        slug="coordinating_conjunction_series_assiduitate_varietate_magnificentia",
        passage="Tarquinius et assiduitate et varietate et magnificentia omnes antecessit.",
        tags=["coordinating conjunction (series/polysyndeton of three connectors, 'et A et B et C' shape: an introductory connector before the first item takes relatedtoken1 only, every later connector pairs its flanking items like an ordinary two-item conjunction)", "subject", "ablative", "direct object", "unit verb", "independent"],
        canned_answer=_COORDINATING_CONJUNCTION_SERIES_ANSWER,
    ),
    GoldExample(
        slug="indirect_question_theseus_audit_quanta",
        passage="Theseus audit quanta calamitate ciuitas afficeretur.",
        tags=["subordinating conjunction (interrogative word introducing an indirect question, reuses the label)", "unit verb", "adjectival", "ablative", "subject", "dependent", "independent", "relatedtoken2/relationship2 overflow"],
        canned_answer=_INDIRECT_QUESTION_THESEUS_AUDIT_ANSWER,
    ),
    GoldExample(
        slug="apposition_neptunus_aegeus_filius",
        passage="Neptunus et Aegeus Pandionis filius in fano Mineruae cum Aethra Pitthei filia una nocte concubuerunt.",
        tags=["apposition", "genitive", "coordinating conjunction (pair of nouns)", "adverbial", "object of preposition", "subject", "adjectival", "ablative", "independent"],
        canned_answer=_APPOSITION_NEPTUNUS_AEGEUS_ANSWER,
    ),
    GoldExample(
        slug="complementary_infinitive_amphion_expugnare_vellet",
        passage="Amphion autem cum templum Apollinis expugnare vellet, ab Apolline sagittis est interfectus.",
        tags=["complementary infinitive", "subordinating word", "unit verb", "direct object", "genitive", "agent-ablative", "object of preposition", "ablative", "subject", "auxiliary", "dependent", "independent"],
        canned_answer=_COMPLEMENTARY_INFINITIVE_AMPHION_ANSWER,
    ),
    GoldExample(
        slug="infinitive_as_subject_dolere_malum",
        passage="Dolere malum est.",
        tags=["infinitive used as a noun (subject, no verbal-expression status)", "subject", "predicate", "unit verb", "independent"],
        canned_answer=_INFINITIVE_AS_SUBJECT_DOLERE_MALUM_ANSWER,
    ),
    GoldExample(
        slug="gerundive_metapontus_sacrum_faciendum",
        passage="Metapontus exiit ad Dianam Metapontinam ad sacrum faciendum.",
        tags=["gerundive (treated as an ordinary adjective)", "adjectival", "adverbial", "object of preposition", "subject", "unit verb", "independent"],
        canned_answer=_GERUNDIVE_METAPONTUS_SACRUM_FACIENDUM_ANSWER,
    ),
    GoldExample(
        slug="gerund_ars_bene_disserendi",
        passage="Ars bene disserendi magna est.",
        tags=["gerund (treated as an ordinary noun, can take its own adverb)", "genitive", "adverbial", "subject", "predicate", "unit verb", "independent"],
        canned_answer=_GERUND_ARS_BENE_DISSERENDI_ANSWER,
    ),
    GoldExample(
        slug="implied_sum_omnia_praeclara_rara",
        passage="Omnia praeclara rara.",
        tags=["implied sum (elided present of sum, bare predicate construction)", "subject", "predicate", "adjectival", "unit verb", "independent"],
        canned_answer=_IMPLIED_SUM_OMNIA_PRAECLARA_ANSWER,
    ),
    GoldExample(
        slug="implied_sum_consules_facti",
        passage="inde P. Valerius iterum T. Lucretius consules facti.",
        tags=["implied sum (elided present of sum, compound perfect passive)", "subject", "predicate", "auxiliary", "adverbial", "unit verb", "independent"],
        canned_answer=_IMPLIED_SUM_CONSULES_FACTI_ANSWER,
    ),
    GoldExample(
        slug="implied_participle_of_sum_consulibus",
        passage="P. Valerius anno post Agrippa Menenio P. Postumio consulibus moritur.",
        tags=["implied sum (always-implied participle of sum, ablative absolute)", "circumstantial participle", "ablative absolute", "apposition", "subject", "ablative", "adverbial", "unit verb", "dependent", "independent"],
        canned_answer=_IMPLIED_PARTICIPLE_OF_SUM_CONSULIBUS_ANSWER,
    ),
    GoldExample(
        slug="implied_subject_recordatus_somniorum_ait",
        passage="Recordatus somniorum ait ad eos.",
        tags=["implied subject (circumstantial participle agreeing with a governing verb's own unexpressed subject)", "circumstantial participle", "genitive", "adverbial", "object of preposition", "unit verb", "dependent", "independent"],
        canned_answer=_IMPLIED_SUBJECT_RECORDATUS_SOMNIORUM_ANSWER,
    ),
    GoldExample(
        slug="continuation_indirect_discourse_tarquinios_adsuesse",
        passage="nimium Tarquinios regno adsuesse; initium a Prisco factum esse; regnasse dein Ser. Tullium.",
        tags=["continued discourse (continuation of indirect discourse, shared governing verb)", "indirect statement", "subject", "dative", "agent-ablative", "object of preposition", "auxiliary", "adverbial", "unit verb", "independent"],
        canned_answer=_CONTINUATION_INDIRECT_DISCOURSE_ANSWER,
    ),
    GoldExample(
        slug="praenomen_sex_tarquinius_venit",
        passage="Sex. Tarquinius inscio Collatino cum comite uno Collatiam venit.",
        tags=["praenomen", "subject", "circumstantial participle", "ablative absolute", "adjectival", "adverbial", "object of preposition", "implied sum (always-implied participle of sum, ablative absolute)", "unit verb", "independent", "dependent"],
        canned_answer=_PRAENOMEN_SEX_TARQUINIUS_ANSWER,
    ),
    GoldExample(
        slug="accusative_romam_venit",
        passage="Romam venit.",
        tags=["accusative", "unit verb", "independent"],
        canned_answer=_ACCUSATIVE_ROMAM_VENIT_ANSWER,
    ),
    GoldExample(
        slug="accusative_milia_passuum_iter",
        passage="Duo milia passuum iter fecerunt.",
        tags=["accusative", "adjectival", "genitive", "direct object", "unit verb", "independent"],
        canned_answer=_ACCUSATIVE_MILIA_PASSUUM_ITER_ANSWER,
    ),
    GoldExample(
        slug="ablative_opus_est_verbis",
        passage="Collatinus negat verbis opus esse.",
        tags=["ablative (idiomatic 'opus est')", "subject", "predicate", "indirect statement", "unit verb", "independent"],
        canned_answer=_ABLATIVE_OPUS_EST_VERBIS_ANSWER,
    ),
    GoldExample(
        slug="vocative_domine_venit",
        passage="Domine, venit.",
        tags=["vocative", "unit verb", "independent"],
        canned_answer=_VOCATIVE_DOMINE_VENIT_ANSWER,
    ),
    # RelationLabel coverage is complete -- every documented relation has at
    # least one tagged example, including the relatedtoken2/relationship2
    # overflow pattern, "coordinating word" (which uses relation1 AND
    # relation2 for two ends of the same relation, not as an overflow slot --
    # see enclitic_arma_virumque_cano for the paired-nouns case, the two new
    # coordinating_conjunction_* fixtures above for the paired-verbs,
    # sentence-initial, and et-as-adverb cases), "apposition" (see
    # apposition_neptunus_aegeus_filius), "subordinating word"'s
    # reuse for the interrogative word introducing an indirect question
    # (see indirect_question_theseus_audit_quanta), "complementary
    # infinitive" (see complementary_infinitive_amphion_expugnare_vellet),
    # "praenomen" (see praenomen_sex_tarquinius_venit, and now also
    # praenomen_abbreviation_m_agrippa_cos, implied_sum_consules_facti,
    # implied_participle_of_sum_consulibus, and
    # continuation_indirect_discourse_tarquinios_adsuesse, all retrofitted
    # once this label was added), "accusative" (see
    # accusative_romam_venit for the verb-linked case,
    # accusative_milia_passuum_iter for the noun-linked case, and now also
    # numeral_hiberna_aberant_xxv, retrofitted once this label was added),
    # and "vocative" (see vocative_domine_venit -- always verb-linked, per
    # the scheme docs' own note, so there's no noun-linked counterpart to
    # add the way accusative has one).
    # ablative_opus_est_verbis adds a documented idiom for the pre-existing
    # "ablative" label (the 'opus est' construction) rather than exercising
    # a new one. Two related constructions need no dedicated label at all
    # and are exercised for documentation/regression value rather than
    # test_coverage.py's sake: an infinitive used as an ordinary noun
    # (infinitive_as_subject_dolere_malum) and gerunds/gerundives
    # (gerund_ars_bene_disserendi, gerundive_metapontus_sacrum_faciendum),
    # which simply reuse 'genitive'/'adverbial' and 'adjectival'
    # respectively. VerbalExpression.syntactic_type coverage is also
    # complete: independent, dependent, direct quote, aside, and indirect
    # statement all have a tagged example. TokenAnalysis.tokentype coverage
    # is also complete, including "abbreviation" (see
    # praenomen_abbreviation_m_agrippa_cos) and the enclitic-tokenization
    # nuances the scheme docs' tokenization section documents: a
    # context-dependent split ("ratione") and a word that has incorporated
    # its historic enclitic and must never be split ("quisque" and its
    # compounds), and now all three implied-token types too (see
    # models.py's IMPLIED_TOKENTYPES): "implied sum" for an elided present
    # of *sum* (bare predicate construction, implied_sum_omnia_praeclara_rara;
    # compound perfect passive with the auxiliary omitted,
    # implied_sum_consules_facti; the always-implied participle of *sum*,
    # implied_participle_of_sum_consulibus), "implied verb" for a
    # continuation of indirect discourse sharing one unwritten governing verb
    # (continuation_indirect_discourse_tarquinios_adsuesse), and "implied
    # subject" for a circumstantial participle agreeing with a governing
    # verb's own unexpressed subject (implied_subject_recordatus_somniorum_ait).
    # "implied substantive" never anchors a verbal expression (no `verbalunits`
    # entry of its own), and neither does "implied sum" in its
    # implied_sum_consules_facti sub-case specifically -- there, the real,
    # already-present participle (facti) anchors instead, and the implied
    # token merely relates to it via 'auxiliary'. "implied sum" DOES anchor
    # its own verbal expression in its other two sub-cases (bare predicate;
    # always-implied participle of *sum*), and "implied verb" always
    # anchors -- so "implied sum" is the one implied-token type whose
    # anchoring behavior depends on which sub-case applies.
    # lexical_numeral_fratres_joseph_decem exercises the scheme docs'
    # clarified numeral-vs-lexical boundary (see the numeral tokentype's
    # own note in models.py's TokenAnalysis.tokentype field): a number
    # spelled out as a word ("decem") is 'lexical', not 'numeral', unlike
    # numeral_hiberna_aberant_xxv's numerically-written "XXV". Not itself
    # needed for test_coverage.py's sake (numeral_hiberna_aberant_xxv
    # already exercises both 'lexical' and 'numeral'), but worth keeping
    # as a regression fixture for the distinction specifically.
    # numeral_relation_fratres_joseph_xii is the regression fixture for the
    # HTML-coloring bug fix: numeral_hiberna_aberant_xxv's "XXV" carries no
    # relation at all, so it never exercised _tokens_to_html()'s
    # tokentype-eligibility check either way. This fixture gives a numeral
    # ("XII") a real relation ("adjectival" -> Fratres, the same relation
    # lexical_numeral_fratres_joseph_decem's spelled-out "decem" uses at the
    # same position) specifically so
    # test_html_colors_match_mermaid_colors_for_every_gold_example (and
    # test_depth_html_never_warns_and_covers_every_token_for_every_gold_example)
    # would catch a numeral-with-relation going uncolored in HTML/depth-HTML
    # while Mermaid colors it correctly -- the exact bug reported by the
    # user, previously invisible to this fixture set.
    # coordinating_conjunction_series_assiduitate_varietate_magnificentia
    # is not needed for test_coverage.py's sake ("coordinating word"
    # is already covered by the pairwise fixtures above) -- it exists for
    # documentation/regression value, exercising the scheme docs' series/
    # polysyndeton chaining rule (relatedtoken2 links between NEIGHBORING
    # connectors, not between the two conjuncts) and guarding
    # find_unanchored_coordinated_verbs()'s series-aware fix (see that
    # function's own docstring, and test_verbal_units.py's synthetic
    # verb-series test for the false positive this fixture's own
    # noun-series shape doesn't happen to trigger on its own).
    GoldExample(
        slug="parataxis_precor_eam_videam",
        passage="Precor eam videam.",
        tags=["parataxis", "unit verb", "direct object"],
        canned_answer=_PARATAXIS_PRECOR_ANSWER,
    ),
    GoldExample(
        slug="agent_dative_caesari_omnia_agenda",
        passage="Caesari omnia uno tempore erant agenda.",
        tags=["agent-dative", "auxiliary", "subject", "ablative", "adjectival"],
        canned_answer=_AGENT_DATIVE_CAESARI_AGENDA_ANSWER,
    ),
    GoldExample(
        slug="predicate_of_object_ciceronem_consulem",
        passage="Ciceronem consulem creaverunt.",
        tags=["predicate", "direct object"],
        canned_answer=_PREDICATE_OBJECT_CICERONEM_CONSULEM_ANSWER,
    ),
    GoldExample(
        slug="predicate_passive_cicero_consul_creatus",
        passage="Cicero consul creatus est.",
        tags=["predicate", "subject", "auxiliary"],
        canned_answer=_PREDICATE_PASSIVE_CICERO_CONSUL_ANSWER,
    ),
    GoldExample(
        slug="implied_substantive_quem_dii_amant",
        passage="Quem dii amant adulescens moritur.",
        tags=["implied substantive", "relative pronoun", "direct object", "predicate"],
        canned_answer=_IMPLIED_SUBSTANTIVE_QUEM_DII_AMANT_ANSWER,
    ),
    GoldExample(
        slug="passive_periphrastic_carthago_delenda_est",
        passage="Carthago delenda est.",
        tags=["auxiliary", "subject"],
        canned_answer=_PASSIVE_PERIPHRASTIC_CARTHAGO_DELENDA_ANSWER,
    ),
]
 