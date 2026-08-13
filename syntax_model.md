# Overview

This repository hosts a python package leveraging language models with `dspy` to analyze the syntax of passages of Latin. The unique analytical scheme is specific to Latin, and is documented here.

In this scheme, analysis of a passage of Latin is expressed in two related structures:

- a list of verbal expressions, generally corresponding to clauses in an English translation
- a token-level table capturing principal relations in a dependency graph

This draft describes a first, partial implementation of the scheme.

## Table of verbal expressions

"Verbal expressions" are subject-verb ideas that most frequently correspond to clauses in an English translation. (Of course in Latin the subject may be implicit where that is not possible in English.) This scheme identifies three constructions as verbal expressions:

1. *Every finite verb* constitutes a verbal expression. Latin finite verbs include the compound forms of the perfect and pluperfect tenses (composed of a past participle plus a form of *sum*) as well as conjugated verbs forms identifiable by tense-mood-voice-person-number. 
2. *Infinitives* constitute a verbal expression when they are part of an expression in indirect speech.
3. *Participles* constitute a verbal expression when they have a *predicate* sense rather than purely *attributive* sense. For example, in the sentence *gloria est consentiens laus bonorum*, the participle *consentiens* has an attributive sense with *laus*, "universal praise": this is *not* a verbal expression. But in the sentence *Anco regnante Lucumo, vir inpiger ac divitiis potens, Romam commigravit* the participle *regnante* has a predicate sense with *Anco* "while Ancus was reigning..."

In this scheme, verbal expressions are classified according to:

1. their *syntactic type*, as either *independent* (also called "main" or "principal") verbs or *dependent* ("subordinate" or "secondary") verbs. For example, in the sentence *principes Albanorum in patres, ut ea quoque pars rei publicae cresceret, legit* the verb *legit* is an *independent* verbal expression, and *cresceret* is dependent (introduced by the subordinating conjunction *ut*).
2. by their *semantic type* ,as *transitive active*, *transitive passive*, *intransitive* or a *linking verb*. In the sentence *principes Albanorum in patres, ut ea quoque pars rei publicae cresceret, legit*m the verb *legit* is *transitive active*; and *cresceret* is *intransitive*. In *urbs a Romulo condita est*, the compound verb *condita est* is *transitive passive*.  In the sentence *Etruria erat vicina*, the verb *erat* is a *linking verb*.


## Token-level table of dependencies

### Tokenization

The textual content of Latin passages with citation references may be analyzed; the analyzing program will keep track of the citation. 

The text of the passage must be tokenized, and each token classified as one of:

-  a *punctuation* token. Example: "." in the phrase *arma virumque cano*
-  an *enclitic* token. Example: the enclitic *que* in the phrase *arma virumque cano.* Tokenization of enclitics must consider the context. Example: in the phrase, *aequa ratione imperat*, the string *ratione* is a single lexical token (noun in the ablative singular); in the phrase *ratione docet?*, the string *ratione* represents the enclitic token *ne* (question words) with the lexical token *ratio* (noun in the nominative singular).
-  a *lexical* token. Example: the tokens *arma*, *virum* and *cano* in the phrase *arma virumque cano.*
- a *praenomen*, including its punctuating period. Example: *M.* in the phrase *M. Agrippa L. f. cos. tertium fecit*
- other *abbreviation*, including its period. Example: *f.* and *cos.* in the the phrase *M. Agrippa L. f. cos. tertium fecit*
- a *numeral* written numerically. Example: *XXV* in the phrase *hiberna aberant ab eo milia passuum XXV*




### Syntactic relations among tokens

In the first phase of implementing our syntax model, we will record the following set of relations among tokens.


#### Verbs and their principal construction

- verb of an independent clause: the `relation1` of independent verbs has the special value `root` which must not be used as identifier for any token. Its 'relationship1` value is `unit verb`. Example: in *arma virumque cano*, *cano* is an independent verb with `relation1` value `root`, and `relationship1` value `unit verb`.

- multi-word compound verb forms in the passive: the conjugated form of *sum* will be taken as the verb of the verbal unit. The associated participle will relate to the form of *sum* as its *auxiliary*. Example: in *urbs condita est* with token ids `t1`, `t2` and `t3`, the participle *condita* has for its `relation1` the value `t3` (*est*), and for `relationship1`, *auxiliary*.

- verb of a dependent clause: the verb of a dependent clause must be related to a subordinating word, either a subordinating conjunction or a relative pronoun. *relation1* will be the ID of the conjunction of pronoun, and the value of *relationship1* will be *unit verb*.  In the sentence  *Hercules cum gregem perlustrasset, pergit ad proximam speluncam*, the verb *perlustrasset* is releated to the subordinating conjunction *cum* with the value of `unit verb` for `relationship1`.

- agent of passive verbs: if a passive verb includes an expression for agent using *a* or *ab* plus a nominal expression in the ablative, *a* or *ab* should have the passive verb token as *relation1* and *agent* as the value of *relationship1*. The noun or pronoun constructed with *a/ab* should have the id of *a/ab* as its *relation1* and *object of preposition* as its*relationship1* value. Example: if *urbs a Romulo condita est* is tokenized with the IDs `t1`, `t2`...`t5`, then `t2` (*a*) will have a `relation1` of `t5` (*est*), and `relationship1` of `agent`. The token *Romulo* will be related to `t2` as a normal `object of preposition` (see below).


- subordinating conjunctions: *relation1* will be the ID of the verb in their governing (superior clause), and the *relationship1* will be *subordinating conjunction*. In the sentence  *Hercules cum gregem perlustrasset, pergit ad proximam speluncam*, the  conjunction *cum* is releated as a subordinating conjunction to the main verb *pergit*.  Here's a partial extract of the relations resulting from this sentence:

| ID | token | relation1 | relationship1 |
| --- | --- | --- | --- |
| cum | t2 | t5 | subordinating conjunction |
| perlustrasset | t4 |  t2 | unit verb |
| pergit | t5 | | |


- relative pronouns: *relation1* will be the ID of its antecedent, and *relationship1* will be *relative pronoun*. Example: here is a partial extract from an analysis of the sentence *Latini, cum quibus ictum foedus erat, sustulerant animos.*


| ID | token | relation1 | relationship1 | relation2 | relationship2 |
| --- | --- | --- | --- | --- | --- |
| Latini | t1 | t9 | subject | | |
| cum | t3 | | | | | 
| quibus | t4 | t1 | relative pronoun | t3 | object of preposition |
| ictum | t5 | t7 | auxiliary | | |
| erat | t7 | t4 | unit verb | | |
| sustulerant | t9 | | | 
| animos | t10 | t9 | direct object | | 


- noun or pronoun serving as the subject of a verbal expression: *relation1* will be the id of the token of the verb. If it is a compound verb form in the perfect passive system, this should be the id of the form of *sum*. The value of *relation1ship* will be *subject*.

- noun or pronoun functioning as direct object of a verbal expression: *relation1* will be the id of the token of the verb. If it is a compound verb form in the perfect passive system, this should be the id of the form of *sum*. The value of *relation1ship* will be *direct object*.

- noun or pronoun functioning as the predicate of a linking verb: *relation1* will be the id of the token of the verb. If it is a compound verb form in the perfect passive system, this should be the id of the form of *sum*. The value of *relationship1* will be *predicate*. Example: In the sentence *Lucumo Demarati Corinthii filius erat*, *Lucumo* is the subject of the linking verb *erat*, and *filius* is the predicate.



#### Adjectives, adverbs, prepositional phrases


- adjectives: if an adjective is used as a substantive, it is treated as a noun or pronoun. When it describes a noun, it has the noun's id as its `relation1`, and `adjectival` as its `relationship1`. In the sentence *Lucumo superfuit patri bonorum omnium heres*, the adjective *omnium* will have the id of *bonorum* as its `relation1` and the `relationship1` value will be `adjectival`. The token `bonorum` will be treated as a noun (see below).

- adverbs: adverbs have the id of the verb they modify as `relation1`, with `relationship1` value `adverbial`. In the sentence *ad Ianiculum forte ventum erat*, the adverb *forte* will take the id of `erat` for `relation1` with `relationship1` value `adverbial`.  `ventum` will also be related to `erat` but with `relationship1` value `auxiliary`.

- prepositional phrases: prepositional phrases either stand in an adverbial relation to a verbal expression or in an attributive relation to a nominal expression. 
   - attributive to a noun: in the phrase *pugna ad Cannas*, "the battle near Cannae," the prepositional phrase *ad Cannas* is attributive. *ad* will have as *relation1* the id of *pugna*, and its *relationship1* will be *attributive*. (*Cannas* will be the object of the preposition, see below.)
   - adverbial related to a verb: in the sentence *statua Atti in comitio in gradibus ipsis ad laevam curiae fuit*, the three prepositional phrases *in comitio*, *in gradibus ipsis* and *ad laevam curiae* will each each have for `relation1` the id of the verb *fuit*, with the `relationship1` value `adverbial`.



### Noun relations





## Incomplete status

This describes only the principal syntactic relationships analyzed. Therefore not all tokens will have a value for *relation1* and *relationship1* in the current implmentation.


### TBA

- gerunds and gerundives

