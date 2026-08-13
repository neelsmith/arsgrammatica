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
# notes.md's own worked example for "unit verb" / "subordinating
# conjunction". Moved here unchanged from the original test_pipeline.py.
# ---------------------------------------------------------------------------
 
_HERCULES_ANSWER = {
    "reasoning": (
        "perlustrasset is the dependent verb of the cum-clause, linked to cum as "
        "its unit verb; cum is the subordinating conjunction linked to the main "
        "verb pergit; gregem is the direct object of perlustrasset; Hercules is "
        "the subject of pergit; ad is an adverbial preposition modifying pergit, "
        "governing speluncam as its object."
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
         "verbalunitid": "t5"},
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
# syntax_model.md's own worked example for the *enclitic* token type:
# "the enclitic que in the phrase arma virumque cano." virumque splits into
# virum (lexical) + que (enclitic). que itself gets no relation -- the
# scheme has no documented relation type for a connective enclitic, per
# "Incomplete status".
# ---------------------------------------------------------------------------
 
_ENCLITIC_ANSWER = {
    "reasoning": (
        "cano is the independent main verb (transitive active, 'I sing'); "
        "arma and virum -- joined by the enclitic -que ('and') -- are both "
        "its direct objects."
    ),
    "verbalunits": [
        {"id": "t3", "syntactic_type": "independent", "semantic_type": "transitive active"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "arma", "tokentype": "lexical", "lemma": "arma",
         "relatedtoken1": "t3", "relationship1": "direct object"},
        {"id": "t1", "token": "virum", "tokentype": "lexical", "lemma": "vir",
         "relatedtoken1": "t3", "relationship1": "direct object"},
        {"id": "t2", "token": "que", "tokentype": "enclitic"},
        {"id": "t3", "token": "cano", "tokentype": "lexical", "lemma": "cano",
         "verbalunitid": "t3"},
        {"id": "t4", "token": ".", "tokentype": "punctuation"},
    ],
}
 
 
# ---------------------------------------------------------------------------
# "M. Tullius epistulam scripsit."
#   t0 M.  t1 Tullius  t2 epistulam  t3 scripsit  t4 .
#
# Adapted from syntax_model.md's *praenomen* example ("M. Agrippa L. f. cos.
# tertium fecit") -- trimmed to just the praenomen "M." and dropped "L. f.
# cos.", which are *abbreviation* tokens. TokenAnalysis.tokentype doesn't
# have an "abbreviation" value yet (syntax_model.md documents it, models.py
# hasn't caught up), so a fixture using "f."/"cos." would fail to validate
# against the current model -- that's a separate gap, not this one. M. gets
# no relation of its own: the scheme has no documented relation type for a
# praenomen's link to the name it precedes.
# ---------------------------------------------------------------------------
 
_PRAENOMEN_ANSWER = {
    "reasoning": (
        "scripsit is the independent main verb (transitive active); Tullius "
        "(with the praenomen M.) is its subject, epistulam its direct object."
    ),
    "verbalunits": [
        {"id": "t3", "syntactic_type": "independent", "semantic_type": "transitive active"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "M.", "tokentype": "praenomen"},
        {"id": "t1", "token": "Tullius", "tokentype": "lexical", "lemma": "Tullius",
         "relatedtoken1": "t3", "relationship1": "subject"},
        {"id": "t2", "token": "epistulam", "tokentype": "lexical", "lemma": "epistula",
         "relatedtoken1": "t3", "relationship1": "direct object"},
        {"id": "t3", "token": "scripsit", "tokentype": "lexical", "lemma": "scribo",
         "verbalunitid": "t3"},
        {"id": "t4", "token": ".", "tokentype": "punctuation"},
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
        "distant'); Hiberna is its subject; ab is an adverbial preposition "
        "modifying aberant, governing eo as its object of preposition; "
        "milia passuum XXV ('twenty-five thousand paces') is an accusative-"
        "of-extent phrase with no relation type in the current scheme."
    ),
    "verbalunits": [
        {"id": "t1", "syntactic_type": "independent", "semantic_type": "intransitive"},
    ],
    "tokengraph": [
        {"id": "t0", "token": "Hiberna", "tokentype": "lexical", "lemma": "hiberna",
         "relatedtoken1": "t1", "relationship1": "subject"},
        {"id": "t1", "token": "aberant", "tokentype": "lexical", "lemma": "absum",
         "verbalunitid": "t1"},
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
        tags=["enclitic", "direct object"],
        canned_answer=_ENCLITIC_ANSWER,
    ),
    GoldExample(
        slug="praenomen_m_tullius_scripsit",
        passage="M. Tullius epistulam scripsit.",
        tags=["praenomen", "subject", "direct object"],
        canned_answer=_PRAENOMEN_ANSWER,
    ),
    GoldExample(
        slug="numeral_hiberna_aberant_xxv",
        passage="Hiberna aberant ab eo milia passuum XXV.",
        tags=["numeral", "subject", "adverbial", "object of preposition"],
        canned_answer=_NUMERAL_ANSWER,
    ),
    # Next up (see test_coverage.py's failure for the authoritative list):
    #   - "agent" + "object of preposition" via a passive + a/ab phrase
    #   - "relative pronoun" via an antecedent example
    #   - "attributive" (vs. "adverbial") via a noun-modifying prepositional phrase
    #   - a relatedtoken2/relationship2 overflow case (relative pronoun that is
    #     also a subject/object/object-of-preposition)
    #   - "linking verb" + "transitive passive" verbal-expression semantic types
]
