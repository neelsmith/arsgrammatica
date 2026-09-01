# `relationship1`/`relationship2` values

The full set of relation labels a tokengraph entry's `relationship1`/`relationship2` can take -- the `RelationLabel` `Literal` in `arsgrammatica/models.py` (both fields share one restricted set). Canonical definitions and worked examples are in `syntax_model.md`'s "Token-level table of dependencies"; this is just the flat list with a one-line gloss each.

`relationship2`/`relatedtoken2` is normally an overflow slot, used only when `relationship1`/`relatedtoken1` is already occupied by something else (e.g. a relative pronoun that's also its clause's subject). `coordinating conjunction` is the one label that genuinely uses both at once -- see its own entry below.

1. **unit verb** -- the verb of a clause. An independent verb's `relatedtoken1` is the reserved value `root` (never used as an actual token id); a dependent clause's verb instead points to its subordinating conjunction or relative pronoun.
2. **subordinating conjunction** -- a subordinating conjunction, linking to the verb of the clause it introduces (also covers an indirect question's interrogative word).
3. **relative pronoun** -- a relative pronoun, linking to its antecedent.
4. **subject** -- a noun/pronoun (or infinitive used as one) linking to the verb it's the subject of.
5. **direct object** -- a noun/pronoun linking to the transitive-active verb it's the object of.
6. **predicate** -- a noun/adjective linking to the linking verb it's the predicate complement of.
7. **agent** -- the preposition (*a*/*ab*) of a passive verb's ablative-of-agent phrase, linking to that verb.
8. **auxiliary** -- a participle linking to the accompanying form of *sum* in a compound perfect-passive/future-active verb form.
9. **object of preposition** -- a noun/pronoun linking to the preposition governing it.
10. **adverbial** -- an adverb, or a prepositional phrase used adverbially, linking to the verb it modifies.
11. **attributive** -- a prepositional phrase linking to the noun it modifies.
12. **adjectival** -- an adjective (or gerundive) linking to the noun it agrees with.
13. **genitive** -- a genitive noun linking to the noun or verb it depends on.
14. **dative** -- a dative noun linking to the noun or verb it depends on.
15. **ablative** -- an ablative noun linking to the noun or verb it depends on (also covers the *opus est* idiom's ablative).
16. **accusative** -- an accusative relation that isn't a direct object (accusative of place-to-which, extent, etc.), linking to the verb or noun it depends on.
17. **vocative** -- a vocative noun, linking to the verb of the clause it appears in.
18. **direct quote** -- a direct-quotation verbal expression's verb, linking back to the verb of the clause it interrupts.
19. **aside** -- a parenthetical aside's verb, linking back to the verb of the clause it interrupts.
20. **indirect statement** -- an indirect-statement infinitive, linking back to the governing verb of saying/thinking/perceiving.
21. **circumstantial participle** -- a participle linking to the noun/pronoun (real or implied) it agrees with.
22. **ablative absolute** -- the noun/pronoun of a true ablative absolute, linking back to the main verb when it has no other syntactic connection to the clause.
23. **coordinating conjunction** -- a coordinating conjunction linking the two items (nouns, adjectives, prepositional phrases, or verbal expressions) it joins. For one pair it sets *both* `relatedtoken1`/`relationship1` and `relatedtoken2`/`relationship2` (one per side of the pair); a repeated connector (*et...et...et*) instead chains `relatedtoken2` to the next/preceding connector.
24. **apposition** -- a noun in apposition, linking back to the first noun it stands in apposition to.
25. **complementary infinitive** -- an infinitive completing a governing verb like *volo*/*incipio*/*audeo*/*licet*/*decet*, linking to that verb (not its own verbal-expression anchor -- no separate `verbalunits` entry).
26. **praenomen** -- an abbreviated Roman first-name token, linking to the lexical token spelling out the name it abbreviates.

Not every relation gets its own label: an infinitive used as an ordinary noun takes whatever normal noun relation fits (`subject`, `direct object`, ...), a gerund likewise takes an ordinary noun relation (usually `genitive`), and a gerundive is just `adjectival` like any other adjective.
