# Third review: revised syntax model and serialization format

Drafted 2026-10-15 on `wip`. It compares the working tree against `syntax_model.md` and against the earlier serialization docs (`analysisformat.qmd` at `c93eeb7`, and `notes/serialization_formats.md`).

Pages reviewed:

| Abbreviation | Page | Changed since `f05a476`? |
|---|---|---|
| TK | `quarto/concepts/tokens.qmd` | no |
| VU | `quarto/concepts/verbalunits.qmd` | yes |
| SA | `quarto/concepts/syntactic-analysis.qmd` | yes |
| AF | `quarto/reference/analysisformat.qmd` | yes |

Earlier reviews are in `notes/syntax_model_revision_review.md` and `notes/syntax_model_revision_review_2.md`. Line numbers below refer to the current working-tree files.

---

## 1. Changes from `syntax_model.md`

### Cumulative summary

These changes were already described in the earlier reviews.

- **Verbal units**
  - Verbal units carry a syntactic type only. The semantic types are gone.
  - Gerundives are verbal expressions, with syntactic type `gerundive` when attributive. Gerundive + *sum* is a compound form.
  - The participle criterion is "circumstantial" sense.
- **Tokens**
  - There are three categories of implied token.
  - `praenomen` need not be abbreviated.
  - Abbreviations and numerals now get relations.
- **Relations**
  - `coordinating word` replaces `coordinating conjunction`.
  - `subordinating word` replaces `subordinating conjunction`.
  - `adjectival` absorbs `attributive`.
  - `gerundive` is new.
  - `parataxis` is new.
  - `agent` is split into `agent-ablative` and `agent-dative`.
  - `predicate` has three uses.
  - A token may have any number of relations.
- **Serialization**
  - Each relation is one row in `#!tokens`, replacing the two column pairs `related1`/`relationship1` and `related2`/`relationship2`.

### New in this revision

**Verbal units**

- **New syntactic type `parataxis`** (VU:71–78): a subjunctive clause after verbs of necessity, wishing or commanding, with no subordinating word. This closes the gap noted in both earlier reviews.

**Graph relations (SA)**

- **A-A-T mapping rewritten** (SA:206–210). It is now stated by voice rather than by semantic type:
  - **Active and deponent verbs:** the `subject` is the agent; a `direct object` is the target; a nominative `predicate` of a linking verb is the target.
  - **Non-deponent passive verbs:** the `subject` is the target; `agent-ablative` or `agent-dative` is the agent.
  - Predicate uses 2 and 3 are explicitly *not* targets.
- **`agent-dative` scope narrowed** (SA:248–281). It is now:
  - *regular* with gerundive + an explicit or implicit *sum*;
  - *sometimes* found with perfect compound forms.

  Two new examples were added.
- **`predicate` use 3 now attaches to the direct object.** *consulem* → *Ciceronem* (SA:333), where it previously attached to the verb.
- **`praenomen` redefined** (SA:622) as "always used in conjunction with a fully spelled out *nomen* or *cognomen*". It is no longer required to be an abbreviation.

**Serialization (AF)**

- **`#!verbal_units`:** the `semantic_type` column is dropped. The header is now `context|token|syntactic_type`.
- **`#!tokens`:** the `verbalunit` column is dropped. The header is now `context|id|tokentype|text|lemma|related|relationship`, which is 7 columns, down from 10 in the original format.
- **Repeated rows:**
  - A token's repeated rows must be identical except for `related` and `relationship`.
  - They must be contiguous.
  - Their internal order is unspecified.
- **Implied tokens:**
  - They may appear anywhere in `#!tokens`.
  - They carry a token type such as `implied sum`.
  - The example uses a new ID convention, `t2_implied`.
- **Final punctuation** now belongs to the sentence: the `#!sentences` example ends at `t4`.

### Comparison with the previous serialization docs

| Block | Earlier format | Now |
|---|---|---|
| `#!sentences` | unchanged | unchanged; the example now includes the final punctuation |
| `#!verbal_units` | `context\|token\|syntactic_type\|semantic_type` | `context\|token\|syntactic_type` |
| `#!tokens` | `context\|id\|tokentype\|text\|lemma\|verbalunit\|related1\|relationship1\|related2\|relationship2` | `context\|id\|tokentype\|text\|lemma\|related\|relationship`, with one row per relation |
| `#!lm` | unchanged | unchanged |

---

## 2. Status of the second review's items

Neel marked the items he addressed with ✅ in `notes/syntax_model_revision_review_2.md`. I checked each against the current text.

### Resolved

- **1** Parataxis now has a syntactic type.
- **16** SA:177 now says `indirect statement`.
- **A1** `semantic_type` is gone from AF.
- **A3** The `verbalunit` column is removed.
- **A5** The rule for repeated rows is now stated.
- **A7** The `#!sentences` example now includes the final punctuation.
- **B2** The A-A-T paragraph is rewritten. A residual issue is in C5 below.
- **B4** `predicate` use 3 now attaches to the object.
- **B6** The link is fixed.
- **Most typos in SA, VU and AF** are fixed.

### Partly resolved

- **A4** Implied-token placement and token type are now stated. The new example row is malformed, though (C1), and the ID convention is undocumented (C3).
- **A6** The punctuation lemma was fixed in the first `#!tokens` example only. The second example still has `.|cano|` (AF:87). Both punctuation rows also have an extra field (C2).
- **A8** Fixed:
  - "metatadata"
  - "table token"
  - "Puncutuation"
  - "URN content"

  Still there:
  - "it that" (AF:9)
  - a new typo, "producse" (AF:113)
- **B1** SA's `praenomen` definition no longer requires an abbreviation, but the new wording contradicts the *L. f.* example (C6).
- **B3** The scope is now stated, but my question text was pasted into the page (C4), and one example is wrong (C4).
- **B8** Most typos are fixed, but *praerterita* is still at SA:278.

### Still open

- **A2** The `#!lm` REASONING example still uses retired vocabulary: "transitive active", `relatedtoken1`/`relatedtoken2`, and 'coordinating conjunction' (AF:119).
- **First-review items 6–12, 21, 22, 24, 25.** In brief:
  - 6: no graph example for the *consulibus* ablative absolute.
  - 7: *cum* `adjectival` → *Latini* (SA:792).
  - 8: no graph example for the *ut … superaret* repeated verb.
  - 9: the implied verb has no row of its own (SA:840–849).
  - 11: `adverbial` is still defined as attaching "to a verbal expression" (SA:498).
  - 12: the circular VU:17.
  - 21: TK:122 says an elided *sum* always adds a verbal expression.
  - 22: "every gerundive" (VU:19).
  - 24: terminology drift.
  - 25: *te mihi mater* (SA:343ff).
  - 23 is also only partly fixed: "preceding expression" remains at SA:749, and the same phrase is at SA:654.
- **C (related pages and code):** `vuvalues.qmd`, `relationshipvalues.qmd`, `notes/serialization_formats.md` and the code are unchanged. See C9 below for a new conflict in `tokentypes.qmd`.

---

## 3. Inconsistencies and unclear points in this revision

### C1. The implied-token example in AF is malformed (AF:99–107)

Several problems in one small block:

- **Header:** it says `relationship1`. It should say `relationship`.
- **The implied row has its fields shifted.** `|t2_implied|implied sum|sum|t2_implied|root|unit verb` puts `sum` in `text` and `t2_implied` in `lemma`. AF:11, TK:116 and SA all say implied tokens have text `None`, which is serialized as empty. The row should presumably be `|t2_implied|implied sum||sum|root|unit verb`.
- **`context` is empty on every row.** The other examples use a URN. If an empty context is allowed (e.g. analyzing a bare string with no citation), AF should say so. Otherwise the rows need a URN.
- **The relations contradict SA.**
  - AF has *omnia* `subject` → implied *sum*, and *praeclara* `adjectival` → *omnia*.
  - SA:816–818 has the reverse: *omnia* `adjectival` → *praeclara*, and *praeclara* `subject`.

  Either reading is defensible, but the two pages should agree.

### C2. Punctuation rows have one field too many

The `#!tokens` header has 7 fields. These rows have 8:

- AF:72 `…|t4|punctuation|.||||`
- AF:87 `…|t4|punctuation|.|cano|||`
- AF:106 `|t3|punctuation|.||||`

Each should end `.|||`. That's lemma, related and relationship, all empty. AF:87 also still has the stray lemma `cano`.

### C3. Implied tokens' IDs and sentence membership are undefined

- **IDs.** The `t2_implied` convention appears only in the example. Questions to settle:
  - Is the number the ID of a neighboring real token? Here it's *rara*, `t2`.
  - How are two implied tokens near the same position kept distinct?
  - Is the convention required, or can any unique ID be used?
- **Sentence membership.** "Implied tokens … may be added to the table at any point" (AF:93). But `#!sentences` defines a sentence by its first and last token, and the current reader finds sentence boundaries by row position. In a file with several sentences, an implied token placed outside its sentence's run of rows has no stated way to say which sentence it belongs to.

  Options include:
  - requiring implied rows to fall within their sentence's run, while leaving their order within the sentence free;
  - deriving membership from the token's relations.

### C4. Problems in the `agent-dative` section (SA:244–281)

- **Pasted review text.** SA:246 is my review's question text pasted into the page: *"compound forms of the perfect sometimes …" Is `agent-dative` limited…*. It needs to be deleted.
- **Wrong relationship label.** SA:256 has *agenda* `verbal unit` → (`root`); it should be `unit verb`.
- **The second example is wrong.** *nunc pede libero pulsanda tellus* (SA:259–266) uses *pede (libero)*, which is ablative ("with free foot"), not a dative of agent. The sentence does have gerundive + implied *sum*, but it has no agent at all. In the current scheme *pede* would be `ablative` → *pulsanda*. A different example is needed, e.g. *mihi eundum est*, or one with an implied *sum* plus a real dative.
- **Typo.** *praerterita* (SA:278).
- **Remaining scope question.** The text now implies, without stating it, that a dative with an attributive `gerundive` or with a simple passive is plain `dative`. One sentence saying so would close it.

### C5. A-A-T paragraph: "nominative predicate" is too narrow (SA:208)

The target of a linking verb is defined as a *nominative* `predicate`, and "non-nominative predicates (illustrated below) are not treated as targets". But a linking verb's predicate is accusative in indirect statement (*dixit Lucumonem filium esse*) and dative in some constructions (*licet esse beatis*). These are use-1 predicates, so presumably they are targets. Use 2's *heres* shows the opposite problem: it is nominative, but explicitly not a target.

The criterion that matches the three-use scheme is "the predicate of a linking verb" (use 1), not the case of the predicate.

A related point: gerundive + *sum* takes an `agent-dative`, but the gerundive isn't a "passive voice verb" in the usual morphological sense. The paragraph should say explicitly that gerundive compounds follow the passive mapping.

### C6. The `praenomen` definition contradicts its example (SA:622 vs SA:636)

- SA:622 says a `praenomen` token is "*always* used in conjunction with a fully spelled out *nomen* or *cognomen*".
- SA:636 then treats *L.* as a praenomen "without corresponding nomen".
- TK:32 classifies *L.* as `praenomen`.

So the token *type* is `praenomen` while the "always" rule doesn't hold. Two possible fixes:

- Say the `praenomen` *relation* is used only when a nomen or cognomen is present.
- Classify a bare praenomen differently.

Also:
- SA:622 has "will clearly showing".
- The definition no longer says that the relationship is `praenomen`.

### C7. `predicate` with passive verbs of naming is unstated

Use 3 (*Ciceronem consulem creaverunt*) attaches the predicate to the direct object. In the passive (*Cicero consul creatus est*), there is no object, and *consul* is a nominative predicate of a non-linking passive verb. Which use applies there, and what is it related to: *Cicero* or *creatus*? Is it a target?

### C8. Leftover AAT phrasing in VU:9

VU:9 still gives "transitive active verbs" as its example of agent and target. That's harmless as ordinary grammar, but it's now the only place in VU that uses the retired semantic-type term. "active verbs with a direct object" would avoid it.

### C9. Implied-token type names disagree across pages

- `quarto/reference/tokentypes.qmd`, which is outside this review's four pages, lists the implied token types as `implied sum`, `continued verb`, `implied substantive`.
- SA:833 names them `implied sum`, `implied verb`, `implied substantive`.
- TK's headings are "Elided forms of `sum`", "Understood repeated verb", "Implied substantive", and TK's category list (TK:20–100) doesn't mention implied types at all.
- AF now uses `implied sum` as an actual `tokentype` value.

So the vocabulary needs one canonical set, and TK should list it.

### C10. `#!lm` example out of step

- The CONTEXT range still ends at `…1.1.t3` (AF:118), while the `#!sentences` example now ends at `t4`.
- The REASONING text still uses the old vocabulary (see A2).

### C11. Smaller points

- VU:73–76: the `parataxis` definition calls it "a subordinate clause … introduced by a verb". "Governed by" would be clearer, since "introduced by" is how VU describes subordinating words.
- AF:93: "Implied tokens have no specified order since they do not appear in the text." This conflicts with "Entries in the table for tokens are *ordered*" (AF:68) unless the exception is stated there.
- AF: what does `related` contain when it points to an implied token: just the bare ID (`t2_implied`)? The example implies so. It would also help to say that `root` is a reserved value that cannot be used as a token ID. The old spec said this; the new pages don't.
