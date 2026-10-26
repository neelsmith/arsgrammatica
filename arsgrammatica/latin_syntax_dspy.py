"""
DSPy program that analyzes the syntax of a Latin passage according to the scheme documented in the Quarto "Concepts" pages (quarto/concepts/tokens.qmd, verbalunits.qmd, syntactic-analysis.qmd): a list of verbal expressions, plus a graph of syntactic relations among tokens.
 
This module covers only the analysis stage:
  1. SentenceAnalysis -- a dspy.Signature that takes a passage plus its pre-segmented token list and produces `verbalunits` and `tokengraph`, using the ids handed to it.
  2. validate()   -- a light sanity check that every id the LM refers to in its output actually exists in the input token list, so malformed output is easy to spot.
 
Tokens are no longer produced here. The old deterministic tokenizer.py has
been retired; tokens now come from segmentation_dspy.py's LLM-driven,
citation-aware segmentation stage. See pipeline.py for the module that ties
the two stages together, including its analyze_string() convenience
wrapper (the replacement for the function that used to live in this file).
 
Run this file directly for a quick smoke test against the configured LM:
    python latin_syntax_dspy.py
 
For tests that don't need network access to the school proxy, see the
`tests/` directory, which drives this signature with dspy's DummyLM.
"""
 
from typing import List
 
import dspy
 
from .models import IMPLIED_TOKENTYPES, Token, VerbalExpression, TokenAnalysis
 
 
# ---------------------------------------------------------------------------
# Signature
# ---------------------------------------------------------------------------
 
class SentenceAnalysis(dspy.Signature):
    """Analyze the syntax of a passage of Latin according to the
    arsgrammatica scheme, producing (1) a list of verbal expressions and (2)
    a graph of syntactic relations among the tokens.

    (1) VERBAL EXPRESSIONS. Every syntactic feature is organized around
        explicit or implicit verbal ideas. Four constructions are verbal
        expressions:
        - every finite verb. A compound form of the perfect passive system
          (participle + a form of 'sum') is ONE verbal expression, anchored
          on the participle; the form of 'sum' is its auxiliary.
        - an infinitive that is the verb of an indirect statement. A
          complementary infinitive, or an infinitive used as a noun, is NOT
          a verbal expression. A compound infinitive (e.g. future
          "facturum ... fuisse") is anchored on the participle.
        - a participle with a circumstantial sense (e.g. "Anco regnante",
          'while Ancus was reigning'), but NOT a purely attributive
          participle (e.g. "consentiens laus", 'universal praise', which is
          simply 'adjectival'). When it is unclear whether a participle is
          attributive or circumstantial, PREFER the circumstantial reading.
        - every gerundive (e.g. "ad pacem faciendam"). A gerundive + 'sum'
          (passive periphrastic, e.g. "Carthago delenda est") is a compound
          form anchored on the gerundive. The GERUND (e.g. "ars dicendi") is
          a noun, NOT a verbal expression.

        Give each verbal expression the id of its anchor token and one
        syntactic type:
        - 'independent': a main verb, syntactically complete by itself.
        - 'dependent': a verb introduced by a subordinating word (a
          subordinating conjunction, or a word introducing an indirect
          question) or by a relative pronoun.
        - 'direct quote': the top-level verb of directly quoted speech (the
          verb that would be 'independent' if the quotation stood alone).
          Clauses subordinate to it inside the quotation are typed normally
          (e.g. 'dependent').
        - 'aside': a verb whose clause interrupts the syntax of the
          surrounding sentence (e.g. "dixerim" in "equidem -- pace dixerim
          deum -- eos ... esse spero").
        - 'parataxis': a subjunctive verb governed WITHOUT any subordinating
          word by a verb of necessity, wishing, preference or command (e.g.
          oportet, necesse est, volo, peto, precor, imperative fac): "videam"
          in "Precor eam videam", "scribas" in "Tu velim ad me scribas".
        - 'indirect statement': an infinitive of indirect speech.
        - 'circumstantial participle': a circumstantial participle.
        - 'gerundive': an attributive gerundive (one NOT in a compound with
          'sum'). A gerundive + 'sum' takes the type of its context instead
          ('independent', 'dependent', 'indirect statement', ...).

    (2) THE SYNTAX GRAPH. Give every token a list of `relations`; each
        relation has `related` (the id of a token, of an implied token, or
        the reserved value 'root') and `relationship` (one of the labels
        below). Every non-punctuation token gets at least one relation;
        punctuation gets none. A token may have SEVERAL relations (e.g. a
        relative pronoun; a coordinating word joining two items) -- list one
        relation per edge. The order of a token's relations does not matter.

        Constructions of verbal expressions:
        - 'unit verb': the anchor of an independent verbal expression ->
          'root' (never use 'root' as a token id). The anchor of a dependent
          clause -> its subordinating word or relative pronoun.
        - 'auxiliary': the form of 'sum' in a compound form (perfect passive
          system, compound infinitive, gerundive + 'sum') -> the participle
          / infinitive / gerundive, which is the target of every other
          relation into the verbal expression (subject, agent, ...). E.g.
          "urbs condita est": est -> condita 'auxiliary'; condita -> 'root'.
          Also for impersonal passives ("ventum erat").
        - 'direct quote': the top-level verb of a direct quotation -> the
          verb introducing the quotation (e.g. dedico -> inquit).
        - 'aside': the verb of an interrupting clause -> the verb of the
          interrupted clause.
        - 'parataxis': a paratactic subjunctive -> its governing verb.
        - 'indirect statement': the indirect-statement infinitive -> the
          governing verb of saying/thinking/perceiving (e.g. esse -> dixit).
          Its accusative subject is its 'subject'.
        - 'circumstantial participle': the participle -> the substantive it
          agrees with (e.g. adveniens -> vir).
        - 'gerundive': an attributive gerundive -> the substantive it agrees
          with (e.g. faciendam -> pacem; faciendum -> pontem in "pontem
          faciendum curavit").

        Other constructions with verbs:
        - 'complementary infinitive': an infinitive completing a verb like
          volo, possum, incipio, audeo -> that verb. It can still take its
          own objects and adverbs.

        A-A-T (Agent-Action-Target) relations:
        - 'subject': the grammatical subject -> its verbal expression.
        - 'direct object': the direct object -> its verb.
        - 'agent-ablative': the preposition a/ab expressing agency with a
          passive verb -> the verb (its noun is 'object of preposition' ->
          a/ab). E.g. "urbs a Romulo condita est": a -> condita.
        - 'agent-dative': a dative of agent -> the verb. Used regularly with a
          gerundive + 'sum' (explicit or implied: "Caesari omnia erant
          agenda": Caesari -> agenda), and sometimes with a compound perfect
          passive ("res praeterita nobis est": nobis -> praeterita). A dative
          with an attributive gerundive is plain 'dative'.
        - 'predicate', in four uses:
          1. the predicate of a linking verb -> the verb ("Lucumo ... filius
             erat": filius -> erat);
          2. a substantive giving the role or state in which the subject acts
             -> the verb ("Lucumo superfuit ... heres": heres -> superfuit);
          3. after verbs of naming, making, thinking, judging, showing
             (appello, voco, creo, facio, habeo, iudico, puto, aestimo, se
             praebere, reddo), a substantive describing the direct object ->
             THE DIRECT OBJECT ("Ciceronem consulem creaverunt": consulem ->
             Ciceronem);
          4. the passive of use 3 -> the passive verb ("Cicero consul creatus
             est": consul -> creatus).

        Case constructions (purely syntactic: do NOT distinguish semantic
        subtypes such as possessive vs. partitive genitive):
        - 'genitive', 'dative', 'accusative', 'ablative': a substantive in
          that case depending on a verb or another substantive, when no more
          specific relation applies -> that verb or substantive. 'accusative'
          is for accusatives that are NOT direct objects (e.g. "Romam venit":
          Romam -> venit; "duo milia passuum iter": milia -> iter). In "opus
          est" + ablative, the ablative -> opus.
        - 'vocative': a vocative -> the verb of its clause.

        Substantives from verbal roots: an infinitive used as a noun, or a
        gerund, takes the same relations as any substantive ("dolere malum
        est": dolere -> est 'subject'; "ars dicendi": dicendi -> ars
        'genitive'), and can still take its own objects and adverbs.

        Adverbial and adjectival expressions:
        - 'adverbial': an adverb, or a preposition heading an adverbial
          phrase, -> the token it qualifies, whether verbal, substantive or
          adjectival.
        - 'adjectival': an adjective (or attributive participle, or numeral
          such as XXV) -> the substantive it describes; also a preposition
          heading a phrase that describes a substantive ("nuntius victoriae
          ad Cannas": ad -> victoriae). An adjective used as a substantive
          takes substantive relations instead.
        - 'object of preposition': the substantive governed by a preposition
          -> the preposition, whatever its case.

        Special substantive relations:
        - 'ablative absolute': in an ablative absolute, the ablative
          substantive -> the governing verb (its participle is a
          'circumstantial participle' -> the substantive).
        - 'apposition': an appositive -> the substantive it stands in
          apposition to (the first substantive is constructed normally).
        - 'praenomen': a praenomen used with a nomen or cognomen -> that
          name (e.g. "Sp. Nautius": Sp. -> Nautius). A praenomen standing
          alone is treated like any other substantive (e.g. "M. Agrippa L.
          f. cos.": L. -> f. 'genitive'; f. and cos. -> Agrippa
          'apposition').

        Coordinating and subordinating words:
        - 'coordinating word': a connective (e.g. autem, igitur, sed, nam,
          ceterum) joining a verbal expression to a preceding SENTENCE ->
          that verb (one relation only). A coordinating word (et, aut,
          -que, ...) joining a pair of items -> EACH of the two items (two
          relations). When it joins verbal expressions, relate it to the
          two verbs, even when it is attached to some other word (e.g.
          "Hermionenque ... adduxit": que -> noluit and que -> adduxit). In
          a series "A et B et C", each connector -> the item before and the
          item after it. In "et A et B et C", the first connector -> A only;
          the rest -> the items on either side. Each joined item keeps its
          own normal relation as well. When et means 'even, also', it is
          'adverbial'.
        - 'subordinating word': a subordinating conjunction (ut, cum, ne,
          quoniam, quod, si, ...) or a word introducing an indirect question
          -> the verb of the governing clause; the dependent verb -> the
          subordinating word as 'unit verb'. Distinguish interrogatives
          introducing indirect questions from relative pronouns.
        - 'relative pronoun': a relative pronoun -> its antecedent, PLUS a
          second relation giving its function in its own clause (e.g.
          'subject', 'direct object', 'object of preposition'); the verb of
          the relative clause -> the relative pronoun as 'unit verb'.

    (3) IMPLIED TOKENS. When something exists grammatically but has no
        written form, add a NEW entry to `tokengraph` with a new id, no
        `token` text, and one of three tokentypes:
        - 'implied sum': an elided form of 'sum'.
          - In a bare predicate construction ("omnia praeclara rara") it
            anchors its own verbal expression (here 'independent'), and the
            subject and predicate relate to it.
          - There is no present participle of 'sum', so an ablative absolute
            with a predicate noun ("Agrippa Menenio P. Postumio consulibus")
            implies one: it anchors a 'circumstantial participle' verbal
            expression and relates to the names it agrees with as
            'circumstantial participle'.
          - When it is the missing auxiliary of a compound form ("consules
            facti" for "facti sunt") it does NOT anchor a verbal expression:
            the participle does, and the implied token -> the participle as
            'auxiliary'.
        - 'implied verb': an understood repeated verb, which anchors its own
          verbal expression with the type the written verb would have. E.g.
          a verb shared by parallel clauses ("ut famam ... exspectatio,
          exspectationem ... adventus admiratioque superaret": superaret
          belongs to the first clause; an implied verb, 'dependent' -> ut,
          serves the second), or a governing verb of speaking omitted
          throughout a passage of indirect discourse (the infinitives ->
          the implied verb as 'indirect statement'; the implied verb is
          'independent' -> 'root').
        - 'implied substantive': an unexpressed antecedent that a relative
          pronoun or participle depends on. It is not a verbal expression.
          E.g. "quem dii amant adolescens moritur": an implied substantive
          -> moritur 'subject', and quem -> it 'relative pronoun'. Add one
          ONLY when another token needs it to relate to: an omitted subject
          is normal in Latin and needs no implied token otherwise. A
          participle used substantively ("sapienti sat est") needs none.
        Every implied token gets its own relations exactly like a written
        word (e.g. an implied 'sum' anchoring an independent clause ->
        'root' as 'unit verb').
        Naming: append '_implied' to the id of the last real token before
        the place where the implied word would stand (or to the first token's
        id, if it would stand first); for more than one at the same place,
        append '2', '3', ... ('t5_implied', 't5_implied2'). Place the entry
        among the tokens of its own clause.

    TOKEN TYPES. Keep the tokentype given by segmentation where possible:
    'praenomen' (a Roman first name, abbreviated with its period or not,
    e.g. "M.", or "Agrippa" in "Agrippa Menenio"), 'abbreviation' (any
    other abbreviation with its period, e.g. "f.", "cos."), 'punctuation',
    'enclitic' (que, ve, ne, -cum in nobiscum, ...), 'numeral' (written
    with numerals, e.g. "XXV"; "decem" is 'lexical'), 'lexical' (any other
    word), plus the three implied types above.

    FLAGGING AMBIGUITY: when the passage genuinely supports more than one
    defensible reading of a specific construction, say so in your
    reasoning: name the token(s), the alternative you considered, and why
    you chose as you did. Do not pad your reasoning with hedges about
    routine analysis you are confident in.
    """

    passage: str = dspy.InputField(desc="The Latin passage to analyze, exactly as written.")
    tokens: List[Token] = dspy.InputField(
        desc="Pre-segmented tokens of the passage, in order, with fixed ids. Reference these ids in your output; only implied tokens get new ids."
    )
    verbalunits: List[VerbalExpression] = dspy.OutputField(
        desc="One entry per verbal expression (explicit or implied) in the passage."
    )
    tokengraph: List[TokenAnalysis] = dspy.OutputField(
        desc=(
            "One entry per token in `tokens`, in the same order, with its "
            "type and its list of relations -- PLUS one entry for each "
            "implied token you add, placed among the tokens of its own clause."
        )
    )


analyze = dspy.ChainOfThought(SentenceAnalysis)
 
 
# ---------------------------------------------------------------------------
# Runner + validation
# ---------------------------------------------------------------------------
 
def validate(tokens: List[Token], result) -> List[str]:
    """Check an analysis for referential integrity. Returns a list of
    human-readable problem descriptions (empty if clean).

    Checks:

    - every tokengraph entry is either one of `tokens` (by id) or a
      well-formed implied token (tokentype in IMPLIED_TOKENTYPES, a NEW id
      not in `tokens`, and no surface text); conversely only an implied
      token may omit its text;
    - every relation points at a known node: a token id, an implied
      token's id, or the reserved value 'root';
    - 'root' is only used as the target of a 'unit verb' relation, and is
      never itself a token id;
    - every verbal expression is anchored on a known token.

    This is purely structural: it never judges whether the analysis is
    linguistically correct."""
    valid_ids = {t.id for t in tokens}
    problems = []

    if "root" in valid_ids:
        problems.append(
            "token id 'root' is reserved as the target of an independent "
            "verb's 'unit verb' relation and must not be assigned to an "
            "actual token"
        )

    implied_ids = {tok.id for tok in result.tokengraph if tok.tokentype in IMPLIED_TOKENTYPES}
    known_ids = valid_ids | implied_ids

    for tok in result.tokengraph:
        if tok.tokentype in IMPLIED_TOKENTYPES:
            if tok.id in valid_ids:
                problems.append(
                    f"tokengraph entry {tok.id!r} is tokentype={tok.tokentype!r} but "
                    "reuses an id already in the input `tokens` list -- an "
                    "implied token must use a new id"
                )
            if tok.token is not None:
                problems.append(
                    f"tokengraph entry {tok.id!r} is tokentype={tok.tokentype!r} but "
                    f"has a non-None token value {tok.token!r} -- an implied "
                    "token's text must be left unset"
                )
        else:
            if tok.id not in valid_ids:
                problems.append(f"tokengraph entry has unknown id {tok.id!r}")
            if tok.token is None:
                allowed = "/".join(repr(t) for t in sorted(IMPLIED_TOKENTYPES))
                problems.append(
                    f"tokengraph entry {tok.id!r} has token=None but "
                    f"tokentype={tok.tokentype!r} -- only {allowed} may "
                    "omit surface text"
                )
        for relation in tok.relations:
            target = relation.related
            if target == "root":
                if relation.relationship != "unit verb":
                    problems.append(
                        f"token {tok.id!r} relates to 'root' as "
                        f"{relation.relationship!r} -- 'root' may only be the "
                        "target of a 'unit verb' relation"
                    )
            elif target not in known_ids:
                problems.append(
                    f"token {tok.id!r} relation {relation.relationship!r} -> "
                    f"{target!r} is not a known token id"
                )

    for vu in result.verbalunits:
        if vu.id not in known_ids:
            problems.append(f"verbal expression id {vu.id!r} is not a known token id")

    return problems


def print_analysis(tokens: List[Token], result):
    print("Tokens:")
    for t in tokens:
        print(f"  {t.id:>4}  {t.text}")

    print("\nVerbal expressions:")
    for vu in result.verbalunits:
        print(f"  id={vu.id}  syntactic_type={vu.syntactic_type}")

    print("\nToken graph:")
    for tok in result.tokengraph:
        rels = [f"{r.relationship} -> {r.related}" for r in tok.relations]
        rel_str = "; ".join(rels) if rels else "-"
        vu_str = f" [verbal unit {tok.verbalunitid}]" if tok.verbalunitid else ""
        token_str = tok.token if tok.token is not None else f"({tok.tokentype})"
        print(f"  {tok.id:>4}  {token_str:<15} type={tok.tokentype:<11} lemma={tok.lemma or '-':<15} {rel_str}{vu_str}")
