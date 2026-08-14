"""
DSPy program that segments a sequence of citation-labeled Latin source
units into sentences, and each sentence into tokens -- replacing
tokenizer.py's deterministic, regex-based segmentation with an LLM-driven
one, per syntax_model.md's "Tokenization" section (context-dependent
enclitic splitting, abbreviation recognition), while also tracking which
citation unit each token came from.
 
Input is `sources: List[CitedText]` rather than a single passage string
specifically so that a sentence spanning more than one citation unit (a
verse sentence running across two lines, say) is representable: sentence
boundaries do not need to respect CitedText boundaries, but every token
still records the citation it came from via Token.citation.
 
This is a separate stage from SyntaxAnalysis (latin_syntax_dspy.py) on
purpose: SegmentPassage's output (List[Sentence]) still feeds
SyntaxAnalysis as `tokens: List[Token]` per sentence, unchanged -- adding
citation tracking here required no changes to SyntaxAnalysis at all, since
Token.citation just rides along and SyntaxAnalysis never needs to look at
it.
 
Run this file directly for a quick smoke test against the configured LM:
    python segmentation_dspy.py
"""
 
from typing import List
 
import dspy
 
from .models import CitedText, Sentence
 
 
class SegmentPassage(dspy.Signature):
    """Segment a sequence of citation-labeled Latin source units into
    sentences, and each sentence into tokens, following syntax_model.md's
    tokenization scheme.
 
    `sources` is given in reading order; treat its units' text as one
    continuous passage for sentence-splitting purposes -- a sentence may
    start in one unit's text and finish in the next one's, and often will
    in continuous verse or prose. Every token you produce must carry the
    `citation` of whichever `sources` unit its surface text came from, even
    for a sentence that spans more than one unit.
 
    - Split into sentences at sentence-ending punctuation (. ? !). A period
      after a praenomen (e.g. "M.") or another abbreviation (e.g. "f.",
      "cos.") is NOT a sentence boundary.
 
    - Within each sentence, segment tokens as: lexical, enclitic,
      punctuation, numeral (Arabic or Roman), praenomen (a letter plus its
      period), or other abbreviation (letters plus a period, e.g. "f.",
      "cos."). Praenomina and other abbreviations are each a single token
      including their period -- never split the letters from the period the
      way ordinary sentence-final punctuation is separated.
 
    - Enclitic splitting (-que, -ve, -ne) must consider context, not just
      the trailing letters. Only split off an enclitic when the remainder
      is itself a real word AND context supports that reading. Ordinary
      words that happen to end in "que"/"ve"/"ne" (e.g. "sine", "bene")
      are never split -- their whole spelling is the word, full stop.
 
      For "-ne" specifically: only read it as the interrogative particle
      when the sentence is a yes/no question AND its token is that
      question's first word. A sentence ending in "?" is a yes/no
      question -- that is your signal, use it directly rather than
      guessing from meaning alone. For example:
        - "aequa ratione imperat." does not end in "?", so it is not a
          question. ratione stays one token (ablative of ratio),
          regardless of its position in the sentence.
        - "ratione docet?" ends in "?": a yes/no question. ratione is
          that question's first word, so it splits into ratio
          (nominative) + the interrogative enclitic -ne.
      If a sentence does not end in "?", never split off an interrogative
      "-ne" -- not even from a sentence-initial word ending in "-ne".
 
    - Assign token ids sequentially across the WHOLE input, in reading
      order: t0, t1, t2, .... Do not restart numbering at each sentence or
      at each source unit. Every token, across every sentence and every
      source unit, has a unique id, and running this on the same `sources`
      again must produce the same ids for the same tokens.
    """
 
    sources: List[CitedText] = dspy.InputField(
        desc="Citation-labeled source units, in reading order, to segment as one continuous passage."
    )
    sentences: List[Sentence] = dspy.OutputField(
        desc="The sentences found across all of `sources`, in order. Token ids are global (see instructions); each token's `citation` names the source unit it came from."
    )
 
 
segment = dspy.ChainOfThought(SegmentPassage)
 
 
def segment_sources(sources: List[CitedText]) -> List[Sentence]:
    """Run the segmentation stage and return its sentences."""
    result = segment(sources=sources)
    return result.sentences