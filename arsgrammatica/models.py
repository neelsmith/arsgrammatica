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
            "of the form of *sum*. For an implied/elided verbal expression (see "
            "TokenAnalysis's 'implied sum'/'continued discourse' tokentypes, "
            "IMPLIED_TOKENTYPES), use the new implied token's "
            "id instead -- an implied token always anchors its own verbal "
            "expression."
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
# expression back to the verb of the clause it interrupts; "indirect
# statement" does the same for an indirect-statement infinitive, linking
# it back to the verb that governs it (the verb of saying/thinking/
# perceiving it depends on) -- all three reuse their verbal expression's
# own syntactic_type value as the relationship label, the same convention.
# "circumstantial
# participle" and "ablative absolute" were added for participial verbal
# expressions: the participle points to the noun/pronoun it agrees with
# via "circumstantial participle"; if that noun doesn't otherwise fit into
# the surrounding clause (a true ablative absolute), the noun points back
# out to the main verb via "ablative absolute" instead of taking a normal
# noun relation. "apposition" links a noun in apposition back to the first
# noun it stands in apposition to (relatedtoken1 -> that first noun's id,
# relationship1 = "apposition") -- a genitive depending on either noun
# still gets its own separate "genitive" relation, pointing at whichever
# noun it actually depends on. "subordinating conjunction" is also reused,
# unchanged, for the interrogative word introducing an indirect question
# (treated as a kind of dependent clause) -- see the "verb of a dependent
# clause" note in latin_syntax_dspy.py's docstring; no new label was needed
# for that case. "coordinating conjunction" joins a pair of nouns,
# adjectives, prepositional phrases, or verbal expressions: the conjunction
# has BOTH relation1 -> the first joined token's id and relation2 -> the
# second's, both labelled "coordinating conjunction" -- except when the
# conjunction opens a new sentence with no explicit token to its left to
# pair with, in which case only relation1/relationship1 is set (see
# latin_syntax_dspy.py's docstring for the full set of cases, including the
# word-order caveat and the "et" adverb-vs-conjunction ambiguity).
# "complementary infinitive" is the only other new label: an infinitive
# that completes the sense of a governing verb like "volo"/"incipio"/
# "audeo"/"licet"/"decet" (e.g. "expugnare" completing "vellet") has
# relatedtoken1 -> that governing verb's id, relationship1 =
# "complementary infinitive" -- but is NOT itself a separate verbal
# expression (no `verbalunits` entry of its own), unlike an
# indirect-statement infinitive. Two other infinitive/gerund/gerundive
# uses need NO new label at all: an infinitive used as an ordinary noun
# (e.g. as a verb's subject or object) just takes the normal "subject"/
# "direct object"/etc. relation, like any other noun; a gerund (the oblique-
# case noun form of a verb) likewise takes whatever ordinary noun relation
# fits (most often "genitive"), and can itself govern an object or take an
# adverb the same way a finite verb or infinitive can; and a gerundive is
# simply treated as an ordinary adjective, agreeing with its noun via
# "adjectival". None of these three make their token a verbal-expression
# anchor either.
# "vocative" is the newest label: a noun in the vocative case relates to
# a VERB only (never to another noun, unlike "genitive"/"dative"/
# "ablative"/"accusative" above) -- relatedtoken1 -> the verb's id,
# relationship1 = "vocative". Example: in "Non est ita, domine, sed servi
# tui venerunt ut emerent cibos.", "domine" has relatedtoken1 -> "est",
# relationship1 = "vocative".
# "accusative" and "praenomen" are the two newest labels before that. "accusative"
# covers an accusative relation that ISN'T a direct object -- e.g. a bare
# accusative of place to which ("Romam" in "Romam venit", relatedtoken1 ->
# the verb "venit") or an accusative of extent modifying another noun
# rather than a verb (e.g. "milia" in "duo milia passuum iter fecerunt",
# relatedtoken1 -> "iter", the noun it qualifies) -- either a verb or
# another noun can be the target, same as "genitive"/"dative"/"ablative"
# below. "praenomen" links a `tokentype='praenomen'` token (an abbreviated
# Roman first name, e.g. "M." or "Sex.") to the lexical token spelling out
# the individual's own name it abbreviates/precedes: relatedtoken1 -> that
# lexical token's id, relationship1 = "praenomen". (A praenomen with no
# such name token to its own right -- e.g. the genitive filiation formula
# "L. f." for "Lucii filius", where "L." precedes only the abbreviation
# "f." rather than a lexical name -- has no target under this rule and is
# left unrelated, same as before.)
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
    "accusative",
    "vocative",
    "direct quote",
    "aside",
    "indirect statement",
    "circumstantial participle",
    "ablative absolute",
    "coordinating conjunction",
    "apposition",
    "complementary infinitive",
    "praenomen",
]
 
 
class TokenAnalysis(BaseModel):
    """One entry per token in the dependency graph (syntax_model.md,
    'Token-level table of dependencies'). Per syntax_model.md's 'Incomplete
    status' section, not every token will have a relation -- leave the
    relatedtoken*/relationship* fields unset when none of the documented
    relations apply.

    Most entries correspond 1:1 to an entry in the input `tokens` list. The
    exceptions are the two IMPLIED_TOKENTYPES values below: syntax_model.md's
    'understood or implied verbal expressions' section documents two
    DIFFERENT situations where a verbal expression exists grammatically but
    has no surface realization at all in the passage, and this codebase
    distinguishes them with two distinct tokentype values rather than one
    generic 'implied':

    - 'implied sum': an elided form of *sum* -- syntax_model.md's three
      elided-sum sub-cases (a bare predicate construction, a compound
      perfect passive/future infinitive missing its auxiliary, or the
      always-implied present participle of *sum*, which doesn't exist in
      Latin at all) all use this one value.
    - 'continued discourse': a governing verb of indirect discourse left
      unrepeated across several continuation clauses.

    For either, add a NEW entry here -- with a NEW id, not present in
    `tokens` -- rather than skipping the construction entirely; see
    latin_syntax_dspy.SyntaxAnalysis's docstring for the full rules and the
    id-naming convention."""

    id: str = Field(
        description=(
            "For an ordinary entry, must match the id of the corresponding "
            "entry in the input `tokens` list. For an implied token "
            "(tokentype in IMPLIED_TOKENTYPES -- 'implied sum' or "
            "'continued discourse'), a NEW id not used by any entry in "
            "`tokens` or elsewhere in this tokengraph -- see "
            "SyntaxAnalysis's docstring for the naming convention."
        )
    )
    token: Optional[str] = Field(
        default=None,
        description=(
            "The token's surface text; should match the `text` of the input "
            "token with this id. Leave as None ONLY for an implied token "
            "(tokentype 'implied sum' or 'continued discourse') -- one with "
            "no surface realization in the passage at all; every other "
            "tokentype must have real text."
        ),
    )
    tokentype: Literal[
        "lexical", "enclitic", "punctuation", "numeral", "praenomen", "abbreviation",
        "implied sum", "continued discourse",
    ] = Field(
        description=(
            "'praenomen' is specifically an abbreviated Roman first name "
            "(e.g. 'M.' for Marcus), including its period; 'abbreviation' is "
            "any other abbreviation, including its period (e.g. 'f.' for "
            "filius, 'cos.' for consul) -- syntax_model.md's tokenization "
            "section documents these as two distinct token types, not one. "
            "'implied sum' and 'continued discourse' each mark a token with "
            "NO surface realization at all (see this model's own docstring "
            "for the distinction) -- the only two tokentypes whose `token` "
            "field is None and whose `id` is not one of the input `tokens`' "
            "own ids."
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


# The two tokentype values (see TokenAnalysis's own docstring) that mark a
# token with no surface realization at all -- an elided form of *sum*, or
# an unrepeated governing verb of indirect discourse. Every other module
# that needs to ask "is this an implied token" (validate(), rendering.py,
# serialization.py, conftest.py's tokens_from_canned_answer()) checks
# membership in this set rather than hardcoding either string itself, so
# adding a third implied-token category later only needs a change here.
IMPLIED_TOKENTYPES = frozenset({"implied sum", "continued discourse"})