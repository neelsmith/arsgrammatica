
"""
Pydantic models describing the two structures from notes.md:
 
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
 
    `citation` is optional so this model still works unchanged for the
    older, citation-free callers (tokenizer.py's deterministic tokenize(),
    and any test fixture built from a bare passage string) -- it is only
    ever populated by the citation-aware segmentation stage
    (segmentation_dspy.py), which knows which CitedText source unit each
    token came from."""
 
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
    """One entry in the table of verbal expressions (notes.md, 'Table of
    verbal expressions'). Every finite verb is a verbal expression; so is
    an infinitive when it is part of indirect speech."""
 
    id: str = Field(
        description=(
            "The token id (from the input `tokens` list) of the finite verb or "
            "infinitive that anchors this verbal expression. For a compound "
            "perfect/pluperfect passive form (participle + sum), use the id of "
            "the form of *sum*."
        )
    )
    syntactic_type: Literal["independent", "dependent"] = Field(
        description="'independent' (main/principal) or 'dependent' (subordinate/secondary)."
    )
    semantic_type: Literal[
        "transitive active", "transitive passive", "intransitive", "linking verb"
    ] = Field(description="The verb's semantic/voice type.")
 
 
# The relation labels documented in notes.md ("Token-level table of
# dependencies"). Keep relationship1 and relationship2 restricted to the
# same set of labels, since the scheme uses relation2/relationship2 as an
# overflow slot when relation1/relationship1 is already occupied (e.g. a
# relative pronoun that is also a clause's subject).
RelationLabel = Literal[
    "unit verb",
    "subordinating conjunction",
    "relative pronoun",
    "subject",
    "direct object",
    "agent",
    "object of preposition",
    "adverbial",
    "attributive",
]
 
 
class TokenAnalysis(BaseModel):
    """One entry per token in the dependency graph (notes.md, 'Token-level
    table of dependencies'). Per notes.md's 'Incomplete status' section, not
    every token will have a relation -- leave the relatedtoken*/relationship*
    fields unset when none of the documented relations apply."""
 
    id: str = Field(description="Must match the id of the corresponding entry in the input `tokens` list.")
    token: str = Field(description="The token's surface text; should match the `text` of the input token with this id.")
    tokentype: Literal["lexical", "enclitic", "punctuation", "numeral", "praenomen"]
 
    lemma: Optional[str] = Field(default=None, description="Dictionary headword, for lexical tokens. Omit for punctuation.")
    verbalunitid: Optional[str] = Field(
        default=None,
        description="If this token anchors a verbal expression in `verbalunits`, repeat its own id here; otherwise omit.",
    )
 
    relatedtoken1: Optional[str] = Field(default=None, description="Token id this token relates to (primary relation).")
    relationship1: Optional[RelationLabel] = Field(default=None, description="The primary relation type, if any.")
 
    relatedtoken2: Optional[str] = Field(default=None, description="Token id this token relates to (secondary relation, used when relation1 is already occupied).")
    relationship2: Optional[RelationLabel] = Field(default=None, description="The secondary relation type, if any.")