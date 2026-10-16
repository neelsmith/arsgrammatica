# Review: `quarto/concepts/verbalunits.qmd`

Drafted 2026-10-15 on `wip`. This review covers the committed version of `quarto/concepts/verbalunits.qmd` (VU) only; the file is Neel's and read-only for Claude. Line numbers refer to it as of this date.

## Contradictions to fix

1. ✅  **The `direct quote` scope is too broad (line 56).** "Finite verbs in directly quoted speech" also covers subordinate verbs inside a quotation. But `syntactic-analysis.qmd` (lines 65–77) analyzes those normally: *conveniat* in *"Vos," inquit, "videritis quid balteo conveniat"* relates to *quid*, so it is presumably `dependent`. Say "the main verb(s) of directly quoted speech".
2.  ✅  **"Every gerundive" (line 19) vs the `gerundive` type (lines 122–129).**
   - Line 19 says every gerundive is a verbal expression.
   - The type `gerundive` applies only to the attributive use.
   - Gerundive + *sum* takes the type of its context, e.g. `independent` or `indirect statement`.

   Lines 122–129 do say this, but line 19 reads as if the type is always `gerundive`. One sentence at line 19 would prevent the misreading.
3.  ✅  **The infinitive criterion is circular (line 17).** "Constitute a verbal expression when they are constructed as a verbal expression in indirect speech" defines the term with itself. Say "when they are the verb of an indirect statement".
4. **The *superaret* example (line 174).** *superaret* is written at the end of the *second* clause (*exspectationem … adventus admiratioque superaret*). A singular verb with a compound subject like *adventus admiratioque* is normal in Latin. So the more natural reading is the reverse of the page's:
   - the explicit verb belongs to the second clause;
   - the understood verb belongs to the first clause (*famam … exspectatio [superaret]*).

   Is the page's reading intended, and is a plural form needed? `tokens.qmd` has the same example.

## Questions to decide

5. **Verb forms not covered.** Should any of these be verbal expressions, and of what type?
   - **Historical infinitive:** an infinitive used as the main verb of a narrative sentence, e.g. *Catilina … agitare*. As written, it is neither `indirect statement` nor finite.
   - **Supine:** *venerunt questum*.
   - **Gerundive after verbs of arranging:** *pontem faciendum curavit*. Is this attributive `gerundive`, or a predicate of the object?
6. **Complementary and substantive infinitives.** Should these be stated explicitly as *not* verbal expressions? `syntactic-analysis.qmd` gives them their own relations (`complementary infinitive`, and `subject` etc.), and line 17 only implies the exclusion.
7. **The participle *exceptum* (line 113).** *sanguinem suum exceptum Deianirae dedit* also contains *exceptum*, but the explanation (line 115) discusses only *moriens* and *tinctas*. Under the "prefer circumstantial" rule (line 111), is *exceptum* a circumstantial participle too?
8. **Syntactic type of implied verbal expressions in general.**
   - Each example gives a type: `independent` (line 151), `circumstantial participle` (line 165), `dependent` (line 174), `independent` (line 180).
   - No general rule is stated. Presumably an implied verbal expression takes the type its construction would have if the verb were written out. Is that the rule?
   - Line 40 defines `independent` as "finite verbs", but implied tokens also receive that type.

## Clarifications to add

9. **Structure of "Handling implied verbal expressions" (lines 142–180).**
   - Line 144 says there are "two circumstances" that create an entry.
   - But the "Omitted forms of *sum*" section has three cases, one of which (the perfect passive, lines 154–158) does *not* create an entry.
   - Consider moving the perfect-passive case into a note, or saying explicitly "two circumstances; elided auxiliaries are not among them".
10. **`parataxis` wording (line 73).**
    - "Introduced by a verb" is how VU describes subordinating *words*. "Governed by a verb" would be clearer.
    - The other types are defined as kinds of *verbs* ("Finite verbs introduced by…"), but this one is defined as "a subordinate clause". Consider "A subjunctive verb governed without a subordinating word by…".
11. **Compound forms (line 16).** "Perfect and pluperfect tenses" should be "the perfect passive system", which also covers the future perfect. The page could also say once that the *participle* anchors the verbal expression, even though line 16 counts the compound as a "finite verb".

## Terminology

12. **"Verbal unit" vs "verbal expression".** The page uses several terms interchangeably:
    - the title, and lines 60 and 78: "verbal unit"
    - line 154: "verbal units table"
    - line 174: "verbal entry table"
    - line 144: "list of verbal expressions"
    - the class `VerbalExpression`

    Pick one term for the item and one for the list.
13.  ✅ **"Token graph" vs "syntax graph".** Lines 91 and 95 say "token graph"; lines 109 and 133 say "syntax graph".
14. ✅ **Line 9.** "e.g., for transitive active verbs" is the only remaining use of a retired semantic-type term. Consider "e.g., for active verbs with a direct object".

## Minor

15.  ✅ **Line 16:** "conjugated verbs forms" → "conjugated verb forms".
16.  ✅**Line 113:** "**Example**" is missing its colon.
17. **Duplicate examples.** *Legatos … ad pacem faciendam* and *Carthago delenda est* appear twice: at lines 21–27 and again at 124–133. That's fine, but the first pair could simply link forward.

## Related page (outside this review)

- `quarto/reference/vuvalues.qmd` is out of date:
  - It still lists the four semantic types.
  - Its syntactic types are missing `parataxis`, `circumstantial participle` and `gerundive`.
