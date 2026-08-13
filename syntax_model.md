# Overview

This repository hosts a python package leveraging language models with `dspy` to analyze the syntax of passages of Latin. The unique analytical scheme is specific to Latin, and is documented here.





In this scheme, analysis of a passage of Latin is expressed in two related structures:


- a list of verbal expressions, generally corresponding to clauses in an English translation
- a token-level table capturing principal relations in a dependency graph

This draft describes a first, partial implementation of the scheme.

## Table of verbal expressions

"Verbal expressions" are subject-verb ideas that most frequently correspond to clauses in an English translation. (Of course in Latin the subject may be implicit where that is not possible in English.) Every *finite verb* constitutes a verbal expression. Latin finite verbs include the compound forms of the perfect and pluperfect tenses (composed of a past participle plus a form of *sum*) as well as conjugated forms identifiable by tense-mood-voice-person-number. In addition, *infinitives* constitute a verbal expression when they are part of an expression in indirect speech.

In this scheme, verbal expressions are classified according to:

1. their *syntactic type*, as either *independent* (also called "main" or "principal") verbs or *dependent* ("subordinate" or "secondary") verbs. For example, in the sentence *principes Albanorum in patres, ut ea quoque pars rei publicae cresceret, legit* the verb *legit* is an *independent* verbal expression, and *cresceret* is dependent (introduced by the subordinating conjunction *ut*).
2. by their *semantic type* ,as *transitive active*, *transitive passive*, *intransitive* or a *linking verb*. In the sentence *principes Albanorum in patres, ut ea quoque pars rei publicae cresceret, legit*m the verb *legit* is *transitive active*; and *cresceret* is *intransitive*. In *urbs a Romulo condita est*, the compound verb *condita est* is *transitive passive*.  In the sentence *Etruria erat vicina*, the verb *erat* is a *linking verb*.


## Token-level table of dependencies

### Tokenization

The passage of Latin must be tokenized, and each token classified as one of:

-  a *punctuation* token. Example: "." in the phrase *arma virumque cano*
-  an *enclitic* token. Example: the enclitic *que* in the phrase *arma virumque cano.* Tokenization of enclitics must consider the context. Example: in the phrase, *aequa ratione imperat*, the string *ratione* is a single lexical token (noun in the ablative singular); in the phrase *ratione docet?*, the string *ratione* represents the enclitic token *ne* (question words) with the lexical token *ratio* (noun in the nominative singular).
-  a *lexical* token. Example: the tokens *arma*, *virum* and *cano* in the phrase *arma virumque cano.*
- a *praenomen*, including its punctuating period. Example: *M.* in the phrase *M. Agrippa L. f. cos. tertium fecit*
- other *abbreviation*, including its period. Example: *f.* and *cos.* in the the phrase *M. Agrippa L. f. cos. tertium fecit*
- a *numeral* written numerically. Example: *XXV* in the phrase *hiberna aberant ab eo milia passuum XXV*




### Syntactic relations among tokens

In the first phase of implementing our syntax model, we will record a limited set of relations among tokens:


- agent of passive verbs: if a passive verb includes an expression for agent using *a* or *ab* plus a nominal expression in the ablative, *a* or *ab* should have the passive verb token as *relation1* and *agent* as the value of *relationship1*. The noun or pronoun constructed with *a/ab* should have the id of *a/ab* as its *relation1* and *object of preposition* as its*relationship1* value.
- verb of a dependent clause: the verb of an dependent clause must be related to a subordniating word, either a subordinating conjunction or a relative pronoun. *relatedtoken1* will be the ID of the conjunction of pronoun, and the value of *relationship1* will be *unit verb*. 
In the sentence  *Hercules cum gregem perlustrasset, pergit ad proximam speluncam*, the verb *perlustrasset* is releated to the subordinating conjunction *cum* as its unit verb.
- subordinating conjunctions: *relation1* will be the ID of the verb in their governing (superior clause), and the *relationship1* will be *subordinating conjunction*. In the sentence  *Hercules cum gregem perlustrasset, pergit ad proximam speluncam*, the  conjunction *cum* is releated as a 
subordinating conjunction to the main verb *pergit*.
- relative pronouns: *relation1* will be the ID of its antecedent, and *relationship1* will be *relative pronoun*. 
In *laboris praemium petam, ut me a conspectu malorum, 
quae nostra tot per annos vidit aetas, avertam.* the relatie pronoun *quae* will have the ID of *malorum* as its antecedent.
- noun or pronoun serving as the subject of a verbal expression: *relatedtoken1* will be the id of the token of the verb. If it is a compound verb form in the perfect passive system, this should be the id of the form of *sum*. The value of *relation1* will be *subject*. The same values will be used for *relation2* and *relationship2* of relative pronouns.



- noun or pronoun functioning as direct object of a verbal expression: *relatedtoken1* will be the id of the token of the verb. If it is a compound verb form in the perfect passive system, this should be the id of the form of *sum*. The value of *relation1* will be *direct object*. The same values will be used for *relation2* and *relationship2* of relative pronouns.

- prepositional phrases: prepositional phrases either stand in an adverbial relation to a verbal expression or in an attributive relation to a nominal expression. (In "The man in the red coat walked down the street", "in the red coat" is an attributive expression describing "The man", while "down the street" is an adverbial expression modifying "walked." ) The preposition should have the ID of the corresponding verb or noun expression for *relation1* and the value of *relationship1* should be *adverbial* or *attributive*. The noun or pronoun governed by the preposition should have the value *object of preposition*. The same values will be used for *relation2* and *relationship2* of relative pronouns.


## Incomplete status

This describes only the principal syntactic relationships analyzed. Therefore not all tokens will have a value for *relation1* and *relationship1* in the current implmentation.