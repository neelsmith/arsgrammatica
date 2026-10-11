# Review: revised syntax model (quarto/concepts) vs. `syntax_model.md`

> ✅ marks issues or questions that have been resolved

Drafted 2026-10-10 on `wip`. Compares the old single-file spec `syntax_model.md` with Neel's rewritten pages `quarto/concepts/tokens.qmd`, `verbalunits.qmd` and `syntactic-analysis.qmd` (read-only for Claude; nothing in them was edited). Line numbers refer to the files as of this date.

---

## 1. What changed between the old and new model

### Organization and framing

- The single spec is split into three pages: tokens, verbal units, and the token graph.
- The model is now explicitly anchored in the Agent-Action-Target (AAT) model. `verbalunits.qmd` adds a table mapping agent and target onto the subject, object and ablative of agent for active and passive verbs. `syntactic-analysis.qmd` groups subject, agent, direct object and predicate as "A-A-T relations".
- Examples are now shown as per-example tables (Token | relationship | related token) instead of prose about `relation1`/`relationship1`.
- New: the note on extending CTS URNs to token-level URNs (`tokens.qmd`).

### Tokens

- The six token categories are unchanged. Praenomen and abbreviation are now listed first, so `punctuation` is defined as "any *other*" punctuation character.
- Implied tokens are reorganized into **three** categories, all with text value `None`.
  1. Elided *sum*. Same as before.
  2. **Understood repeated verb.** This generalizes the old "continuation of indirect discourse" case. A new example has an implied repeated verb inside an *ut* clause (*…exspectationem ipsius adventus admiratioque superaret*).
  3. **Implied substantive.** This is new as a category. It covers a relative pronoun with an unexpressed antecedent (*quem dii amant…*), which is new. It also covers a participle agreeing with an unexpressed subject, which was a sub-rule under circumstantial participles in the old spec.
- New explicit counter-case: a participle used as a plain substantive (*sapienti sat est*) needs no implied token and no verbal expression.
- The *consulibus* example is now called an "ablative absolute construction" (previously "predicate construction"). The implied participle is said to agree with *each* of the two names.

### Verbal units

- **Gerundives are now verbal expressions.** This is the biggest substantive change.
  - New syntactic type `gerundive` for an attributive gerundive.
  - Gerundive + *sum* is now a compound form with *sum* as `auxiliary`, like the perfect passive. It is classified by its context, e.g. `independent` or `indirect statement`.
  - Every gerundive is semantic type `transitive passive`.
  - In the old spec, a gerundive was just an adjective related to its noun as `adjectival`.
- The gerund is still a substantive and not a verbal expression. That is unchanged, but it is now stated explicitly as a counter-example.
- Participles now qualify as verbal expressions when they have a "circumstantial" sense; the old wording was "predicate" sense. The tie-break rule (prefer circumstantial) is unchanged.
- **The future perfect infinitive is now anchored consistently.** The old spec anchored *facturum fuisse* on *fuisse* in one place (line 27) and on *facturum* in another (line 78). The new page uses *facturum* throughout.
- Type names are normalized from `independent clause` to `independent`.
- The semantic types have fuller definitions. `intransitive` now explicitly includes passive-voice forms.
- An implied repeated verb takes the syntactic type of the expression it repeats. In the example that is `dependent` after *ut*. The implied verb of speaking in indirect discourse is still `independent` / `transitive active`.

### Graph relations

Relationship labels compared with the old set:

| Change | Old | New |
|---|---|---|
| renamed | `coordinating conjunction` | `coordinating word` |
| renamed | `subordinating conjunction` | `subordinating word` |
| merged | `attributive` (prepositional phrase modifying a noun) | `adjectival` |
| changed | gerundive → noun as `adjectival` | `gerundive` |
| new | — | `parataxis` (subjunctive clause with no subordinating word after *oportet*, *volo*, *precor*, etc.) |

Other changes in the graph:

- **`coordinating word` is broader** than the old `coordinating conjunction`. It now covers sentence connectives such as *igitur*, *autem*, *nam*, *ceterum* and *sed* when they relate to a single verb. The old spec gave this one-sided treatment only to *sed* opening a sentence.
- **`subordinating word`** explicitly includes interrogatives introducing indirect questions. An example table is given (*scias oportet quid discas*).
- **Agent example fixed.** The old example related *a* to `t5` (*est*), contradicting its own rule that the agent attaches to the participle. The new table relates *a* to *condita*.
- New statement that every non-punctuation token is related to one or two other tokens.
- The infinitive-as-noun and gerund material is regrouped as "Substantives from verbal roots".
- Dropped or no longer explicit:
  - the rule that `root` must never be used as a token ID;
  - the explicit rule that a subject or object attaches to the participle and not the auxiliary in compound forms (the examples still show it);
  - the impersonal verbs (*licet*, *decet*) in the complementary infinitive rule;
  - the example of an adverb modifying a gerund (*bene disserendi*);
  - *opus est* + ablative as a named idiom (it survives only as an example).

### Impact on code (not part of the docs, but worth knowing)

The package still implements the old model.

- `arsgrammatica/models.py`'s `RelationLabel` still lists `subordinating conjunction`, `coordinating conjunction` and `attributive`, and has no `parataxis` or `gerundive`.
- `rendering.py`, `verbal_units.py`, `mermaid.py` and `displacy_viz.py` key on the old coordinating and subordinating labels.
- `latin_syntax_dspy.py` and several tests and gold examples cite `syntax_model.md` by name.

So adopting the new model will mean updating the code, the prompt, the gold examples and the tests, as well as removing `syntax_model.md`. Removing the file without that work would leave the code pointing at a spec that no longer exists.

---

## 2. Inconsistencies, contradictions and unclear points in the new pages

Grouped roughly by importance. "VU" = `verbalunits.qmd`, "SA" = `syntactic-analysis.qmd`, "TK" = `tokens.qmd`.

### Substantive: model-level questions

1. **Parataxis has no verbal-unit syntactic type.** SA:90–107 introduces `parataxis`, but VU defines `dependent` as a verb "introduced by a subordinating word" (VU:51). *videam* in *Precor eam videam* has no subordinating word. So which syntactic type does it get: `dependent` (redefined), or a new `parataxis` type?
2. **`predicate` is used with verbs that are not linking verbs.** SA:243 defines `predicate` for linking verbs only, and VU:139 also limits linking-verb predicates to the nominative. But SA:440 has *heres* `predicate` → *superfuit*, and SA:753 has *adulescens* `predicate` → *moritur*. Both verbs are intransitive. Either broaden the definition (e.g. a predicative complement of any verb), or use another relation for these. This also bears on the AAT section, which treats the linking-verb predicate as a target (SA:189).
3. **A direct quote is analyzed as an indirect question.** In *…interrogans eos: Unde venistis?* (SA:759–770), *Unde* is `subordinating word` → *interrogans* and *venistis* is `unit verb` → *Unde*. By the `direct quote` rule (VU:57, SA:53), *venistis* should be `direct quote` → *interrogans*, and *Unde* should be `adverbial` → *venistis*.
4. **"Every gerundive is transitive passive" vs. impersonal gerundives.** VU:183 says the gerundive is *always* `transitive passive`. But intransitive verbs form impersonal gerundives (*eundum est*, *mihi pugnandum est*). Also, the agent of a gerundive is normally the **dative of agent**. The AAT table (VU:146) and the `agent` relation (SA:207, *a/ab* only) do not cover it. How should *mihi* in *mihi pugnandum est* be related: `agent` or `dative`?
5. **Deponent verbs are not addressed.** Semantic types are defined partly by voice: "active-voice … transitive", "passive-voice … transitive" (VU:160–177). The examples include deponents (*abutere* VU:45, *loquebatur*, *moritur*) and do not say whether a deponent counts as active or passive voice for classification. Deponents that govern a non-accusative case (*abutor* + ablative) make this sharper.
6. **The structure of the implied-participle ablative absolute is unspecified.** TK:123 says the implied participle agrees "with each of the two consuls' names". Several things are unclear:
   - Does the participle use both `relation1` and `relation2`?
   - Do both *Agrippa Menenio* and *P. Postumio* take `ablative absolute` → *moritur*?
   - How does *consulibus* relate? Presumably `predicate` → the implied participle, since it is a `linking verb`.

   No graph example is given for this case, although it is one of the documented implied-token cases.
7. **The prepositional phrase in the relative-pronoun example looks misattached.** SA:682 has *cum* `adjectival` → *Latini*. But *cum quibus* belongs to the relative clause ("with whom a treaty had been struck"), so it should be `adverbial` → *ictum*. The old table left *cum* unrelated. The new example also adds *Tullo regnante*, which is a third verbal expression (an ablative absolute) not shown in the table.
8. **The understood repeated verb in an *ut* clause has no graph example.** TK:140 and VU:221 add this case, but SA "Implied verb" (SA:722) covers only the indirect-discourse case. For the *superaret* example, it's unclear:
   - Do *superaret* and the implied verb both relate to *ut* as `unit verb`?
   - Is there any coordinating relation between the two result clauses?
   - The *que* in *admiratioque* coordinates *adventus* and *admiratio*. Does this interact with the implied verb?
9. **The implied verb has no row of its own.** In the SA:729–738 table, three tokens point to (`implied verb`), but the implied verb itself never appears. Presumably it should be `unit verb` → (`root`), consistent with its `independent` type (VU:229).
10. **The status of implied-token labels is unclear.**
    - SA:695 names the categories `implied sum`, `implied verb`, `implied substantive`, but TK uses different headings: "Elided forms of *sum*", "Understood repeated verb", "Implied substantive".
    - SA:131 uses yet another name, `elided sum`.
    - None of these appears among TK's token categories.

    Are these display labels only, or a token-type value? If an implied token has a token category, which one is it?
11. **The definitions of `adverbial` are too narrow.**
    - SA:416 says adverbial expressions relate "to a verbal expression".
    - SA:453 has prepositions relating `adverbial` to "a verb or adjective".
    - SA:596 has *et* `adverbial` → *tu*, a pronoun.
    - Adverbs that modify adjectives or other adverbs are common (*durius* is fine, but consider *valde bonus*).

    The rule should say what non-verbal heads are allowed.
12. **"Infinitives" in VU's opening list vs. other infinitive uses.** VU:17 makes only the indirect-statement infinitive a verbal expression, which implies complementary and substantive infinitives are not. But SA:395 has *artes* `direct object` → *didicisse*, so a token that is not a verbal expression can take a direct object. That is reasonable, but the AAT framing on VU:9 ("all syntactic features are organized around … verbal ideas") reads as if it shouldn't. A sentence acknowledging this would help.
13. **`direct quote` scope.** VU:59 says "finite verbs in directly quoted speech", while SA:55 says "*independent* verbs in directly quoted speech". What type does a subordinate clause *inside* a quotation get: `dependent` or `direct quote`? Use SA's wording in VU, and state the rule for subordinate clauses.
14. **"Every non-punctuation token is related to one or two other tokens" (SA:11).** Independent verbs relate to `root`, which is not a token. The first *et* of an *et A et B* series relates to only one token. And it's not stated how `abbreviation` and `numeral` tokens relate. *f.*, *cos.* and *XXV* never appear in any relation, and the code currently leaves *L. f.*-style praenomens unrelated.

### Internal contradictions and label errors

15. **"Three constructions" but four are listed.** VU:14 says "three possible constructions"; the list has four (gerundive added).
16. **`indirect speech` is used where `indirect statement` is meant.** VU:82 has "*esse* is `indirect speech`" and SA:160 has *subeundam* `indirect speech`. The defined label is `indirect statement`.
17. **Wrong token in the future-infinitive example.** VU:88 says "*esse* will be related to it as `auxiliary`", but the example is *facturum fuisse*, so this should be *fuisse*.
18. **Auxiliary attached to itself.** SA:424 and SA:464 have *erat* `auxiliary` → *erat*. It should be → *ventum*.
19. **A row with swapped columns.** SA:131 has `(elided sum) | excepti | auxiliary`, so the relationship and the related token are in the wrong columns. The label `elided sum` also differs from `implied sum` elsewhere.
20. **Spelling mismatch.** *adolescens* (TK:160) vs. *adulescens* (SA:753).
21. **The general rule for elided *sum* is overstated.** TK:112 says an elided *sum* always adds an entry to the list of verbal expressions. The perfect-passive case a few lines later (TK:129) correctly says it doesn't. Qualify the general sentence.
22. **"Every gerundive is a verbal expression" (VU:19) vs. the `gerundive` type (VU:115).** These are compatible: attributive gets type `gerundive` and predicate + *sum* gets the type of its context. But a reader could take VU:19 to mean the type is always `gerundive`. A line saying "the syntactic type `gerundive` is only for attributive use" would prevent that. Also, the attributive gerundive in SA:227's example (*Lucretiae … stuprandae*) is not acknowledged.
23. **Subordinating-word definition.** SA:639 says "we relate the *coordinating* word to the verb" (it should be *subordinating*). It also says the word joins a clause "to a *preceding* expression", but the example's subordinate clause precedes its governing verb (*cum … perlustrasset, pergit*).
24. **Terminology drift.**
    - "verbal unit" and "verbal expression" are used interchangeably: the VU page title vs. the `VerbalExpression` class and most of the text.
    - SA:596 switches to `relation1`/`relationship1`, which the rest of the page no longer uses.
    - TK:167 calls the participle's head an "antecedent".

### Questionable examples

25. **SA:290, *te mihi mater aucturum … cecinit*.** *mihi* is more naturally read with *cecinit* ("my mother prophesied to me") than with *mater*. The sentence also contains an indirect statement with an elided *esse* (*aucturum [esse]*), which would itself need an implied token and an `indirect statement` row. A cleaner example of a dative depending on a noun might be better.
26. **SA:528, praenomen: "relates to the full form clearly showing its case usage".** The wording is unclear. It probably means "relates to the fully written name (nomen or cognomen), which shows the case".

### Markdown and formatting issues

- SA:285 and SA:293: header rows have two columns, but the data rows have three.
- SA:443–449: an orphaned table fragment (*Legatos … mittunt … ad*) with no heading or example, ending in a stray `|`.
- SA:748: the header repeats `relationship 1 | related token 1` and should be `… 2`. Row SA:755 is short.
- SA:587: the row has extra trailing cells.
- SA:162: stray `´` after (`root`).
- SA:507: stray leading `.` in the example.
- SA:518: `*filia` is missing its closing asterisk.
- SA:571: `dixit` is in code style instead of italics.
- SA:711: `(root)` vs. (`root`) elsewhere.


### Typos

- **TK:**
  - ✅ "impementation" (7)
  - ✅ "This distinguish this" (169)
  - ✅ *sapientī* with a macron vs. *sapienti* in the text
- **VU:**
  - ✅ "Classifiying" (34)
  - ✅ "expresion" (47)
  - ✅ "classifed" (63)
  - ✅ "unconneccted" (72)
  - ✅ "indepedendent" (82)
  - ✅ "wil" (88)
  - ✅ "circumsstantial" (98)
  - ✅ "definiing" (108)
  - ✅ "thpe" (199)
  - ✅ "situtation" (202)
  - ✅ "explict" (223)
  - ✅ "discourse.Entire" (226)
  - ✅ "syntatic" (229)
- **SA:**
  - ✅ "impementation" (7)
  - ✅ "hypthetical" (18)
  - ✅ "commandsj" (92)
  - ✅ *Precord* (99)
  - ✅ "functional adverbially" (453)
  - ✅ *venerate* (478)
  - ✅ "wth" (528)
  - ✅ "la\`t" (596)
  - ✅ assiduitate*assiduate* (621, inherited from the old spec)
  - ✅ "introducted" (671)
