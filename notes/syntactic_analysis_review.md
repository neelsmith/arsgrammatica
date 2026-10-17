# Review: `quarto/concepts/syntactic-analysis.qmd`


Drafted 2026-10-15 on `wip`. This review covers only the committed version of `quarto/concepts/syntactic-analysis.qmd` (SA). The page is Neel's and read-only for Claude. Line numbers refer to it as of this date.

## Errors to fix

1. ✅ **Line 253:** *agenda* has the relationship `verbal unit`. It should be `unit verb`.
2. ✅ **The second `agent-dative` example is wrong (lines 256–263).** In *nunc pede libero pulsanda tellus*, *pede (libero)* is ablative ("with free foot"), not a dative of agent.
   - The sentence has gerundive + implied *sum*, but no agent at all. *pede* should be `ablative` → *pulsanda*.
   - For an example with an implied *sum* and a real dative, try something like *mihi eundum* or *Carthago nobis delenda*.
3.  ✅ **Line 275:** *praerterita* → *praeterita*.
4.  ✅ **Line 792:** *cum* `adjectival` → *Latini* looks misattached. *cum quibus* belongs to the relative clause ("with whom a treaty had been struck"), so it should be `adverbial` → *ictum*.
5. ✅ **Implied verbal tokens have no rows of their own.** In these tables, other tokens point to the implied token, but it never appears as a row itself:
   - lines 814–818: (`implied sum`) for *omnia praeclara rara*
   - lines 840–849: (`implied verb`)

   Each needs a row: `unit verb` → (`root`). `verbalunits.qmd` types both as `independent`.

## Contradictions and unclear rules

6. ✅ **A-A-T: "nominative predicate" is the wrong criterion (line 208).**
   - Line 208 makes a linking verb's *nominative* predicate the target. It adds that "non-nominative predicates (illustrated below) are not treated as targets".
   - But a linking verb's predicate is accusative in indirect statement (*dixit Lucumonem filium esse*). This is still predicate use 1, so presumably a target.
   - Meanwhile use 2's *heres* is nominative, yet explicitly not a target.

   The criterion that matches lines 300–322 is "use 1: the predicate of a linking verb", not the predicate's case.
7. ✅ **A-A-T: gerundive compounds.** Line 210 maps agent and target for "passive voice verbs that are not deponent". Say explicitly that gerundive + *sum* follows the same mapping. The gerundive isn't a passive verb form in the morphological sense, yet it takes `agent-dative`.
8. ✅ **`adverbial` is defined too narrowly (line 495).** It says "to a verbal expression", but the page itself attaches `adverbial` to other things:
   - prepositions → "a verb or adjective" (line 543)
   - *tertium* → *cos.*, a noun (line 645)
   - *et* → *tu*, a pronoun (line 702)

   Widen the definition, and say what heads are allowed.
9. ✅ **Where a subordinate clause sits (lines 95 and 749).** Both lines say the subordinating word joins a clause "to a *preceding* expression". But the example's subordinate clause comes first (*cum … perlustrasset, pergit*). Drop "preceding".
10. ✅ **Relative pronouns vs. `subordinating word`.**
    - Line 95 lists the relative pronoun as a kind of subordinating word.
    - But relatives never take the `subordinating word` relation. They take `relative pronoun` plus their function in the clause (lines 781–799).

    One sentence would prevent confusion.
11. ✅ ***Predicate use 3 in the passive.** In *Cicero consul creatus est*, there is no object for *consul* to attach to.
    - Which use applies?
    - Is it related to *Cicero* or to *creatus*?
    - Is it a target?
12. ✅ **`agent-dative` vs. `dative`.** The text implies, but doesn't say, that the following are plain `dative`:
    - a dative with an attributive `gerundive`;
    - a dative with a simple (non-compound) passive.

    One sentence would close the question.

## Questions to decide

13. **Ablative absolute with an implied participle.** There's no example of this (cf. *Agrippa Menenio P. Postumio consulibus*, `tokens.qmd`). It's unclear:
    - whether both names (*Menenio*, *Postumio*) take `ablative absolute` → verb;
    - whether the implied participle relates to both names;
    - how *consulibus* relates (presumably `predicate` → the implied participle).
14. **The dative example *te mihi mater aucturum … cecinit* (lines 369–376).**
    - *mihi* is more naturally read with *cecinit* ("my mother prophesied to me") than with *mater*.
    - The sentence also contains an indirect statement with an elided *esse* (*aucturum [esse]*), which the table doesn't show.

    A cleaner example of a dative depending on a noun would help.
15. **Complementary infinitive (line 189).** Which verbs count beyond *volo*?
    - Is the list open-ended?
    - Do impersonals (*licet*, *decet*, *oportet* + infinitive) belong? The old spec listed them.
    - *oportet* also appears under `parataxis` (line 766), with a subjunctive.

## Terminology and formatting

16. **Line 702:** "as its `relation`" doesn't match the column names `related` / `relationship` used in `analysisformat.qmd`, nor this page's own "related token" column. Also, *adverbial* should be in code style.
17. **Line 140:** "related to an antecedent substantive". Participles don't have antecedents; "the substantive it agrees with" is clearer.
18. **Line 519:** `superfuit` is in code style; elsewhere related tokens are in italics.
19. **Lines 65 and 67:**
    - Line 65 has no final period.
    - The example on line 67 isn't italicized and mixes straight and curly quotation marks.
20. **Line 619:** "relatinship" → "relationship".
21. **Line 636:** "we take it be" → "we take it to be".
22. **"Token graph" vs "syntax graph".** This page's title says "graph of syntactic relations", while `verbalunits.qmd` uses both "token graph" and "syntax graph". Pick one term across pages.

## Related page (outside this review)

- **`quarto/reference/relationshipvalues.qmd` is out of date.**
  - It still lists `subordinating conjunction`, `coordinating conjunction`, `attributive` and `agent`.
  - It lacks `parataxis`, `gerundive`, `agent-ablative`, `agent-dative` and `subordinating word`.
  - It still describes `predicate` as linked to a linking verb, and `praenomen` as abbreviated.
  - Its "Two-way relationships" section assumes the old two-column model.
