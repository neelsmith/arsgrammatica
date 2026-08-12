"""
DSPy program that analyzes the syntax of a Latin passage according to the scheme documented in notes.md: a table of verbal expressions, plus a token-level dependency graph.

Pipeline:
  1. tokenize()   -- deterministically segments the passage into tokens with fixed ids (see tokenizer.py).
  2. SyntaxAnalysis -- a dspy.Signature that takes the passage + token list and produces `verbalunits` and `tokengraph`, using the ids handed to it.
  3. validate()   -- a light sanity check that every id the LM refers to in its output actually exists in the input token list, so malformed output is easy to spot.

Run this file directly for a quick smoke test against the configured LM:
    python latin_syntax_dspy.py

For a test that doesn't need network access to the school proxy, see `test_pipeline.py`, which drives the same signature with dspy's DummyLM.
"""

from typing import List

import dspy

from .models import Token, VerbalExpression, TokenAnalysis
from .tokenizer import tokenize


# ---------------------------------------------------------------------------
# Signature
# ---------------------------------------------------------------------------

class SyntaxAnalysis(dspy.Signature):
    """Analyze the syntax of a passage of Latin according to a two-part scheme:

    (1) a list of verbal expressions: every finite verb, and every infinitive
        used in indirect speech, classified by syntactic type
        (independent/dependent) and semantic type (transitive
        active/transitive passive/intransitive/linking verb).

    (2) a token-by-token dependency graph. For each token, record up to two
        relations to other tokens (by id), using only these relation labels:

        - agent: the preposition 'a'/'ab' introducing the agent of a passive
          verb has relatedtoken1 -> the passive verb's id, relationship1 =
          'agent'. The noun/pronoun governed by that 'a'/'ab' has
          relatedtoken1 -> the id of 'a'/'ab', relationship1 = 'object of
          preposition'.
        - unit verb: the verb of a dependent clause has relatedtoken1 -> the
          id of its subordinating conjunction or relative pronoun,
          relationship1 = 'unit verb'.
        - subordinating conjunction: the conjunction has relatedtoken1 -> the
          id of the verb of the clause it subordinates to, relationship1 =
          'subordinating conjunction'.
        - relative pronoun: relatedtoken1 -> the id of its antecedent,
          relationship1 = 'relative pronoun'.
        - subject / direct object: a noun or pronoun serving as subject or
          direct object has relatedtoken1 -> the id of the verb (or, for
          perfect passive compound forms, the id of the form of 'sum'),
          relationship1 = 'subject' or 'direct object'. If the token is a
          relative pronoun already using relatedtoken1/relationship1 for its
          antecedent link, put the subject/object relation in
          relatedtoken2/relationship2 instead.
        - prepositional phrases: the preposition has relatedtoken1 -> the id
          of the verb (adverbial) or noun (attributive) it modifies,
          relationship1 = 'adverbial' or 'attributive'. The noun/pronoun it
          governs has relatedtoken1 -> the id of the preposition,
          relationship1 = 'object of preposition' (or relatedtoken2/
          relationship2 if relatedtoken1 is already used for a
          relative-pronoun link).

        Only assign relations described above. Leave relatedtoken/
        relationship fields unset for tokens with no relation of these
        kinds -- not every token will have one. Use only the token ids given
        in the input `tokens` list; never invent new ids.
    """

    passage: str = dspy.InputField(desc="The Latin passage to analyze, exactly as written.")
    tokens: List[Token] = dspy.InputField(
        desc="Pre-segmented tokens of the passage, in order, with fixed ids. Reference these ids in your output; do not create new ones."
    )
    verbalunits: List[VerbalExpression] = dspy.OutputField(
        desc="One entry per verbal expression (finite verb, or infinitive used in indirect speech) in the passage."
    )
    tokengraph: List[TokenAnalysis] = dspy.OutputField(
        desc="One entry per token in `tokens`, in the same order, with its type and any relations."
    )


analyze = dspy.ChainOfThought(SyntaxAnalysis)


# ---------------------------------------------------------------------------
# Runner + validation
# ---------------------------------------------------------------------------

def validate(tokens: List[Token], result) -> List[str]:
    """Check that every id the LM produced actually exists among `tokens`.
    Returns a list of human-readable problem descriptions (empty if clean)."""
    valid_ids = {t.id for t in tokens}
    problems = []

    for tok in result.tokengraph:
        if tok.id not in valid_ids:
            problems.append(f"tokengraph entry has unknown id {tok.id!r}")
        for field in ("relatedtoken1", "relatedtoken2"):
            val = getattr(tok, field)
            if val is not None and val not in valid_ids:
                problems.append(f"token {tok.id!r} {field}={val!r} is not a known token id")

    for vu in result.verbalunits:
        if vu.id not in valid_ids:
            problems.append(f"verbal expression id {vu.id!r} is not a known token id")

    return problems


def analyze_passage(passage: str):
    """Tokenize `passage`, run it through the SyntaxAnalysis program, and
    validate the result. Returns (tokens, result)."""
    tokens = tokenize(passage)
    result = analyze(passage=passage, tokens=tokens)

    problems = validate(tokens, result)
    if problems:
        print("Validation warnings:")
        for p in problems:
            print(f"  - {p}")

    return tokens, result


def print_analysis(tokens: List[Token], result):
    print("Tokens:")
    for t in tokens:
        print(f"  {t.id:>4}  {t.text}")

    print("\nVerbal expressions:")
    for vu in result.verbalunits:
        print(f"  id={vu.id}  syntactic_type={vu.syntactic_type}  semantic_type={vu.semantic_type}")

    print("\nToken graph:")
    for tok in result.tokengraph:
        rels = []
        if tok.relationship1:
            rels.append(f"{tok.relationship1} -> {tok.relatedtoken1}")
        if tok.relationship2:
            rels.append(f"{tok.relationship2} -> {tok.relatedtoken2}")
        rel_str = "; ".join(rels) if rels else "-"
        vu_str = f" [verbal unit {tok.verbalunitid}]" if tok.verbalunitid else ""
        print(f"  {tok.id:>4}  {tok.token:<15} type={tok.tokentype:<11} lemma={tok.lemma or '-':<15} {rel_str}{vu_str}")



