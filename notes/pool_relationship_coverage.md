# A minimal set of pool sentences covering every relationship label

`relationship_labels.md` glosses all 26 `RelationLabel` values and `relationship_examples.md` gives each one a minimal illustration drawn from `syntax_model.md`'s own canned examples. This note is a third, complementary angle: rather than one hand-picked snippet per label, it finds the smallest set of whole SENTENCES from `scratch/pool` (the three real corpora already run through the pipeline there -- Cicero's *Pro Archia* 1.6, Livy 1.57, and the Vulgate's Genesis 42, 65 `.cex` files/sentences in all) whose combined relationships, as actually produced by `SentenceAnalysis`, cover all 26 values -- so each one can be pointed to as a genuine worked example from the corpus rather than a constructed one.

Every sentence in the pool was parsed with `read_analyses()`/`split_analysis_by_sentence()`, and the set of `relationship1`/`relationship2` values used anywhere in each sentence's own tokengraph slice was collected. All 26 labels turned out to be attested somewhere in the pool -- none are missing. An exhaustive search over all 43,680 three-sentence combinations (65 choose 3) found none that covers all 26, so four sentences is the true minimum (not just a greedy approximation); a further exhaustive search over all 677,040 four-sentence combinations (65 choose 4) found exactly nine that achieve full coverage, and the four below are the shortest of those nine by total token count.

## The four sentences

### 1. urn:cts:latinLit:phi0474.phi016.omar:3

Source: `cicero/cic_pro_arch_1_6_tokenized_6_urn_cts_latinLit_phi0474_phi016_omar_3.cex`

> sed ne cui vestrum mirum esse videatur, me in quaestione legitima et in iudicio publico, cum res agatur apud praetorem populi Romani, lectissimum virum, et apud severissimos iudices, tanto conventu hominum ac frequentia hoc uti genere dicendi quod non modo a consuetudine iudiciorum verum etiam a forensi sermone abhorreat, quaeso a vobis ut in hac causa mihi detis hanc veniam accommodatam huic reo, vobis, quem ad modum spero, non molestam, ut me pro summo poeta atque eruditissimo homine dicentem hoc concursu hominum litteratissimorum, hac vestra humanitate, hoc denique praetore exercente iudicium, patiamini de studiis humanitatis ac litterarum paulo loqui liberius, et in eius modi persona quae propter otium ac studium minime in iudiciis periculis que tractata est uti prope novo quodam et inusitato genere dicendi.

Relationships illustrated in this sentence (20): ablative, ablative absolute, adjectival, adverbial, apposition, aside, auxiliary, circumstantial participle, complementary infinitive, coordinating conjunction, dative, direct object, genitive, indirect statement, object of preposition, predicate, relative pronoun, subject, subordinating conjunction, unit verb.

### 2. urn:cts:latinLit:phi0474.phi016.omar:4

Source: `cicero/cic_pro_arch_1_6_tokenized_7_urn_cts_latinLit_phi0474_phi016_omar_4.cex`

> quod si mihi a vobis tribui concedi que sentiam, perficiam profecto ut hunc A. Licinium non modo non segregandum, cum sit civis, a numero civium verum etiam, si non esset, putetis asciscendum fuisse.

Relationships illustrated in this sentence (14): accusative, adjectival, adverbial, agent, coordinating conjunction, dative, genitive, indirect statement, object of preposition, praenomen, predicate, subject, subordinating conjunction, unit verb.

### 3. urn:cts:compnov:bible.genesis.vulgate:42.10

Source: `vulgate/vulgate_genesis_42_tokenized_10_urn_cts_compnov_bible_genesis_vulgate_42_10.cex`

> Qui dixerunt: Non est ita, domine, sed servi tui venerunt ut emerent cibos.

Relationships illustrated in this sentence (9): adjectival, adverbial, coordinating conjunction, direct object, direct quote, subject, subordinating conjunction, unit verb, vocative.

### 4. urn:cts:compnov:bible.genesis.vulgate:42.22

Source: `vulgate/vulgate_genesis_42_tokenized_21_urn_cts_compnov_bible_genesis_vulgate_42_22.cex`

> E quibus unus Ruben, ait: Numquid non dixi vobis: Nolite peccare in puerum: et non audistis me?

Relationships illustrated in this sentence (11): adverbial, apposition, attributive, complementary infinitive, coordinating conjunction, dative, direct object, direct quote, object of preposition, subject, unit verb.

## Which sentence illustrates which relationship

For each of the 26 labels, one concrete example (the related token and the token it relates to) drawn from the four sentences above, taking the first sentence in the list above where that label appears:

| Relationship | Example (token → related token) | Sentence |
|---|---|---|
| ablative | *conventu* → *agatur* | 1 |
| ablative absolute | *praetore* → *patiamini* | 1 |
| accusative | *quod* → *perficiam* | 2 |
| adjectival | *legitima* → *quaestione* | 1 |
| adverbial | *in* → *uti* | 1 |
| agent | *a* → *tribui* | 2 |
| apposition | *virum* → *praetorem* | 1 |
| aside | *spero* → *detis* | 1 |
| attributive | *E* → *unus* | 4 |
| auxiliary | *est* → *tractata* | 1 |
| circumstantial participle | *accommodatam* → *veniam* | 1 |
| complementary infinitive | *esse* → *videatur* | 1 |
| coordinating conjunction | *sed* → *quaeso* | 1 |
| dative | *cui* → *videatur* | 1 |
| direct object | *veniam* → *detis* | 1 |
| direct quote | *est* → *dixerunt* | 3 |
| genitive | *vestrum* → *cui* | 1 |
| indirect statement | *uti* → *videatur* | 1 |
| object of preposition | *quaestione* → *in* | 1 |
| praenomen | *A.* → *Licinium* | 2 |
| predicate | *mirum* → *esse* | 1 |
| relative pronoun | *quod* → *genere* | 1 |
| subject | *me* → *uti* | 1 |
| subordinating conjunction | *ne* → *quaeso* | 1 |
| unit verb | *videatur* → *ne* | 1 |
| vocative | *domine* → *est* | 3 |
