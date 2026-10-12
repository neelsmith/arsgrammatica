# Second review: revised syntax model and serialization format

Drafted 2026-10-12 on `wip`, at commit `f05a476`. This review covers four pages, all Neel's and read-only for Claude:

- `quarto/concepts/tokens.qmd` (TK)
- `quarto/concepts/verbalunits.qmd` (VU)
- `quarto/concepts/syntactic-analysis.qmd` (SA)
- `quarto/reference/analysisformat.qmd` (AF)

They are compared with `syntax_model.md` and with the earlier serialization docs: AF as of `c93eeb7` and `notes/serialization_formats.md`. The first review is `notes/syntax_model_revision_review.md`. Line numbers below refer to the current files.

---

## 1. Changes from `syntax_model.md`

This list is cumulative. Items marked **(new)** first appear in this revision; the rest were already in the first revision and are summarized briefly.

### Verbal units

- **(new) Semantic classification is removed.** `transitive active`, `transitive passive`, `intransitive` and `linking verb` are gone from VU, along with the AAT agent/target table that went with them. Verbal expressions now carry a syntactic type only.
- Gerundives are verbal expressions. There is a syntactic type `gerundive` for attributive use. Gerundive + *sum* is a compound form, and *sum* is its `auxiliary`.
- Participles are verbal expressions when they have a "circumstantial" sense; the old spec said "predicate" sense.
- The future infinitive *facturum fuisse* is anchored on *facturum* consistently.
- Syntactic types are now: `independent`, `dependent`, `direct quote`, `aside`, `indirect statement`, `circumstantial participle`, `gerundive`. The old spec used `independent clause`.

### Tokens

- **(new) `praenomen` no longer has to be abbreviated.** TK:28 defines it as the praenomen of a *praenomen nomen* pair, so *Agrippa* in *Agrippa Menenio* is a `praenomen` (TK:37).
- **(new) The other parts of a filiation formula are related.** A praenomen without a nomen (*L.* in *L. f.*) is treated as an ordinary substantive (`genitive` → *f.*). Abbreviations such as *f.* and *cos.* now receive relations (`apposition`) (SA:605–617). The old spec, and the code, left these unrelated.
- **(new) Numeral tokens get relations.** *XXV* is `adjectival` → *milia* (SA:496–509).
- There are three categories of implied token: elided *sum*, understood repeated verb, and implied substantive.

### Relations

| Change | Old (`syntax_model.md`) | Now |
|---|---|---|
| **(new)** split | `agent` | `agent-ablative` (*a/ab* + ablative) and `agent-dative` (dative of agent, mainly with gerundive + *sum*) |
| **(new)** widened | `predicate` (linking verbs only) | three uses: the predicate of a linking verb; the role or state of the subject (*heres*, *adolescens*); a predicate describing the object after verbs of naming or making (*consulem creaverunt*) |
| **(new)** clarified | — | subordinate clauses inside direct speech are analyzed normally under the quoted verb (SA:65–77) |
| renamed | `coordinating conjunction` | `coordinating word` (also used for sentence connectives such as *autem* and *igitur*) |
| renamed | `subordinating conjunction` | `subordinating word` (includes words that introduce indirect questions) |
| merged | `attributive` | `adjectival` |
| changed | gerundive → noun as `adjectival` | `gerundive` |
| new | — | `parataxis` |

- **(new) A token is no longer limited to two relations.** SA:11 says a token relates to "one or more" other tokens, implied tokens, or `root`. The old model, and the code, allowed at most two (`relation1`/`relation2`).
- **(new) Examples show multiple relations as repeated rows** for the same token ID (e.g. *que* (t2) on two rows), matching the new serialization format.

### Serialization (`#!tokens` block)

| | Before (AF@`c93eeb7`, `notes/serialization_formats.md`) | Now (AF) |
|---|---|---|
| Header | `context\|id\|tokentype\|text\|lemma\|verbalunit\|related1\|relationship1\|related2\|relationship2` (10 columns) | `context\|id\|tokentype\|text\|lemma\|verbalunit\|related\|relationship` (8 columns) |
| More than one relation | second column pair, at most two relations | one row per relation, unlimited; the order of a token's rows is unspecified |
| Row order | "ordered" (not further defined) | the set of distinct tokens is in document order |
| Punctuation | not stated | punctuation rows appear, with empty `related` and `relationship` |

The `#!sentences`, `#!verbal_units` and `#!lm` blocks are unchanged. That includes `#!verbal_units` still having a `semantic_type` column; see issue A1.

---

## 2. Status of the first review's items

Neel marked items ✅ in the first note. I checked each one against the current text.

| # | Item | Status |
|---|---|---|
| 1 | Parataxis has no verbal-unit syntactic type | **Still open.** SA:105–124 is reworded, but VU still defines `dependent` as "introduced by a subordinating word" (VU:48) and lists no `parataxis` type. What type do *videam* and *scribas* get? |
| 2 | `predicate` used with non-linking verbs | Resolved: SA:270–305 defines three uses. The A-A-T paragraph still mentions only the first use (B2). |
| 3 | *Unde venistis?* analyzed as an indirect question | Resolved (SA:851–852). |
| 4 | Gerundives always transitive passive; dative of agent | Resolved: semantic types are gone and `agent-dative` is added. |
| 5 | Deponents | No longer applies now that semantic types are gone. |
| 6 | Structure of the implied-participle ablative absolute (*consulibus*) | Open. No graph example yet. Multi-row serialization now makes "agrees with each of the two names" representable, but which relations are used is still unstated. *Agrippa* is now a `praenomen` → *Menenio*, so the two names are *Menenio* and *Postumio*. |
| 7 | *cum* `adjectival` → *Latini* in the relative-clause example | Open (SA:763). |
| 8 | No graph example for the understood repeated verb in the *ut* clause | Open. |
| 9 | The implied verb has no row of its own | Open (SA:811–820). |
| 10 | Status of implied-token labels | Open. AF now makes this concrete too (A4). |
| 11 | `adverbial` defined too narrowly | Open, and there are more instances now. SA:469 still says "to a verbal expression", but *tertium* → *cos.* (SA:616) and *et* → *tu* (SA:673) attach to nominals. |
| 12 | Infinitives that aren't verbal expressions take objects | Open. VU:17 is also circular ("constitute a verbal expression when they are constructed as a verbal expression"). |
| 13 | `direct quote` scope | Resolved in SA:55–77. VU:56 still says "Finite verbs in directly quoted speech", which could be read to include *conveniat* in SA's own example. That verb is presumably `dependent`. |
| 14 | "Every non-punctuation token…" | Resolved (SA:11). Praenomina, abbreviations and numerals now get relations. |
| 15 | "Three constructions" with four listed | Resolved. |
| 16 | `indirect speech` vs `indirect statement` | **Mostly resolved.** SA:177 still has *subeundam* `indirect speech`. |
| 17 | *esse* vs *fuisse* | Resolved. |
| 18 | Auxiliary attached to itself | Resolved. |
| 19 | Row with swapped columns | Resolved. |
| 20 | *adolescens* / *adulescens* | Resolved. |
| 21 | General elided-*sum* rule overstated (TK:122) | Open. |
| 22 | "Every gerundive is a verbal expression" vs the `gerundive` type | Open. Minor. |
| 23 | Subordinating-word definition | Partly resolved. "coordinating" is fixed, but SA:720 still says the word joins a clause "to a *preceding* expression", while the example's clause precedes its main verb. |
| 24 | Terminology drift | Open. New instance: SA:673 says "its `relation`", but AF's column is `related`. |
| 25 | *te mihi mater…* example | Open (SA:343–350). |
| 26 | Praenomen wording | Open, and now contradicted by TK (B1). |
| — | Orphan table fragment (SA:443–449 in the first review) | Resolved. It was removed. |

---

## 3. Remaining inconsistencies and unclear points

### A. Serialization (`analysisformat.qmd`)

1. **`#!verbal_units` still has `semantic_type`.** AF:34 and AF:41–42 give the header `context|token|syntactic_type|semantic_type`, and the example row has `transitive active`. This contradicts the removal of semantic classification. Either drop the column or say that it is retained and left empty.
2. **The `#!lm` example uses retired vocabulary.** The REASONING text (AF:96) mentions "transitive active", `relatedtoken1`/`relatedtoken2` and 'coordinating conjunction'. Readers may take it as current.
3. **The `verbalunit` column is never explained.** In the example only *cano* has a value (its own ID, `t3`), and *arma* and *virum* are empty. Does it mean "this token anchors a verbal unit"? Or "the verbal unit this token belongs to"? If the second, why are the objects empty?
4. **Where do implied tokens go, and what do they contain?** AF:51 orders rows by "the position of the token in document order", but implied tokens have no position in the text. Three things need stating:
   - where implied tokens are placed in the row order;
   - what their `tokentype` is (none of the six categories fits; compare item 10);
   - what goes in `text` and `lemma`. The text is presumably empty, since `None` is written as `""`. Is the lemma `sum` for an implied *sum*?
5. **Should a token's repeated rows agree?** With one row per relation, `context`, `tokentype`, `text`, `lemma` and `verbalunit` repeat. Must they be identical across a token's rows? Must the rows be contiguous? AF:72 implies contiguity ("the unique set of tokens appears in document order"), but doesn't state it.
6. **The punctuation row has a lemma.** AF:68 and AF:83 give `.` the lemma `cano`, which looks like a copy-paste slip. It should probably be empty.
7. **Does the sentence include its final punctuation?** The `#!sentences` example ends the sentence at `t3`, but the `#!tokens` example includes `t4` (`.`). So it's unclear whether final punctuation belongs to the sentence. This matters because the reader currently finds sentence boundaries by row position (see `notes/serialization_formats.md`).
8. **Typos in AF:**
   - "metatadata", "it that" (9)
   - "table token" (51)
   - "Puncutuation" (54)
   - "produce", "anlaysis", "sentences ID", "models reasoning", and an unbalanced "(" (90)
   - "URN content" probably means "URN context" (19)

### B. Model pages

1. **The two `praenomen` definitions disagree.** TK:28–37 allows an unabbreviated praenomen (*Agrippa*). SA:593 still defines it as "an abbreviation used in conjunction with a fully spelled out *nomen* or *cognomen*". Also, *Agrippa* is a `praenomen` in *Agrippa Menenio* (TK:37) but the subject in *M. Agrippa* (SA:611). That's correct, but it means the token type depends on context. A sentence in TK saying the tokenizer has to decide this from context would help.
2. **The A-A-T paragraph (SA:206) is out of step with the rest.**
   - It still uses the semantic-type vocabulary ("transitive active, intransitive, and linking verbs") that VU no longer defines.
   - It names only the ablative of agent, not `agent-dative`.
   - It names only the linking-verb `predicate` as a target. Is the predicate of use 3 (*consulem*) a target, or part of the target?

   Since VU's AAT table is gone, this paragraph and `concepts/aat.qmd` are now the only statement of the mapping.
3. **The `agent-dative` scope is vague.** SA:239 says "compound forms of the perfect sometimes and compounds formed from the gerundive + *sum* regularly". Is `agent-dative` limited to compound forms? What about the dative of agent with a gerundive that is not in a compound with *sum*, e.g. an attributive `gerundive`? There is also a related question: should a dative after a simple passive be `dative` or `agent-dative`?
4. **`predicate` use 3 attaches to the verb.** In *Ciceronem consulem creaverunt*, *consulem* → *creaverunt*, even though it describes *Ciceronem*. That may be intended, since it parallels use 2. But with multiple relations now allowed, it's worth stating explicitly that there is no link to the object.
5. **`parataxis` and `direct quote` interact with subordination.** In *scias oportet quid discas*, *quid* is `subordinating word` → *scias*. That's fine, but it shows a paratactic verb can govern subordinate clauses. Its syntactic type (item 1) affects how renderers will rank it.
6. **SA:11 links to the wrong page.** The link to "the format used to serialize analyses" points to `../reference/tokenizationformat.qmd`. It should be `analysisformat.qmd`.
7. **The direct-quote example (SA:67) is not formatted like the others.** It isn't italicized and mixes straight and curly quotation marks. SA:65 is also missing its final period.
8. **Typos in SA and VU:**
   - **SA:**
     - "The gerundive classified" (43)
     - "dative cases" (239)
     - `praeterita` in code style (246)
     - *praerterita* (249)
     - "on the other" → "on the other hand", and "co(n)s(sul)" → "co(n)s(ul)" (607)
     - "three categories *implied* tokens" is missing "of" (777)
   - **VU:**
     - "will related" (81)
     - "will classified" (141)
     - "an entry with its unique" is missing "ID" (164)
     - "the reduced semantic model of Agent-Action-Target model" repeats "model" (9)

### C. Related pages and code now out of date

These are not among the files reviewed, but readers will hit them.

- **`quarto/reference/vuvalues.qmd`:**
  - It still lists the four semantic types.
  - Its syntactic types lack `circumstantial participle` and `gerundive`.
  - It has no `parataxis` type, if one is added.
- **`quarto/reference/relationshipvalues.qmd`:** it still uses the old label set and descriptions.
  - It lists `subordinating conjunction`, `coordinating conjunction`, `attributive` and `agent`.
  - It is missing `parataxis`, `gerundive`, `agent-ablative`, `agent-dative` and `subordinating word`.
  - `predicate` is still "linked to a linking verb".
  - `praenomen` is still "abbreviated".
  - Its "Two-way relationships" section assumes the old two-slot model.
- **`notes/serialization_formats.md`** (Claude's) documents the 10-column `#!tokens` header. It will need updating when the code changes.
- **Code:** `arsgrammatica/serialization.py` still writes and reads `related1|relationship1|related2|relationship2` and `semantic_type`. `models.py` still has the old `RelationLabel` set: `agent`, `attributive`, `coordinating conjunction` and `subordinating conjunction`; no `parataxis`, `gerundive`, `agent-*` or `subordinating word`. It also still has the two-slot `relation1`/`relation2` structure. The dspy prompt, renderers, gold examples and tests depend on all of this. Moving to the new model means a coordinated change to code, prompt, fixtures and tests, plus a migration path (or a read-compatibility path) for analyses already saved in the 10-column format.
