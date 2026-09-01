"""
DSPy program that analyzes the syntax of a Latin passage according to the scheme documented in syntax_model.md: a table of verbal expressions, plus a token-level dependency graph.
 
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
          at all). Use 'dependent' as its syntactic type. When it's
          genuinely uncertain whether a given participle is attributive or
          predicate/circumstantial, PREFER the circumstantial reading --
          treat it as its own verbal expression rather than folding it into
          an attributive relation. Example: in "ille moriens, cum sciret
          sagittas hydrae Lernaeae felle tinctas quantam uim haberent
          ueneni, sanguinem suum exceptum Deianirae dedit", both "moriens"
          (agreeing with "ille") and "tinctas" (agreeing with "sagittas")
          are treated as circumstantial participles, each anchoring its own
          verbal expression, rather than as ordinary attributive
          adjectives.
 
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
          Indirect questions are treated as a kind of dependent clause: the
          interrogative word introducing one (e.g. "quanta" in "Theseus
          audit quanta calamitate ciuitas afficeretur") is treated the same
          way as a subordinating conjunction -- it has relatedtoken1 -> the
          id of the verb it introduces (here "audit"), relationship1 =
          'subordinating conjunction' (no separate label for this case) --
          while the dependent verb itself ("afficeretur") has relatedtoken1
          -> the interrogative word's id ("quanta"), relationship1 = 'unit
          verb', exactly like any other dependent clause.
        - indirect statement (governing verb): an infinitive anchoring an
          indirect-statement verbal expression ALSO has relatedtoken1 ->
          the id of the verb that governs the indirect statement (the verb
          of saying/thinking/perceiving it depends on), relationship1 =
          'indirect statement' -- matching its own syntactic type, the same
          convention 'direct quote' and 'aside' verbal expressions use
          below. There's no separate subordinating-word token to point at
          first (a Latin accusative-and-infinitive construction has no
          equivalent of English 'that'), so the infinitive points directly
          at its governing verb, rather than via a conjunction/pronoun
          intermediary the way a dependent finite verb's 'unit verb'
          relation does. In a compound future-infinitive form (participle +
          a form of 'sum'), this relation belongs on the form of 'sum' that
          anchors the verbal expression, same as any other relation into it.
        - complementary infinitive: an infinitive that completes the sense
          of a governing verb like 'volo', 'incipio', 'audeo', 'licet', or
          'decet' (rather than reporting indirect speech) has relatedtoken1
          -> the id of that governing verb, relationship1 = 'complementary
          infinitive'. Unlike an indirect-statement infinitive, this does
          NOT make the infinitive its own verbal expression -- it gets no
          `verbalunits` entry of its own; the governing verb is still the
          only verbal expression here. Example: in "Amphion...cum templum
          Apollinis expugnare vellet...", "expugnare" completes "vellet"
          (relatedtoken1 -> "vellet", relationship1 = 'complementary
          infinitive'); "templum" is still "expugnare"'s own direct object,
          exactly as if "expugnare" were a finite verb.
        - infinitive used as a noun: an infinitive can also function as an
          ordinary noun -- most often a verb's subject or object -- rather
          than anchoring an indirect statement or completing another verb.
          Treat it exactly like any other noun in that role: relatedtoken1
          -> the verb it's the subject/object of, relationship1 = 'subject'
          or 'direct object' as appropriate (no dedicated label, and again
          no `verbalunits` entry of its own). Example: in "dolere malum
          est", "dolere" has relatedtoken1 -> "est", relationship1 =
          'subject'. Like any verbal form, an infinitive used this way can
          still take its own object or adverb, related to it the same way
          they'd relate to a finite verb.
        - gerunds and gerundives: a gerundive is simply an adjective --
          treat it exactly like one (relatedtoken1 -> the noun it agrees
          with, relationship1 = 'adjectival'; see 'adjectival' below).
          Example: in "...ad sacrum faciendum", "faciendum" (the gerundive)
          has relatedtoken1 -> "sacrum", relationship1 = 'adjectival'. A
          gerund is a noun -- the oblique-case form a verb takes where an
          infinitive would be needed in the nominative -- so relate it like
          any other noun (most often 'genitive'); it can still take its own
          object or adverb, related to it the same way they'd relate to a
          finite verb or infinitive. Example: in "ars bene disserendi",
          "disserendi" (the gerund) has relatedtoken1 -> "ars",
          relationship1 = 'genitive', and "bene" (the adverb modifying it)
          has relatedtoken1 -> "disserendi", relationship1 = 'adverbial'.
          Neither a gerund nor a gerundive is a verbal expression in its
          own right -- no dedicated label, no `verbalunits` entry.
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
          'coordinating conjunction'. IMPORTANT: when the conjunction joins
          two independent verbs, BOTH still get their own `verbalunits`
          entry and their own relatedtoken1 = 'root'/relationship1 = 'unit
          verb' -- this doesn't change just because one of them (usually
          the second) also governs further subordinate structure of its
          own (a dependent clause, an indirect statement, etc). A verb
          that governs an indirect statement or introduces a further
          clause is NOT thereby demoted to a mere "framing verb" for what
          follows -- it is still, independently, one of the two
          coordinated root verbs, and needs its own entry exactly like the
          first one. Example: in "...dedit et id philtrum esse dixit.",
          dedit and dixit are both independent verbs coordinated by et;
          dixit ALSO governs the indirect statement anchored at esse
          ('id philtrum esse'), but that does not exempt dixit itself from
          getting relatedtoken1 = 'root', relationship1 = 'unit verb', and
          its own entry in `verbalunits` -- exactly as if it stood alone.
        - coordinating conjunction, repeated as a series: a conjunction
          like 'et' or 'aut' can also be repeated before EVERY item of a
          series of three or more (polysyndeton, e.g. 'et...et...et'),
          not just used once between a pair. Annotate this differently
          from the simple pairwise case above. Every connector's own
          relatedtoken1 -> the id of the item it immediately introduces
          (a real noun, adjective, prepositional phrase, or verbal
          expression anchor -- NEVER another connector), relationship1 =
          'coordinating conjunction', exactly as in the pairwise case.
          relatedtoken2 is what differs: the FIRST connector's
          relatedtoken2 -> the id of the NEXT (second) connector, while
          every connector AFTER the first has relatedtoken2 -> the id of
          the PRECEDING connector instead (not the following one).
          relationship2 = 'coordinating conjunction' for all of them,
          same as relationship1 -- this still isn't an overflow slot.
          Each connected item ALSO keeps its own ordinary relation to the
          rest of the sentence (subject, ablative, direct object, or
          whatever fits), completely independent of this chain -- the
          coordinating-conjunction relation only links a connector to the
          item it introduces and to its neighboring connector(s); it
          never substitutes for that item's own relation to whatever
          governs it. Example: in "Tarquinius et assiduitate et
          varietate et magnificentia omnes antecessit", the first et has
          relatedtoken1 -> assiduitate and relatedtoken2 -> the second
          et; the second et has relatedtoken1 -> varietate and
          relatedtoken2 -> the FIRST et (not the third); the third et has
          relatedtoken1 -> magnificentia and relatedtoken2 -> the second
          et. assiduitate, varietate, and magnificentia each ALSO have
          their own relatedtoken1 -> antecessit, relationship1 =
          'ablative', same as any other ablative -- unaffected by which
          connector introduces them.
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
          'ablative absolute'. Sometimes there is no noun or pronoun at
          all for the participle to agree with -- most often when it
          agrees with a governing verb's own unexpressed subject. Do NOT
          leave the participle's relatedtoken1 pointing at the verb
          directly in that case (that would misrepresent the participle as
          relating straight to the verb, the way an ablative-absolute noun
          does): instead add a new tokentype='implied subject' token (see
          (3) below) standing in for the missing noun, give IT the normal
          'subject' relation into the verb, and have the participle relate
          to THIS new token via 'circumstantial participle' exactly as it
          would to a real one.
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
        - genitive / dative / ablative / accusative: a noun in the
          genitive, dative, ablative, or accusative case that depends on a
          verb or another noun -- and isn't already covered by a more
          specific relation above (subject, direct object, object of
          preposition, ablative absolute, etc) -- has relatedtoken1 -> the
          id of the verb or noun it depends on, relationship1 = the
          matching case name ('genitive', 'dative', 'ablative', or
          'accusative'). These are purely syntactic (case-function) labels,
          not semantic ones -- don't distinguish e.g. possessive vs.
          partitive genitive. 'accusative' specifically covers an
          accusative relation that ISN'T a direct object: a bare
          accusative of place to which (e.g. "Romam" in "Romam venit",
          relatedtoken1 -> "venit", even though "venit" is intransitive)
          or an accusative of extent that modifies another NOUN rather
          than a verb (e.g. "milia" in "duo milia passuum iter fecerunt",
          relatedtoken1 -> "iter", the noun it qualifies, not "fecerunt").
          The idiomatic construction 'opus est' + an ablative is a special
          case worth noting for 'ablative': the ablative token relates to
          "opus" itself, not to "est" -- e.g. in "Collatinus negat verbis
          opus esse", "verbis" has relatedtoken1 -> "opus", relationship1 =
          'ablative'.
        - vocative: a noun in the vocative case (direct address) has
          relatedtoken1 -> the id of the verb of the clause it's addressed
          within, relationship1 = 'vocative'. Unlike 'genitive'/'dative'/
          'ablative'/'accusative' above, a vocative relates to a verb
          only, never to another noun. Example: in "Non est ita, domine,
          sed servi tui venerunt ut emerent cibos.", "domine" has
          relatedtoken1 -> "est", relationship1 = 'vocative'.
        - apposition: when one noun stands in apposition to another, the
          appositive has relatedtoken1 -> the id of the first (the noun it
          restates or further identifies), relationship1 = 'apposition'. A
          genitive depending on either noun still gets its own ordinary
          'genitive' relation, pointing at whichever noun it actually
          depends on -- apposition doesn't change that. Example: in
          "Neptunus et Aegeus Pandionis filius...cum Aethra Pitthei
          filia...", "filius" is in apposition to "Aegeus" (relatedtoken1
          -> "Aegeus", relationship1 = 'apposition'), and "Pandionis" (the
          genitive depending on "filius") has relatedtoken1 -> "filius",
          relationship1 = 'genitive' -- and likewise "filia" is in
          apposition to "Aethra", with "Pitthei" as a genitive depending on
          "filia".
        - praenomen: a token of tokentype 'praenomen' (an abbreviated Roman
          first name, e.g. "M." or "Sex.") has relatedtoken1 -> the id of
          the LEXICAL token spelling out the individual's own name that it
          abbreviates/precedes, relationship1 = 'praenomen'. Example: in
          "Sex. Tarquinius inscio Collatino...venit", "Sex." has
          relatedtoken1 -> "Tarquinius", relationship1 = 'praenomen'. If
          there is no such lexical name token to relate to -- e.g. the
          genitive filiation formula "L. f." ("Lucii filius", 'son of
          Lucius'), where "L." precedes only the abbreviation "f." rather
          than a lexical name -- leave it unrelated, same as any other
          token with no relation of these kinds.
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
        kinds -- not every token will have one (e.g. a bare accusative of
        place isn't covered). Use only the token ids given in
        the input `tokens` list, the sentinel 'root', or a NEW id you
        create for an implied token (see below), in your output; never
        invent an id for anything else.

    (3) implied/elided tokens. `arsgrammatica` recognizes three DIFFERENT
        situations where something exists grammatically but has no surface
        realization in the passage at all -- rather than skip these, add a
        NEW entry to `tokengraph` with: a brand-new id, not used by any
        entry in `tokens` or elsewhere in your own output (see the naming
        rule below); the matching tokentype below; and no `token` value
        (leave it unset/None) -- these go together, and 'implied sum',
        'continued discourse', and 'implied subject' are the ONLY three
        tokentype values whose id isn't one of `tokens`' own ids and whose
        `token` is empty. Two of the three (`implied sum`, `continued
        discourse`) stand in for a missing VERBAL expression, and so also
        need a matching new entry in `verbalunits`, exactly like any other
        verbal expression; the third (`implied subject`) stands in for a
        missing NOUN or pronoun instead, and never gets a `verbalunits`
        entry of its own.

        - tokentype 'implied sum': an elided present of 'sum' ('to be').
          Three sub-cases, all using this same tokentype:
            - a bare predicate construction (subject + predicate noun/
              adjective, no verb at all): the implied token anchors a
              verbal expression classified 'independent' (or 'dependent',
              if the elided-'sum' clause is itself subordinate) and
              'linking verb'; the subject and predicate each relate to it
              exactly as they would to any linking verb ('subject' /
              'predicate'). Example: "omnia praeclara rara" ('all splendid
              things [are] rare') has an implied token anchoring an
              'independent'/'linking verb' expression, with "omnia" (its
              own 'praeclara' adjectival) as 'subject' and "rara" as
              'predicate'.
            - a compound perfect/pluperfect passive (or impersonal
              passive) with its auxiliary omitted (e.g. "consules facti"
              for "consules facti sunt"): the implied token stands in for
              the omitted form of 'sum' -- everything that would normally
              relate to that auxiliary (subject, the participle's own
              'auxiliary' relation, etc.) relates to the implied token
              instead, exactly as if the auxiliary had been written out.
            - the present participle of 'sum' does not exist in Latin at
              all, so an ablative-absolute-style predicate construction
              built on it (e.g. "Agrippa Menenio P. Postumio consulibus",
              '[when] Agrippa Menenius [and] Publius Postumius [were]
              consuls') is ALWAYS implied, never optional. Classify the
              implied token's verbal expression 'dependent' (this
              codebase's circumstantial-participle convention -- see
              VerbalExpression's own docstring) and 'linking verb'; relate
              it to its noun via 'circumstantial participle' exactly like
              any other circumstantial participle.
        - tokentype 'continued discourse': continuation of indirect
          discourse -- a long run of indirect statements can share one
          governing verb of speaking/thinking stated once, then omitted
          across several further coordinate statements. Add ONE implied
          token (tokentype 'continued discourse') for that omitted
          governing verb (syntactic type 'independent' unless the whole
          passage is itself subordinate, semantic type 'transitive active'
          unless context says otherwise), and give EACH of the governed
          infinitives its normal 'indirect statement' relation into it,
          exactly as if the verb had been repeated for each one.
        - tokentype 'implied subject': a participle's own antecedent (the
          noun/pronoun it agrees with, related via 'circumstantial
          participle' -- see that relation's own note above) can itself go
          unexpressed, most often when the participle agrees with a
          governing verb's own unexpressed subject. Rather than leaving
          the participle with no antecedent to point at (or, worse,
          pointing it straight at the verb, which would misrepresent it as
          an ablative absolute), add ONE implied token (tokentype 'implied
          subject') to stand in for the missing noun/pronoun. This implied
          token is NOT a verbal expression itself -- it gets no
          `verbalunits` entry -- it simply takes a normal 'subject'
          relation into the governing verb (relatedtoken1 -> the verb's
          id, relationship1 = 'subject'), exactly as if that subject had
          been written out as a real word. The participle then relates to
          THIS new token via 'circumstantial participle', exactly as it
          would to a real antecedent. Example: in "Recordatusque
          somniorum ait ad eos: Exploratores estis.", the participle
          "Recordatus" agrees with the unexpressed subject of "ait" -- add
          an implied token (tokentype 'implied subject') with relatedtoken1
          -> "ait"'s id, relationship1 = 'subject'; "Recordatus" then has
          relatedtoken1 -> that new implied token's id, relationship1 =
          'circumstantial participle' (and, since "Recordatus" is itself a
          predicate-sense participle, it ALSO anchors its own
          `verbalunits` entry, syntactic_type 'dependent', semantic_type
          matching its own transitivity -- unaffected by its antecedent
          being implied rather than real).

        Naming an implied token's id (all three tokentypes): append
        '_implied' to the id of the LAST real token in `tokens` that
        precedes where the elided word would have stood (or, if the elided
        word would come before every real token in the sentence, the FIRST
        real token's id instead). If more than one implied token is ever
        needed at the same position, append '2', '3', ... after '_implied'
        to keep them unique (e.g. 't5_implied', 't5_implied2'). Place the
        new `tokengraph` entry at the list position where the elided word
        would have appeared, among the tokens of its own clause -- this
        keeps it grouped with the rest of its verbal expression (or, for
        'implied subject', the clause of the verb it's the subject of) for
        anything that reads `tokengraph` in order.
    """
 
    passage: str = dspy.InputField(desc="The Latin passage to analyze, exactly as written.")
    tokens: List[Token] = dspy.InputField(
        desc="Pre-segmented tokens of the passage, in order, with fixed ids. Reference these ids in your output; do not create new ones."
    )
    verbalunits: List[VerbalExpression] = dspy.OutputField(
        desc="One entry per verbal expression (finite verb; infinitive used in indirect speech; or predicate-sense participle) in the passage."
    )
    tokengraph: List[TokenAnalysis] = dspy.OutputField(
        desc=(
            "One entry per token in `tokens`, in the same order, with its "
            "type and any relations -- PLUS one additional entry for each "
            "implied/elided token you add (see this signature's docstring), "
            "positioned where that token's clause falls in reading order."
        )
    )
 
 
analyze = dspy.ChainOfThought(SentenceAnalysis)
 
 
# ---------------------------------------------------------------------------
# Runner + validation
# ---------------------------------------------------------------------------
 
def validate(tokens: List[Token], result) -> List[str]:
    """Check that every id the LM produced actually exists among `tokens`
    -- OR is a legitimately new implied token (tokentype in
    IMPLIED_TOKENTYPES -- 'implied sum', 'continued discourse', or
    'implied subject'; see SentenceAnalysis's docstring) -- and that implied
    tokens themselves are well-formed. Returns a list of human-readable
    problem descriptions (empty if clean).

    'root' is a special sentinel value for an independent verb's own
    relatedtoken1 (see SentenceAnalysis's docstring) -- it is never treated as
    an unknown id, but syntax_model.md also requires that no actual token
    ever be assigned the id 'root', so that's checked here too.

    Implied tokens get their own, narrower checks: a tokengraph entry
    claiming an IMPLIED_TOKENTYPES value must use a genuinely NEW id (not
    one already in `tokens`) and must leave `token` unset (None) -- getting
    either wrong is exactly the kind of malformed output this function
    exists to catch, not a legitimate implied token. A non-implied entry,
    conversely, must use one of `tokens`' own ids and must NOT have
    `token=None` -- only an IMPLIED_TOKENTYPES tokentype may omit real
    surface text. This check is purely structural either way (new id,
    empty text) -- it does NOT also require an 'implied sum'/'continued
    discourse' token to have a matching `verbalunits` entry, or an
    'implied subject' token to lack one; that distinction is documented
    behavior (see SentenceAnalysis's docstring), not something this function
    enforces."""
    valid_ids = {t.id for t in tokens}
    problems = []

    if "root" in valid_ids:
        problems.append(
            "token id 'root' is reserved as the sentinel relatedtoken1 "
            "value for independent verbs and must not be assigned to an "
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
        for field in ("relatedtoken1", "relatedtoken2"):
            val = getattr(tok, field)
            if val is not None and val != "root" and val not in known_ids:
                problems.append(f"token {tok.id!r} {field}={val!r} is not a known token id")

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
        token_str = tok.token if tok.token is not None else f"({tok.tokentype})"
        print(f"  {tok.id:>4}  {token_str:<15} type={tok.tokentype:<11} lemma={tok.lemma or '-':<15} {rel_str}{vu_str}")