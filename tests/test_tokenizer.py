"""
Unit tests for tokenize() itself -- no DSPy, no LM, no DummyLM. This is pure
string-in/Token-list-out testing of the deterministic pre-segmentation step,
independent of the syntax-analysis scheme entirely.
 
Note tokenize() only returns Token(id, text) pairs -- the "lexical" /
"enclitic" / "punctuation" / etc. classification tokenizer.py computes
internally to decide how to split a raw token is not exposed on Token
itself; that classification is the LM's job later, as part of
TokenAnalysis.tokentype.
 
The tests marked xfail(strict=True) below describe the contextually-aware
tokenizer specified in syntax_model.md's "Tokenization" section, which
tokenizer.py does not implement yet. strict=True means: once you implement
the fix and one of these starts passing, pytest reports XPASS and fails the
run until you remove that test's xfail marker -- a nudge to "graduate" it
rather than a note that lingers forever.
"""
 
import pytest
 
from arsgrammatica.tokenizer import tokenize
 
 
def _text(passage):
    return [t.text for t in tokenize(passage)]
 
 
def _ids_and_text(passage):
    return [(t.id, t.text) for t in tokenize(passage)]
 
 
# ---------------------------------------------------------------------------
# Already-correct behavior -- regression guards, not new specification.
# ---------------------------------------------------------------------------
 
def test_enclitic_splits_off_que():
    # The project's own canonical example (syntaxer_main.py's default).
    assert _ids_and_text("arma virumque cano.") == [
        ("t0", "arma"),
        ("t1", "virum"),
        ("t2", "que"),
        ("t3", "cano"),
        ("t4", "."),
    ]
 
 
def test_praenomen_with_period_stays_one_token():
    # "M." and "L." must not split into letter + "." the way ordinary
    # punctuation would. Worth guarding explicitly once abbreviation
    # handling is added nearby -- easy to break by accident.
    assert _ids_and_text("M. Agrippa L. fecit.") == [
        ("t0", "M."),
        ("t1", "Agrippa"),
        ("t2", "L."),
        ("t3", "fecit"),
        ("t4", "."),
    ]
 
 
def test_numeral_digits_stay_one_token():
    # A digit run is one numeral-shaped token, not split character by
    # character; spelled-out numbers (decem) are ordinary lexical tokens.
    assert _ids_and_text("Anno 10 natus est.") == [
        ("t0", "Anno"),
        ("t1", "10"),
        ("t2", "natus"),
        ("t3", "est"),
        ("t4", "."),
    ]
 
 
def test_bare_enclitic_word_is_not_split_into_an_empty_base():
    # "que" on its own has nothing before the "que" suffix to be a base, so
    # it must fall through to a single ordinary token rather than splitting
    # into ("", "que").
    assert _ids_and_text("que.") == [("t0", "que"), ("t1", ".")]
 
 
def test_ids_are_sequential_regardless_of_content():
    for passage in (
        "arma virumque cano.",
        "M. Agrippa fecit.",
        "Gallia est omnis divisa in partes tres.",
    ):
        ids = [t.id for t in tokenize(passage)]
        assert ids == [f"t{i}" for i in range(len(ids))]
 
 
def test_empty_passage_returns_no_tokens():
    assert tokenize("") == []
 
 
def test_roman_numeral_is_already_one_token():
    # syntax_model.md's numeral example (XXV) is a *classification* question
    # for the LM, not a segmentation bug -- tokenize() already keeps it
    # intact. This pins that so nobody "fixes" segmentation that isn't
    # broken while working on the classification side (models.py's
    # tokentype Literal, not tokenizer.py).
    assert _text("hiberna aberant ab eo milia passuum XXV.") == [
        "hiberna", "aberant", "ab", "eo", "milia", "passuum", "XXV", ".",
    ]
 
 
# ---------------------------------------------------------------------------
# Not implemented yet -- syntax_model.md's new "Tokenization" clarification.
# Each xfail names the specific gap; remove the marker as you close it.
# ---------------------------------------------------------------------------
 
@pytest.mark.xfail(strict=True, reason="_split_enclitic false-positives on real words ending in que/ve/ne")
def test_enclitic_split_does_not_false_positive_on_real_words():
    # sine ("without") and bene ("well") are never enclitic -- the whole
    # word is a real word on its own, so nothing should be split off.
    assert _text("sine ira et studio.") == ["sine", "ira", "et", "studio", "."]
    assert _text("bene vixit.") == ["bene", "vixit", "."]
 
 
@pytest.mark.xfail(strict=True, reason="'-ne' disambiguation needs sentence context (word position + question), not just a suffix check")
def test_ratione_enclitic_split_depends_on_context():
    # syntax_model.md's own contrastive pair: identical trailing letters,
    # opposite correct segmentation, depending on context.
    #
    # "aequa ratione imperat." -- ratione is ablative of ratio, mid-sentence,
    # not a question: stays one token.
    assert _text("aequa ratione imperat.") == ["aequa", "ratione", "imperat", "."]
 
    # "ratione docet?" -- word-initial in a question: splits into the
    # interrogative enclitic -ne plus ratio (nominative).
    assert _text("ratione docet?") == ["ratio", "ne", "docet", "?"]
 
 
@pytest.mark.xfail(strict=True, reason="'other abbreviation' tokens (f., cos., ...) are not yet recognized as single tokens")
def test_abbreviations_stay_one_token():
    # f. (filius) and cos. (consul) must glue to their period the same way
    # a praenomen does -- currently split into letters + "." like ordinary
    # sentence-final punctuation.
    assert _text("M. Agrippa L. f. cos. tertium fecit.") == [
        "M.", "Agrippa", "L.", "f.", "cos.", "tertium", "fecit", ".",
    ]
    