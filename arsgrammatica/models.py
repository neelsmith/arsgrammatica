"""
Pydantic models describing the two structures from syntax_model.md:
 
1. A list of VerbalExpression entries (the "table of verbal expressions").
2. A list of TokenAnalysis entries (the "token-level table of dependencies").
 
These need to be real pydantic BaseModel subclasses (not plain classes with
bare `=` assignments) for DSPy to generate and validate structured output
against them when used inside `List[...]` input/output fields.
"""
 
from typing import List, Literal, Optional
 
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
 
    id: str = Field(description="Stable token id, globally unique and sequential across the whole input, e.g. 't0', 't1', ...")
    text: str = Field(description="The token's surface text, exactly as it appears in the source.")
    citation: Optional[str] = Field(
        default=None,
        description="Citation label of the source unit this token came from (e.g. 'Aeneid 1.1'), if known.",
    )
 
 
class Sentence(BaseModel):
    """One sentence's worth of tokens, in reading order, as produced by the
    LLM-driven segmentation stage (segmentation_dspy.py). Token ids are
    global across the whole passage -- numbering continues across sentence
    boundaries rather than restarting at t0 for each sentence -- so a
    Sentence is a contiguous slice of the passage's id sequence, not an
    independently-numbered unit."""
 
    tokens: List[Token] = Field(
        description="This sentence's tokens, in reading order, using the passage's global token ids."
    )
 
 
class VerbalExpression(BaseModel):
    """One entry in the table of verbal expressions (syntax_model.md, 'Table
    of verbal expressions'). Three constructions count as a verbal
    expression: finite verbs, infinitives (when part of indirect speech),
    and participles (when they have a *predicate* sense -- e.g. an
    ablative-absolute-like "Anco regnante...", 'while Ancus was reigning'
    -- rather than a purely *attributive* sense, like an ordinary adjective,
    e.g. "consentiens laus", 'universal praise': that case is NOT a verbal
    expression at all).
 
    Each construction has its own set of allowed `syntactic_type` values:
    a finite verb is 'independent', 'dependent', 'direct quote' (occurring
    in directly quoted speech, e.g. "est" in `"Tuum est," inquit,`), or
    'aside' (a verbal expression that interrupts the surrounding syntax,
    e.g. "dixerim" in "pace dixerim deum"); an infinitive anchoring an
    indirect statement is always 'indirect statement'. syntax_model.md
    doesn't specify a dedicated syntactic_type value for participles --
    this codebase's convention is to use 'dependent' for a predicate
    participle's verbal expression, since a circumstantial participle /
    ablative absolute functions like a subordinate clause; flag it if you
    intended something else."""
 
    id: str = Field(
        description=(
            "The token id (from the input `tokens` list) of the finite verb, "
            "infinitive, or predicate-sense participle that anchors this "
            "verbal expression. For a compound perfect/pluperfect passive or "
            "future-infinitive form (participle + a form of *sum*), use the id "
            "of the form of *sum*."
        )
    )
    syntactic_type: Literal[
        "independent", "dependent", "direct quote", "aside", "indirect statement"
    ] = Field(
        description=(
            "For a finite verb: 'independent' (main/principal), 'dependent' "
            "(subordinate/secondary), 'direct quote' (occurring in directly "
            "quoted speech), or 'aside' (interrupts the surrounding syntax). "
            "For an infinitive anchoring an indirect statement: 'indirect "
            "statement'. For a predicate-sense participle: 'dependent' (this "
            "codebase's convention; syntax_model.md doesn't specify)."
        )
    )
    semantic_type: Literal[
        "transitive active", "transitive passive", "intransitive", "linking verb"
    ] = Field(description="The verb's semantic/voice type.")
 
 
# The relation labels documented in syntax_model.md ("Token-level table of
# dependencies"). Keep relationship1 and relationship2 restricted to the
# same set of labels. relation2/relationship2 is usually an overflow slot,
# used only when relation1/relationship1 is already occupied by something
# else (e.g. a relative pronoun that is also a clause's subject) --
# "coordinating conjunction" is the one exception: a coordinating
# conjunction genuinely uses BOTH relation1 and relation2 at once, one for
# each half of the pair it joins, with relationship1 AND relationship2 both
# set to "coordinating conjunction" (see that value's own note below).
#
# "auxiliary", "predicate", "adjectival", "genitive", "dative", and
# "ablative" were added when syntax_model.md grew its noun-relations
# section and the participle/auxiliary rules for compound verb forms.
# "direct quote" and "aside" link a direct-quote or aside verbal
# expression back to the verb of the clause it interrupts. "circumstantial
# participle" and "ablative absolute" were added for participial verbal
# expressions: the participle points to the noun/pronoun it agrees with
# via "circumstantial participle"; if that noun doesn't otherwise fit into
# the surrounding clause (a true ablative absolute), the noun points back
# out to the main verb via "ablative absolute" instead of taking a normal
# noun relation. "coordinating conjunction" joins a pair of nouns,
# adjectives, prepositional phrases, or verbal expressions: the conjunction
# has BOTH relation1 -> the first joined token's id and relation2 -> the
# second's, both labelled "coordinating conjunction" -- except when the
# conjunction opens a new sentence with no explicit token to its left to
# pair with, in which case only relation1/relationship1 is set (see
# latin_syntax_dspy.py's docstring for the full set of cases, including the
# word-order caveat and the "et" adverb-vs-conjunction ambiguity).
RelationLabel = Literal[
    "unit verb",
    "subordinating conjunction",
    "relative pronoun",
    "subject",
    "direct object",
    "predicate",
    "agent",
    "auxiliary",
    "object of preposition",
    "adverbial",
    "attributive",
    "adjectival",
    "genitive",
    "dative",
    "ablative",
    "direct quote",
    "aside",
    "circumstantial participle",
    "ablative absolute",
    "coordinating conjunction",
]
 
 
class TokenAnalysis(BaseModel):
    """One entry per token in the dependency graph (syntax_model.md,
    'Token-level table of dependencies'). Per syntax_model.md's 'Incomplete
    status' section, not every token will have a relation -- leave the
    relatedtoken*/relationship* fields unset when none of the documented
    relations apply."""
 
    id: str = Field(description="Must match the id of the corresponding entry in the input `tokens` list.")
    token: str = Field(description="The token's surface text; should match the `text` of the input token with this id.")
    tokentype: Literal[
        "lexical", "enclitic", "punctuation", "numeral", "praenomen", "abbreviation"
    ] = Field(
        description=(
            "'praenomen' is specifically an abbreviated Roman first name "
            "(e.g. 'M.' for Marcus), including its period; 'abbreviation' is "
            "any other abbreviation, including its period (e.g. 'f.' for "
            "filius, 'cos.' for consul) -- syntax_model.md's tokenization "
            "section documents these as two distinct token types, not one."
        )
    )
 
    lemma: Optional[str] = Field(default=None, description="Dictionary headword, for lexical tokens. Omit for punctuation.")
    verbalunitid: Optional[str] = Field(
        default=None,
        description="If this token anchors a verbal expression in `verbalunits`, repeat its own id here; otherwise omit.",
    )
 
    relatedtoken1: Optional[str] = Field(
        default=None,
        description=(
            "Token id this token relates to (primary relation). For an "
            "INDEPENDENT verb's own 'unit verb' relation, use the special "
            "sentinel string 'root' instead of a token id -- 'root' is "
            "reserved and must never be assigned as an actual token's id."
        ),
    )
    relationship1: Optional[RelationLabel] = Field(default=None, description="The primary relation type, if any.")
 
    relatedtoken2: Optional[str] = Field(default=None, description="Token id this token relates to (secondary relation, used when relation1 is already occupied).")
    relationship2: Optional[RelationLabel] = Field(default=None, description="The secondary relation type, if any.")