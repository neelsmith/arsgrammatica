# Review: `quarto/reference/analysisformat.qmd`

Drafted 2026-10-15 on `wip` against the working-tree version of the file, which is Neel's and read-only for Claude. This note covers that one file only. Line numbers refer to it as of this date.

Already fixed:
- the malformed implied-token row;
- the `relationship1` header;
- the extra field in the punctuation rows;
- the stray `cano` lemma.

All data rows now have 7 fields, matching their header.

## Errors to fix

1. ✅ **Line 9 wording.**
   - "This means it that concatenating…" should be "This means that concatenating…".
   - The same sentence repeats itself: "identified by labels for each, identified by the labels…".
2. ✅ **Line 113 wording.**
   - "producse" should be "produces".
   - "with keys (`MODEL`, `CONTEXT` and `REASONING`)" reads awkwardly; "with the keys `MODEL`, `CONTEXT` and `REASONING`" is simpler.
3. ✅ **Line 118:** the `CONTEXT` range ends at `t3`, but the `#!sentences` example (line 27) now ends the sentence at `t4`.
4. ✅ **Line 119:** the `REASONING` example still uses retired vocabulary:
   - "transitive active"
   - `relatedtoken1`/`relatedtoken2`
   - "coordinating conjunction"

## Questions to decide

5. ✅ **Which sentence an implied token belongs to.** Line 91 lets an implied token appear anywhere in `#!tokens`. But `#!sentences` defines a sentence only by its first and last token, so in a file with several sentences nothing ties an implied token to its sentence.
   - One option is to require implied rows to fall inside their sentence's run of rows, in any position there.
   - That rule would also rule out an implied row landing between the repeated rows of another token, which line 91 currently permits.
6. ✅ **`related` IDs across passages.** `related` holds a bare token ID, but `tokens.qmd` says IDs are unique only within a citation context. If a sentence spans two passages (`context_begin` ≠ `context_end`) and IDs restart at `t0` in each, `related = t0` is ambiguous. Either:
   - IDs must be unique across the whole analysis, or
   - `related` needs a context too.
7. ✅ **Implied-token IDs.** `t2_implied` appears only in the example. Is there a required pattern? How are two implied tokens near the same position kept distinct?
8. ✅ **The `context` of an implied token.** With URN-cited text, which URN does an implied token get?
9. ✅ **Empty `context`.** The implied-token example leaves `context` empty on every row.
   - If an empty `context` is allowed for bare strings with no citation, say so.
   - Otherwise give the example a URN like the other examples.
10. ✅ **The delimiter.** "By default, the pipe character" implies the delimiter can change.
    - How does a file declare a different delimiter?
    - How is a `|` inside a field handled?
11. ✅ **Token URNs vs. `CONTEXT`.** The two pages build token references differently. Should they match?
    - The `#!lm` `CONTEXT` uses `…omar:1.1.t0`.
    - The callout in `tokens.qmd` extends the work component with a `tokens` exemplar: `…omar.tokens:1.1.t0`.

## Clarifications to add

12. ✅ **Line 51.**
    ✅ - Add "except implied tokens (see below)" after "ordered by … document order". Otherwise the rule contradicts line 91.
    ✅ - "two fields identifying a token by its ID" should refer to the ID of the *related* token.
     ✅ - Mention that this value may be the reserved `root` (which can never be a token ID) or an implied token's ID.
13.  ✅ **Line 58:** say explicitly that punctuation rows leave `lemma`, `related` and `relationship` empty, as the examples do.
14. **Implied-token example (lines 94–107).**
    ✅ - Showing the matching `#!verbal_units` row (`|t2_implied|independent`) would illustrate an implied token as the anchor of a verbal unit.
    t2_implied- Its relations are the reverse of the table for the same sentence in `syntactic-analysis.qmd`:

| | this page | `syntactic-analysis.qmd` |
|---|---|---|
| *omnia* | `subject` | `adjectival` → *praeclara* |
| *praeclara* | `adjectival` → *omnia* | `subject` |

    ✅ - The token type `implied sum` should match `quarto/reference/tokentypes.qmd`. That list uses `continued verb` where `syntactic-analysis.qmd` uses `implied verb`.
15. ✅ **Line 15:** the example's text content should include the final period (`arma virumque cano.`), since the token tables include `t4`.
