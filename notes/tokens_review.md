# Review: `quarto/concepts/tokens.qmd`

Drafted 2026-10-15 on `wip`, against the working-tree version of `quarto/concepts/tokens.qmd`. The page is Neel's and read-only for Claude. It is unchanged since commit `f05a476`. This review covers that one page only, and line numbers refer to it as of this date.

## Contradictions to fix

1. ✅  **The praenomen definition conflicts with its own example (lines 28 and 32).** The definition covers names "in the form *praenomen nomen*", but line 32 classifies *L.* in *L. f.* as `praenomen`, and *L.* has no nomen. Either:
   - widen the definition to "a praenomen, abbreviated or not, with or without a following nomen"; or
   - classify a bare praenomen differently.

   `syntactic-analysis.qmd` has the same conflict: it says a praenomen is "always used in conjunction with a fully spelled out *nomen* or *cognomen*".
2.  ✅  **The elided-*sum* rule is overstated (line 122).** It says an elided *sum* always gets "an entry added to the list of verbal expressions". The perfect-passive case at line 139 correctly says it doesn't. Qualify the general sentence, e.g. "…unless the *sum* is the auxiliary of a compound form".
3.  ✅  **Identifier scope (line 12).** "Uniquely identified within a given citation context" disagrees with two other sources:
   - `analysisformat.qmd`, which requires implied-token IDs to be unique across the analysis;
   - `arsgrammatica/token_ids.py`, which writes IDs like `1.t0` that are unique across a whole run.

   The page should describe the actual scheme.

## Questions to decide

4. **Token URNs with the real IDs (the callout, line 16).** The example appends `t0` to the passage to get `…omar.tokens:1.t0`. With the code's composite IDs (`1.t0`), naive appending would give `…:1.1.t0`.
   - Say which part of the ID is appended.
   - How does an implied token, which has no place in the text, get a URN?
5. ✅  **Classification depends on context, not just "orthography and content" (line 23).**
   - *Agrippa* is a `praenomen` in *Agrippa Menenio* (line 37) but presumably `lexical` in *M. Agrippa* (line 30). Say so explicitly.
   - The abbreviated praenomina *M.*, *C.*, *D.* and *L.* collide with the Roman numerals 1000, 100, 500 and 50, and *V* and *I* also collide with words. Add a sentence on how these are resolved.
6. ✅   **Which enclitics count (lines 62–79)?** Only *-que* and *-ne* are illustrated.
   - Is *-ve* an enclitic?
   - Is *-cum* in *mecum* / *tecum* / *quibuscum* an enclitic?
   - Are *neque*, *atque*, *itaque*, *denique* and *undique* single `lexical` tokens, like *quisque*? *neque* in particular comes up constantly.
7. **Abbreviation at the end of a sentence (line 45).** In *…cos.* at the end of a sentence, does the period belong to the abbreviation token, to a separate `punctuation` token, or to both?
8. **Text and lemma of implied tokens (line 116).** The page says the text is `None`. What is the lemma?
   - `analysisformat.qmd` gives `sum` for an implied *sum*.
   - For an implied verb, is it *supero* (line 153)? And for the unnamed verb of speaking (line 162)?
   - For an implied substantive, is the lemma empty?
9. **The *superaret* example (lines 150–153).** *superaret* is written at the end of the *second* clause (*exspectationem … adventus admiratioque superaret*), and a singular verb with a compound subject is normal in Latin. The more natural reading is the reverse of the page's: the explicit verb belongs to the second clause, and the understood verb belongs to the first (*famam … exspectatio [superaret]*). Is the page's reading intended? Is a plural form needed at all?
10. **When to add an implied substantive (lines 168–172).** Latin omits subjects routinely. State that an implied substantive is added *only* when another token needs an attachment point, i.e. a relative pronoun's antecedent or a participle's substantive. Otherwise annotators, or the LM, may insert implied subjects everywhere.

## Clarifications to add

11. **Implied token types (lines 20–23 and 116).** The opening says every token gets "one of the following categories", but the list has only the six real types. Name the three implied types here too: `implied sum`, `implied verb` and `implied substantive`. These are the values `analysisformat.qmd` and `tokentypes.qmd` use. The section headings ("Elided forms of `sum`", "Understood repeated verb") don't match those values.
12. **The *consulibus* example (line 133).** "Agreeing with each of the two consuls' names": spell out that these are *Menenio* and *Postumio*, now that *Agrippa* is a praenomen. Also say how *consulibus* relates to the implied participle.
13. **Strings without citations (line 12).** Say how tokens are identified when there's no citation. `analysisformat.qmd` uses `sample:1` as the context in its example.
14. **Line 177:** a participle doesn't have an "antecedent". "The substantive that *interrogans* agrees with" would be clearer.

## Minor

15. ✅  **Line 83:** "phonetically" would be clearer as "spelled out as words".
16. ✅  **Line 96:** "Lexical tokens written in standard orthography" is close to circular. Consider "any word not in the categories above".
17. **Small slips:**
    -  ✅  "explict" (line 153)
    -  ✅ a stray " ." at the end of line 100
    -  ✅ no final period on line 54
    -  ✅ the callout on lines 111–112 says "tokens graph", where other pages say "syntax graph"
18.✅  **Line 54:** "Any *other*" punctuation relies on the reader inferring "other than the periods that belong to praenomina and abbreviations". Say that explicitly.
