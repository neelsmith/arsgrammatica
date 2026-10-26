"""
Pydantic models for arsgrammatica's analytical scheme. The authoritative
specification is the three "Concepts" pages of the Quarto documentation
(these replace the retired the scheme docs (quarto/concepts/)):

- quarto/concepts/tokens.qmd -- token categories and implied tokens
  (Token, TokenAnalysis.tokentype, IMPLIED_TOKENTYPES);
- quarto/concepts/verbalunits.qmd -- verbal expressions and their syntactic
  types (VerbalExpression, SyntacticType);
- quarto/concepts/syntactic-analysis.qmd -- the graph of syntactic
  relations (TokenAnalysis.relations, Relation, RelationLabel).

An analysis of a sentence is two structures:

1. a list of VerbalExpression entries (the verbal expressions that anchor
   the analysis), and
2. a list of TokenAnalysis entries (one per token, real or implied), each
   with zero or more Relation edges to other nodes of the syntax graph.

These need to be real pydantic BaseModel subclasses (not plain classes with
bare `=` assignments) for DSPy to generate and validate structured output
against them when used inside `List[...]` input/output fields.
"""

from typing import Iterable, List, Literal, Optional

from pydantic import BaseModel, Field


class CitedText(BaseModel):
    """One citable unit of source text -- e.g. one line of poetry, one
    section of prose -- paired with its citation label. A sequence of
    these is segmentation_dspy.py's input: sentence boundaries do NOT need
    to respect CitedText boundaries (one sentence may span several units),
    but every resulting token still records which unit it came from via
    Token.citation."""
 
    citation: str = Field(description="Citation label for this unit, e.g. 'Aeneid 1.1'.")
    text: str = Field(description="This unit's raw text, exactly as written.")
 
 
class Token(BaseModel):
    """A single pre-segmented token with a stable id.
 
    `citation` is optional so this model still works for citation-free
    callers -- e.g. a test fixture built directly from a canned tokengraph,
    with no CitedText source at all -- as well as for the citation-aware
    segmentation stage (segmentation_dspy.py), which is the only thing that
    actually populates it, knowing which CitedText source unit each token
    came from."""
 
    id: str = Field(description="Stable token id, unique across the whole input, e.g. 't0', 't1', .... As produced directly by segment_sources(), sequential and unique only WITHIN that one call; a caller that combines several such calls (or wants a given passage to keep the same ids across separate runs) should rewrite these first -- see token_ids.assign_passage_scoped_ids().")
    text: str = Field(description="The token's surface text, exactly as it appears in the source.")
    citation: Optional[str] = Field(
        default=None,
        description="Citation label of the source unit this token came from (e.g. 'Aeneid 1.1'), if known.",
    )
 
 
class Sentence(BaseModel):
    """One sentence's worth of tokens, in reading order, as produced by the
    LLM-driven segmentation stage (segmentation_dspy.py). Ids are global
    across whatever ONE segment_sources() call produced this Sentence --
    numbering continues across sentence boundaries within that call rather
    than restarting at t0 for each sentence -- so a freshly-segmented
    Sentence is a contiguous slice of that call's own id sequence, not an
    independently-numbered unit. A Sentence handed back by
    pipeline.analyze_sources() (or read back from a file
    tokenize_ctsdata.py wrote) may instead carry passage-scoped composite
    ids (token_ids.assign_passage_scoped_ids()) in place of that raw
    per-call numbering -- see that module's own docstring."""
 
    tokens: List[Token] = Field(
        description="This sentence's tokens, in reading order, using the passage's global token ids."
    )


# Syntactic types of verbal expressions (quarto/concepts/verbalunits.qmd;
# allowed values listed in quarto/reference/vuvalues.qmd):
#   finite verbs, and gerundives in a passive periphrastic (gerundive + sum):
#       independent, dependent, direct quote, aside, parataxis
#   infinitives: indirect statement
#   participles not in attributive construction: circumstantial participle
#   other (attributive) gerundives: gerundive
SyntacticType = Literal[
    "independent",
    "dependent",
    "direct quote",
    "aside",
    "parataxis",
    "indirect statement",
    "circumstantial participle",
    "gerundive",
]


# Every relation label documented in quarto/concepts/syntactic-analysis.qmd,
# grouped as on that page.
RelationLabel = Literal[
    # Constructions of verbal expressions
    "unit verb",
    "auxiliary",
    "direct quote",
    "aside",
    "parataxis",
    "indirect statement",
    "circumstantial participle",
    "gerundive",
    # Other constructions with verbs
    "complementary infinitive",
    # A-A-T relations
    "subject",
    "agent-ablative",
    "agent-dative",
    "direct object",
    "predicate",
    # Case constructions with substantives
    "genitive",
    "dative",
    "accusative",
    "ablative",
    "vocative",
    # Adverbial and adjectival expressions
    "adverbial",
    "adjectival",
    "object of preposition",
    # Special substantive relations
    "ablative absolute",
    "apposition",
    "praenomen",
    # Coordinating and subordinating words
    "coordinating word",
    "subordinating word",
    "relative pronoun",
]


# Token categories (quarto/concepts/tokens.qmd; allowed values listed in
# quarto/reference/tokentypes.qmd). The first six are real tokens; the last
# three are implied tokens with no surface text (see IMPLIED_TOKENTYPES).
TokenType = Literal[
    "praenomen",
    "abbreviation",
    "punctuation",
    "enclitic",
    "numeral",
    "lexical",
    "implied sum",
    "implied verb",
    "implied substantive",
]


class VerbalExpression(BaseModel):
    """One verbal expression (quarto/concepts/verbalunits.qmd). Four
    constructions count as verbal expressions:

    - every finite verb (including the compound forms of the perfect
      passive system, participle + a form of *sum*, anchored on the
      participle);
    - an infinitive that is the verb of an indirect statement (NOT a
      complementary infinitive, and NOT an infinitive used as a
      substantive);
    - a participle with a circumstantial (not purely attributive) sense;
    - every gerundive (but NOT the gerund, which is a substantive).

    Implied verbal expressions (an implied form of *sum*, or an understood
    repeated verb) are verbal expressions too, anchored on their implied
    token (see TokenAnalysis and IMPLIED_TOKENTYPES).

    A verbal expression is classified only by its syntactic type; the
    semantic types of the earlier scheme ('transitive active' etc.) were
    retired along with the scheme docs (quarto/concepts/)."""

    id: str = Field(
        description=(
            "Id of the token that anchors this verbal expression: the finite "
            "verb, the indirect-statement infinitive, the circumstantial "
            "participle, or the gerundive. For a compound form with a form of "
            "*sum* (perfect passive system, future infinitive, or gerundive + "
            "*sum*), use the participle's, infinitive's or gerundive's id, "
            "NOT the form of *sum* (which relates to it as 'auxiliary'). For "
            "an implied verbal expression, use the implied token's id."
        )
    )
    syntactic_type: SyntacticType = Field(
        description=(
            "'independent' (main verb), 'dependent' (introduced by a "
            "subordinating word or relative pronoun), 'direct quote' (the "
            "top-level verb of directly quoted speech), 'aside' (interrupts "
            "the surrounding syntax), 'parataxis' (a subjunctive governed, "
            "without any subordinating word, by a verb of necessity, wishing, "
            "preference or command), 'indirect statement' (an infinitive in "
            "indirect speech), 'circumstantial participle', or 'gerundive' "
            "(an attributive gerundive). A gerundive + *sum* (passive "
            "periphrastic) instead takes the type of its context, like any "
            "finite or infinitive form."
        )
    )


class Relation(BaseModel):
    """One edge of the syntax graph, from the TokenAnalysis that owns it to
    another node: a real token, an implied token, or the reserved value
    'root' (quarto/concepts/syntactic-analysis.qmd).

    A token may have any number of relations. The order of a token's
    relations carries no meaning (the serialization format,
    quarto/reference/analysisformat.qmd, leaves it unspecified), so code
    must select a relation by its label, never by its position."""

    related: str = Field(
        description=(
            "Id of the related node: a token id from the input `tokens`, the "
            "id of an implied token, or the reserved value 'root' (used only "
            "as the target of an independent verb's 'unit verb' relation; "
            "'root' may never be used as a token id)."
        )
    )
    relationship: RelationLabel = Field(description="The kind of relation (one of the documented relation labels).")


class TokenAnalysis(BaseModel):
    """One node of the syntax graph (quarto/concepts/syntactic-analysis.qmd).

    Most entries correspond 1:1 to an entry in the input `tokens` list. The
    exceptions are implied tokens (quarto/concepts/tokens.qmd, "Implied
    tokens"), which have no surface text and use a NEW id. There are three
    kinds, one per IMPLIED_TOKENTYPES value:

    - 'implied sum': an elided form of *sum*. It anchors its own verbal
      expression (e.g. "omnia praeclara rara", or the always-implied
      participle of *sum* in "Agrippa Menenio P. Postumio consulibus"),
      EXCEPT when it is the missing auxiliary of a compound form (e.g.
      "consules facti" for "facti sunt"): then the real participle anchors
      the verbal expression and the implied token only relates to it as
      'auxiliary'.
    - 'implied verb': an understood repeated verb -- e.g. a verb shared by
      parallel clauses, or a governing verb of speaking left unrepeated over
      a long passage of indirect discourse. Always anchors its own verbal
      expression.
    - 'implied substantive': an unexpressed antecedent that a relative
      pronoun or a participle depends on. Never a verbal expression.

    Every non-punctuation token should have at least one relation; a token
    may have several (e.g. a relative pronoun relates both to its antecedent
    and to its function in its own clause; a coordinating word relates to
    each of the items it joins)."""

    id: str = Field(
        description=(
            "For a real token, the id of the corresponding entry in the input "
            "`tokens` list. For an implied token, a NEW id not used by any "
            "other token (see SentenceAnalysis's docstring for the naming "
            "convention)."
        )
    )
    token: Optional[str] = Field(
        default=None,
        description=(
            "The token's surface text; should match the `text` of the input "
            "token with this id. Leave unset (None) ONLY for an implied token "
            "('implied sum', 'implied verb' or 'implied substantive')."
        ),
    )
    tokentype: TokenType = Field(
        description=(
            "'praenomen': a Roman first name, abbreviated (with its period, "
            "e.g. 'M.') or not, used with a nomen or cognomen; 'abbreviation': "
            "any other abbreviation, with its period (e.g. 'f.', 'cos.'); "
            "'punctuation'; 'enclitic' (e.g. 'que', 've', 'ne' written "
            "attached to the preceding word); 'numeral': a number written "
            "with numerals (e.g. 'XXV'), not spelled out as a word; "
            "'lexical': any other word. 'implied sum', 'implied verb' and "
            "'implied substantive' mark implied tokens with no surface text."
        )
    )
    lemma: Optional[str] = Field(
        default=None,
        description=(
            "Dictionary headword. Omit for punctuation. For an implied "
            "token, the lemma of the implied word if known (e.g. 'sum')."
        ),
    )
    verbalunitid: Optional[str] = Field(
        default=None,
        description="If this token anchors a verbal expression in `verbalunits`, repeat its own id here; otherwise omit.",
    )
    relations: List[Relation] = Field(
        default_factory=list,
        description=(
            "Every relation from this token to another node of the syntax "
            "graph, in no particular order. Empty only for punctuation (or a "
            "token the analysis could not relate)."
        ),
    )

    def related_ids(self, relationship: Optional[str] = None) -> List[str]:
        """Ids this token relates to, optionally only via `relationship`."""
        return [
            rel.related for rel in self.relations
            if relationship is None or rel.relationship == relationship
        ]

    def relationships(self) -> List[str]:
        """This token's relation labels, in stored order."""
        return [rel.relationship for rel in self.relations]

    def has_relationship(self, *labels: str) -> bool:
        """True if any of this token's relations uses one of `labels`."""
        return any(rel.relationship in labels for rel in self.relations)

    def first_related(self, *labels: str) -> Optional[str]:
        """The target of this token's first relation using one of `labels`
        (any label if none given), or None."""
        for rel in self.relations:
            if not labels or rel.relationship in labels:
                return rel.related
        return None

    def add_relation(self, related: str, relationship: str) -> None:
        """Append a relation (convenience for building graphs by hand)."""
        self.relations.append(Relation(related=related, relationship=relationship))


def rel(related: str, relationship: str) -> Relation:
    """Shorthand constructor: rel('t3', 'subject')."""
    return Relation(related=related, relationship=relationship)


def iter_edges(tokengraph: Iterable[TokenAnalysis]):
    """Yield every (token, relation) pair of a tokengraph, in order."""
    for tok in tokengraph:
        for relation in tok.relations:
            yield tok, relation


# The three tokentype values marking an implied token, one with no surface
# realization in the passage (quarto/concepts/tokens.qmd, "Implied
# tokens"). Every module that needs to ask "is this an implied token"
# checks membership in this set rather than hardcoding the strings.
IMPLIED_TOKENTYPES = frozenset({"implied sum", "implied verb", "implied substantive"})

# The subset of IMPLIED_TOKENTYPES that can anchor a verbal expression.
# ('implied sum' does so except when it is an omitted auxiliary.)
IMPLIED_VERBAL_TOKENTYPES = frozenset({"implied sum", "implied verb"})
