"""
Tests for displacy_viz.py: `tokengraph_to_displacy_data()` (the
words/arcs data conversion), `tokengraph_to_displacy_svg()` (the SVG
renderer built on top of it), and `save_displacy_html()` (the HTML
wrapper) -- see that module's own docstring for the design this exercises:
punctuation excluded from the word list, an implied/elided token included
(right after the token that links to it) only when something actually
does, the synthetic ROOT pseudo-word, arc direction, and verbal-unit
coloring.
"""

import os
import re

import pytest

from arsgrammatica import (
    save_displacy_html,
    tokengraph_to_displacy_data,
    tokengraph_to_displacy_svg,
)
from arsgrammatica.models import TokenAnalysis
from arsgrammatica.verbal_units import (
    assign_verbal_units,
    compute_aat_depths,
    max_aat_depth,
)
from conftest import run_gold_example
from fixtures.gold_examples import GOLD_EXAMPLES


def _example(slug):
    return next(e for e in GOLD_EXAMPLES if e.slug == slug)


# --- tokengraph_to_displacy_data(): basic shape ---


def test_data_shape_matches_displacy_manual_format():
    example = _example("unit_verb_hercules_cum")
    tokens, result = run_gold_example(example)
    data, word_token_ids, warnings = tokengraph_to_displacy_data(result.tokengraph)

    assert not warnings
    assert set(data.keys()) == {"words", "arcs"}
    for word in data["words"]:
        assert set(word.keys()) == {"text", "tag"}
    for arc in data["arcs"]:
        assert set(arc.keys()) == {"start", "end", "label", "dir"}
        assert arc["start"] < arc["end"]
        assert arc["dir"] in ("left", "right")
        assert 0 <= arc["start"] < len(data["words"])
        assert 0 <= arc["end"] < len(data["words"])
    assert len(word_token_ids) == len(data["words"])


def test_words_are_in_reading_order_excluding_punctuation():
    """Punctuation is omitted entirely (unlike mermaid.py's node graph,
    which draws it) -- the word list should read as the sentence's own
    words only, in tokengraph order, with no "tag" at all for an ordinary
    lexical word."""
    example = _example("unit_verb_hercules_cum")
    tokens, result = run_gold_example(example)
    data, word_token_ids, _warnings = tokengraph_to_displacy_data(
        result.tokengraph, show_root=False
    )
    texts = [w["text"] for w in data["words"]]
    assert texts == [
        "Hercules", "cum", "gregem", "perlustrasset",
        "pergit", "ad", "proximam", "speluncam",
    ]
    assert word_token_ids == ["t0", "t1", "t2", "t3", "t5", "t6", "t7", "t8"]
    assert all(tag == "" for tag in (w["tag"] for w in data["words"]))


def test_punctuation_never_appears_as_a_word():
    example = _example("unit_verb_hercules_cum")
    tokens, result = run_gold_example(example)
    data, word_token_ids, _warnings = tokengraph_to_displacy_data(result.tokengraph)
    punctuation_ids = {
        tok.id for tok in result.tokengraph if tok.tokentype == "punctuation"
    }
    assert punctuation_ids  # sanity: this fixture does have punctuation
    assert not (punctuation_ids & set(word_token_ids))
    assert "," not in [w["text"] for w in data["words"]]
    assert "." not in [w["text"] for w in data["words"]]


def test_only_non_lexical_tokentypes_get_a_tag():
    """'lexical' -- the ordinary, overwhelming-majority case -- gets an
    empty tag; a genuinely distinctive tokentype (here, 'praenomen' and
    'abbreviation') still gets its own tag."""
    example = _example("praenomen_abbreviation_m_agrippa_cos")
    tokens, result = run_gold_example(example)
    data, word_token_ids, _warnings = tokengraph_to_displacy_data(result.tokengraph)
    tag_by_id = dict(zip(word_token_ids, (w["tag"] for w in data["words"])))
    tag_by_id.pop(None, None)  # the synthetic ROOT word, if present
    tokentype_by_id = {tok.id: tok.tokentype for tok in result.tokengraph}
    for token_id, tag in tag_by_id.items():
        expected = tokentype_by_id[token_id]
        if expected == "lexical":
            assert tag == "", token_id
        else:
            assert tag == expected, token_id
    assert "praenomen" in tag_by_id.values() or "abbreviation" in tag_by_id.values()


def test_arc_direction_points_at_the_related_token():
    """'gregem' (t2) relates to 'perlustrasset' (t3) via direct object --
    the arc should span [2, 3] with the arrowhead ('dir') pointing at t3's
    own word index (the higher one here), i.e. dir='right'."""
    example = _example("unit_verb_hercules_cum")
    tokens, result = run_gold_example(example)
    data, word_token_ids, _warnings = tokengraph_to_displacy_data(result.tokengraph)
    i2, i3 = word_token_ids.index("t2"), word_token_ids.index("t3")
    arc = next(a for a in data["arcs"] if a["label"] == "direct object")
    assert (arc["start"], arc["end"]) == (min(i2, i3), max(i2, i3))
    assert arc["dir"] == ("right" if i3 > i2 else "left")


# --- the synthetic ROOT word ---


def test_show_root_default_true_adds_root_word_and_arc():
    example = _example("unit_verb_hercules_cum")
    tokens, result = run_gold_example(example)
    data, word_token_ids, warnings = tokengraph_to_displacy_data(result.tokengraph)
    assert not warnings
    assert data["words"][-1] == {"text": "ROOT", "tag": ""}
    assert word_token_ids[-1] is None
    root_index = len(data["words"]) - 1
    pergit_index = word_token_ids.index("t5")
    assert any(
        a["label"] == "unit verb" and root_index in (a["start"], a["end"])
        and pergit_index in (a["start"], a["end"])
        for a in data["arcs"]
    )


def test_show_root_false_omits_root_word_and_arc():
    example = _example("unit_verb_hercules_cum")
    tokens, result = run_gold_example(example)
    data, word_token_ids, warnings = tokengraph_to_displacy_data(
        result.tokengraph, show_root=False
    )
    assert not warnings
    assert "ROOT" not in [w["text"] for w in data["words"]]
    assert None not in word_token_ids
    # Every arc's endpoints must be real word indices -- with no ROOT word
    # to point at, the independent verb's own 'root' relation is simply
    # skipped, not redirected anywhere else.
    for arc in data["arcs"]:
        assert arc["start"] < len(data["words"])
        assert arc["end"] < len(data["words"])


def test_root_word_omitted_when_no_independent_verb_present():
    """Same fixture test_mermaid_root.py uses for its own analogous case:
    a tokengraph with no 'root'-anchored token (e.g. one sentence sliced
    out of a larger passage) must never get an orphan ROOT word."""
    tokengraph = [
        TokenAnalysis(
            id="t0", token="Hercules", tokentype="lexical",
            relatedtoken1="t1", relationship1="subject",
        ),
        TokenAnalysis(
            id="t1", token="pergit", tokentype="lexical", verbalunitid="t1",
            relatedtoken1="t2", relationship1="direct quote",
        ),
        TokenAnalysis(
            id="t2", token="venit", tokentype="lexical", verbalunitid="t2",
        ),
    ]
    data, word_token_ids, warnings = tokengraph_to_displacy_data(tokengraph)
    assert not warnings
    assert "ROOT" not in [w["text"] for w in data["words"]]
    assert None not in word_token_ids


def test_multiple_independent_verbs_share_one_root_word():
    example = _example("coordinating_conjunction_verbs_ille_hermionenque")
    tokens, result = run_gold_example(example)
    data, word_token_ids, warnings = tokengraph_to_displacy_data(result.tokengraph)
    assert not warnings
    assert [w["text"] for w in data["words"]].count("ROOT") == 1
    root_index = len(data["words"]) - 1
    root_arc_sources = {
        (a["start"] if a["end"] == root_index else a["end"])
        for a in data["arcs"]
        if root_index in (a["start"], a["end"]) and a["label"] == "unit verb"
    }
    i4, i10 = word_token_ids.index("t4"), word_token_ids.index("t10")
    assert root_arc_sources == {i4, i10}


# --- implied/elided tokens: included (right after their linking token)
# only when something surviving actually links to them; otherwise still
# excluded, exactly as before this existed. ---


@pytest.mark.parametrize(
    "slug, implied_id, linking_id, is_linked",
    [
        # t2_implied is targeted by BOTH t0 (subject) and t2 (predicate) --
        # "last one wins" places it right after t2, the later of the two.
        ("implied_sum_omnia_praeclara_rara", "t2_implied", "t2", True),
        # t7_implied (the elided "sunt") only relates OUTWARD to t7 --
        # nothing else's relation ever names it as a target, so it stays
        # excluded, same as before this existed.
        ("implied_sum_consules_facti", "t7_implied", None, False),
        # t8_implied (the always-implied participle of sum) likewise only
        # relates outward (to t8) -- nothing targets it.
        ("implied_participle_of_sum_consulibus", "t8_implied", None, False),
        # t0_implied is targeted only by t0 (Recordatus).
        ("implied_subject_recordatus_somniorum_ait", "t0_implied", "t0", True),
    ],
)
def test_implied_token_appears_as_a_word_only_when_something_links_to_it(
    slug, implied_id, linking_id, is_linked
):
    example = _example(slug)
    tokens, result = run_gold_example(example)
    data, word_token_ids, warnings = tokengraph_to_displacy_data(result.tokengraph)
    assert not warnings

    from arsgrammatica.models import IMPLIED_TOKENTYPES

    if is_linked:
        assert implied_id in word_token_ids
        i_implied = word_token_ids.index(implied_id)
        i_linker = word_token_ids.index(linking_id)
        assert i_implied == i_linker + 1, (
            f"{implied_id} should sit immediately after {linking_id}"
        )
    else:
        assert implied_id not in word_token_ids

    # Every real, non-punctuation token still gets its own word either way.
    real_ids = {
        tok.id
        for tok in result.tokengraph
        if tok.tokentype not in IMPLIED_TOKENTYPES and tok.tokentype != "punctuation"
    }
    assert real_ids <= set(word_token_ids)


def test_continuation_indirect_discourse_root_verb_now_appears_and_gets_a_root_arc():
    """continuation_indirect_discourse_tarquinios_adsuesse's own implied
    governing verb (t0_implied) is targeted by THREE infinitives (t3, t8,
    t11) via 'indirect statement' -- it goes right after the LAST of them
    (t11, 'regnasse'), and -- now that it has a word slot at all -- its OWN
    'root'/'unit verb' relation finally gets a ROOT word and arc drawn,
    something no earlier version of this diagram could ever show for this
    passage (the only root-pointing token was always excluded before)."""
    example = _example("continuation_indirect_discourse_tarquinios_adsuesse")
    tokens, result = run_gold_example(example)
    data, word_token_ids, warnings = tokengraph_to_displacy_data(result.tokengraph)
    assert not warnings

    i_implied = word_token_ids.index("t0_implied")
    i_regnasse = word_token_ids.index("t11")
    assert i_implied == i_regnasse + 1

    assert data["words"][-1] == {"text": "ROOT", "tag": ""}
    assert word_token_ids[-1] is None
    root_index = len(data["words"]) - 1
    assert any(
        a["label"] == "unit verb" and root_index in (a["start"], a["end"])
        and i_implied in (a["start"], a["end"])
        for a in data["arcs"]
    )
    # And each of the three infinitives' own 'indirect statement' arcs all
    # converge on that SAME word index -- one shared slot, three arcs.
    indirect_statement_arcs = [a for a in data["arcs"] if a["label"] == "indirect statement"]
    assert len(indirect_statement_arcs) == 3
    assert all(i_implied in (a["start"], a["end"]) for a in indirect_statement_arcs)


def test_linked_implied_token_is_included_right_after_its_source():
    """A hand-built tokengraph where a real token's relation points at an
    implied one: unlike a relation into punctuation or an aat_depth-
    excluded token, this is the one case that gets its target INCLUDED
    rather than skipped -- positioned immediately after the source, with a
    real arc drawn between them, not a warning."""
    tokengraph = [
        TokenAnalysis(
            id="t0", token="dictum", tokentype="lexical",
            relatedtoken1="implied0", relationship1="auxiliary",
        ),
        TokenAnalysis(
            id="implied0", token=None, tokentype="implied sum",
        ),
    ]
    data, word_token_ids, warnings = tokengraph_to_displacy_data(tokengraph)
    assert not warnings
    assert word_token_ids == ["t0", "implied0"]
    assert [w["text"] for w in data["words"]] == ["dictum", "elided sum"]
    assert data["arcs"] == [{"start": 0, "end": 1, "label": "auxiliary", "dir": "right"}]


def test_unlinked_implied_token_is_excluded_with_no_warning():
    """An implied/elided token that nothing else's relation ever names as
    a target has no anchor position to be placed at, and stays excluded
    exactly as before this existed -- its own outgoing relation is simply
    never drawn, silently (there's no arc at all to skip, same as an
    ordinary aat_depth-excluded token's own relations)."""
    tokengraph = [
        TokenAnalysis(
            id="implied0", token=None, tokentype="implied sum",
            relatedtoken1="t0", relationship1="auxiliary",
        ),
        TokenAnalysis(id="t0", token="factum", tokentype="lexical"),
    ]
    data, word_token_ids, warnings = tokengraph_to_displacy_data(tokengraph)
    assert not warnings
    assert word_token_ids == ["t0"]
    assert data["arcs"] == []


def test_implied_token_linked_by_multiple_sources_goes_after_the_last_one():
    """When more than one surviving token's own relation names the SAME
    implied token as a target, it can still only occupy one slot in the
    word sequence -- this module places it right after the LAST such
    token, in reading order (see this module's own docstring), with both
    relations still drawn as separate arcs converging on that one slot."""
    tokengraph = [
        TokenAnalysis(
            id="t0", token="primum", tokentype="lexical",
            relatedtoken1="implied0", relationship1="indirect statement",
        ),
        TokenAnalysis(
            id="t1", token="secundum", tokentype="lexical",
            relatedtoken1="implied0", relationship1="indirect statement",
        ),
        TokenAnalysis(
            id="implied0", token=None, tokentype="continued discourse",
            relatedtoken1="root", relationship1="unit verb",
        ),
    ]
    data, word_token_ids, warnings = tokengraph_to_displacy_data(tokengraph)
    assert not warnings
    assert word_token_ids == ["t0", "t1", "implied0", None]  # ROOT still last
    i0, i1, i_implied = 0, 1, 2
    assert {
        (a["start"], a["end"]) for a in data["arcs"] if a["label"] == "indirect statement"
    } == {(i0, i_implied), (i1, i_implied)}


def test_implied_token_can_itself_anchor_a_further_implied_token():
    """A linked implied token can itself be the target of ANOTHER implied
    token's own relation -- a chain, resolved via this module's own
    fixed-point pass, not just a single one."""
    tokengraph = [
        TokenAnalysis(
            id="t0", token="foo", tokentype="lexical",
            relatedtoken1="implied1", relationship1="circumstantial participle",
        ),
        TokenAnalysis(
            id="implied1", token=None, tokentype="implied subject",
            relatedtoken1="implied2", relationship1="subject",
        ),
        TokenAnalysis(
            id="implied2", token=None, tokentype="implied sum",
            relatedtoken1="root", relationship1="unit verb",
        ),
    ]
    data, word_token_ids, warnings = tokengraph_to_displacy_data(tokengraph)
    assert not warnings
    assert word_token_ids == ["t0", "implied1", "implied2", None]


def test_relation_to_missing_id_is_skipped_with_a_warning():
    tokengraph = [
        TokenAnalysis(
            id="t0", token="foo", tokentype="lexical",
            relatedtoken1="t99", relationship1="subject",
        ),
    ]
    data, word_token_ids, warnings = tokengraph_to_displacy_data(tokengraph)
    assert data["arcs"] == []
    assert len(warnings) == 1
    assert "t99" in warnings[0]


def test_relation_into_punctuation_is_skipped_with_a_warning():
    """A hand-built tokengraph where a real token's relation points at a
    punctuation token -- punctuation never gets a word slot (see this
    module's own docstring), so the arc must be dropped, not turned into a
    malformed word-index reference, and reported as a warning."""
    tokengraph = [
        TokenAnalysis(
            id="t0", token="foo", tokentype="lexical",
            relatedtoken1="t1", relationship1="subject",
        ),
        TokenAnalysis(id="t1", token=",", tokentype="punctuation"),
    ]
    data, word_token_ids, warnings = tokengraph_to_displacy_data(tokengraph)
    assert len(data["words"]) == 1
    assert data["arcs"] == []
    assert len(warnings) == 1
    assert "punctuation" in warnings[0]


def test_self_relation_is_skipped_with_a_warning():
    tokengraph = [
        TokenAnalysis(
            id="t0", token="foo", tokentype="lexical",
            relatedtoken1="t0", relationship1="subject",
        ),
    ]
    data, word_token_ids, warnings = tokengraph_to_displacy_data(tokengraph)
    assert data["arcs"] == []
    assert len(warnings) == 1


# --- tokengraph_to_displacy_svg() ---


@pytest.mark.parametrize("example", GOLD_EXAMPLES, ids=lambda e: e.slug)
def test_svg_renders_without_error_for_every_gold_example(example):
    tokens, result = run_gold_example(example)
    svg, warnings = tokengraph_to_displacy_svg(result.tokengraph)
    assert svg.startswith("<svg")
    assert svg.rstrip().endswith("</svg>")
    # Every data-conversion warning should still surface through the SVG
    # renderer -- it's a strict superset (plus, possibly, a trailing
    # too-many-verbal-units color warning).
    data, _ids, data_warnings = tokengraph_to_displacy_data(result.tokengraph)
    assert set(data_warnings) <= set(warnings)
    # Every word's own text should appear somewhere in the SVG.
    for word in data["words"]:
        assert word["text"] in svg or word["text"] == ""


def test_svg_coloring_adds_no_new_warnings():
    example = _example("coordinating_conjunction_verbs_ille_hermionenque")
    tokens, result = run_gold_example(example)
    _plain_svg, plain_warnings = tokengraph_to_displacy_svg(
        result.tokengraph, color_by_verbal_unit=False
    )
    _colored_svg, colored_warnings = tokengraph_to_displacy_svg(
        result.tokengraph, color_by_verbal_unit=True
    )
    assert colored_warnings == plain_warnings


def test_root_word_is_never_colored():
    example = _example("unit_verb_hercules_cum")
    tokens, result = run_gold_example(example)
    svg, _warnings = tokengraph_to_displacy_svg(result.tokengraph, color_by_verbal_unit=True)
    # The ROOT text element should carry the neutral gray/italic styling,
    # not a verbal-unit fill color -- check it isn't preceded immediately
    # by a colored <rect> the way a real word is.
    root_text_match = re.search(r'<text[^>]*>ROOT</text>', svg)
    assert root_text_match is not None
    assert 'font-style="italic"' in root_text_match.group(0)


def test_included_implied_token_gets_the_dedicated_amber_color():
    """An included implied/elided token always gets
    `verbal_units._IMPLIED_TOKEN_COLOR` -- the same dedicated 'caution'
    amber mermaid.py's own diagram uses for the very same token --
    regardless of which verbal unit it belongs to."""
    from arsgrammatica.verbal_units import _IMPLIED_TOKEN_COLOR

    example = _example("implied_subject_recordatus_somniorum_ait")
    tokens, result = run_gold_example(example)
    svg, _warnings = tokengraph_to_displacy_svg(result.tokengraph, color_by_verbal_unit=True)
    fill, _stroke, _text = _IMPLIED_TOKEN_COLOR
    assert fill in svg


def test_arc_levels_stack_overlapping_arcs_without_collision():
    from arsgrammatica.displacy_viz import _assign_arc_levels

    # (0,5) and (1,3) overlap -> different levels; (6,8) doesn't overlap
    # either -> can share level 0 with whichever of the first two it
    # doesn't overlap (here, neither, so it should land at level 0).
    levels = _assign_arc_levels([(0, 5), (1, 3), (6, 8)])
    assert levels[0] != levels[1]
    assert levels[2] == 0


def test_touching_spans_can_share_a_level():
    from arsgrammatica.displacy_viz import _assign_arc_levels

    levels = _assign_arc_levels([(0, 2), (2, 4)])
    assert levels == [0, 0]


# --- save_displacy_html() ---


def test_save_displacy_html_writes_a_browser_ready_file(tmp_path):
    example = _example("unit_verb_hercules_cum")
    tokens, result = run_gold_example(example)
    out_path = tmp_path / "diagram.html"
    warnings = save_displacy_html(result.tokengraph, str(out_path))
    assert not warnings
    assert out_path.exists()
    content = out_path.read_text(encoding="utf-8")
    assert content.startswith("<!DOCTYPE html>")
    assert "<svg" in content
    assert "Hercules cum gregem perlustrasset" in content  # default caption


def test_save_displacy_html_custom_and_empty_caption(tmp_path):
    example = _example("unit_verb_hercules_cum")
    tokens, result = run_gold_example(example)

    out_path = tmp_path / "custom.html"
    save_displacy_html(result.tokengraph, str(out_path), caption="My own caption")
    assert "My own caption" in out_path.read_text(encoding="utf-8")

    out_path2 = tmp_path / "no_caption.html"
    save_displacy_html(result.tokengraph, str(out_path2), caption="")
    content2 = out_path2.read_text(encoding="utf-8")
    assert "<h1>" not in content2


# --- aat_depth: the same AAT-graph depth cutoff mermaid.py's/dot.py's own
# aat_depth parameters use, so one value can drive all three diagrams. ---


def test_aat_depth_zero_keeps_the_whole_root_clause():
    """Same fixture/expectation as test_mermaid_ranking.py's own
    test_aat_depth_zero_shows_the_whole_root_clause(): pergit's clause
    (t0, t5, t6, t7, t8) survives aat_depth=0 in full; perlustrasset's
    separate, deeper clause (t1, t2, t3) does not."""
    example = _example("unit_verb_hercules_cum")
    tokens, result = run_gold_example(example)
    data, word_token_ids, warnings = tokengraph_to_displacy_data(
        result.tokengraph, aat_depth=0
    )
    assert not warnings
    for kept_id in ("t0", "t5", "t6", "t7", "t8"):
        assert kept_id in word_token_ids, kept_id
    for dropped_id in ("t1", "t2", "t3"):
        assert dropped_id not in word_token_ids, dropped_id


def test_aat_depth_at_or_beyond_passage_max_matches_aat_depth_none():
    example = _example("unit_verb_hercules_cum")
    tokens, result = run_gold_example(example)
    maxd = max_aat_depth(result.tokengraph)
    data_max, ids_max, warnings_max = tokengraph_to_displacy_data(
        result.tokengraph, aat_depth=maxd
    )
    data_none, ids_none, warnings_none = tokengraph_to_displacy_data(
        result.tokengraph, aat_depth=None
    )
    assert data_max == data_none
    assert ids_max == ids_none
    assert warnings_max == warnings_none


def test_aat_depth_negative_raises():
    example = _example("unit_verb_hercules_cum")
    tokens, result = run_gold_example(example)
    with pytest.raises(ValueError, match="aat_depth must be >= 0"):
        tokengraph_to_displacy_data(result.tokengraph, aat_depth=-1)
    with pytest.raises(ValueError, match="aat_depth must be >= 0"):
        tokengraph_to_displacy_svg(result.tokengraph, aat_depth=-1)


def test_aat_depth_and_coloring_compose():
    example = _example("unit_verb_hercules_cum")
    tokens, result = run_gold_example(example)
    svg, _warnings = tokengraph_to_displacy_svg(
        result.tokengraph, aat_depth=0, color_by_verbal_unit=True
    )
    assert "fill=" in svg  # a colored word box still gets drawn


def test_aat_depth_dangling_arc_from_kept_word_is_skipped_with_a_warning():
    """Same hand-built coordinating-conjunction fixture
    test_mermaid_ranking.py's own analogous test uses: "que" resolves into
    "cano"'s unit (depth 0), but its relatedtoken2 points at "virum", which
    anchors its OWN separate, deeper (depth 1) verbal unit. At aat_depth=0,
    "que" is kept but "virum" is excluded, so that relation must be skipped
    with a warning rather than left as a dangling arc."""
    tokengraph = [
        TokenAnalysis(
            id="t5", token="cano", tokentype="lexical", verbalunitid="t5",
            relatedtoken1="root", relationship1="unit verb",
        ),
        TokenAnalysis(
            id="t0", token="arma", tokentype="lexical",
            relatedtoken1="t5", relationship1="direct object",
        ),
        TokenAnalysis(
            id="t1", token="que", tokentype="enclitic",
            relatedtoken1="t0", relationship1="coordinating conjunction",
            relatedtoken2="t2", relationship2="coordinating conjunction",
        ),
        TokenAnalysis(
            id="t2", token="virum", tokentype="lexical", verbalunitid="t2",
            relatedtoken1="t5", relationship1="direct quote",
        ),
    ]
    data, word_token_ids, warnings = tokengraph_to_displacy_data(tokengraph, aat_depth=0)
    assert "t2" not in word_token_ids
    assert any("t2" in w and "aat_depth" in w for w in warnings)
    # The coordinating-conjunction arc from "que" to "arma" (both depth 0)
    # must still be drawn.
    i_que, i_arma = word_token_ids.index("t1"), word_token_ids.index("t0")
    assert any(
        {a["start"], a["end"]} == {i_que, i_arma} for a in data["arcs"]
    )


@pytest.mark.parametrize("example", GOLD_EXAMPLES, ids=lambda e: e.slug)
def test_aat_depth_filtering_never_leaves_a_dangling_arc(example):
    """Property check across every gold example, at every AAT-depth level
    from 0 up to that passage's own max_aat_depth(): no arc's start/end may
    reference a word index beyond the word list -- i.e. every arc endpoint
    corresponds to a token that actually survived the cutoff."""
    tokens, result = run_gold_example(example)
    tokengraph = result.tokengraph
    maxd = max_aat_depth(tokengraph)
    if maxd is None:
        return

    for cap in range(0, maxd + 1):
        data, word_token_ids, _warnings = tokengraph_to_displacy_data(tokengraph, aat_depth=cap)
        for arc in data["arcs"]:
            assert 0 <= arc["start"] < len(word_token_ids), (example.slug, cap)
            assert 0 <= arc["end"] < len(word_token_ids), (example.slug, cap)


@pytest.mark.parametrize("example", GOLD_EXAMPLES, ids=lambda e: e.slug)
def test_aat_depth_zero_never_drops_a_token_from_its_own_clause(example):
    """Structural check across the whole fixture set: at aat_depth=0, every
    KEPT verbal-unit anchor's own dependents (per assign_verbal_units())
    must also be kept -- confirming the filter drops or keeps a whole
    clause together, never splits one apart. Same check
    test_mermaid_ranking.py's own analogous test performs on the mermaid
    side."""
    tokens, result = run_gold_example(example)
    tokengraph = result.tokengraph
    _data, word_token_ids, _warnings = tokengraph_to_displacy_data(tokengraph, aat_depth=0)
    kept_ids = set(word_token_ids)

    from arsgrammatica.models import IMPLIED_TOKENTYPES

    depths = compute_aat_depths(tokengraph)
    assignment = assign_verbal_units(tokengraph)
    for tok in tokengraph:
        if tok.tokentype in IMPLIED_TOKENTYPES or tok.tokentype == "punctuation":
            # Punctuation never gets a word slot here at all. An
            # implied/elided token is never itself excluded by aat_depth
            # either way (see displacy_viz.py's own module docstring) --
            # whether it ends up in the diagram depends solely on whether
            # something links to it, an orthogonal design choice this
            # "clause stays together" check isn't about, so it's skipped
            # here regardless of which way that turned out.
            continue
        unit_id = assignment.get(tok.id)
        unit_depth = depths.get(unit_id, 0) if unit_id is not None else 0
        if unit_depth == 0:
            assert tok.id in kept_ids, f"{example.slug}: {tok.id} should survive aat_depth=0"
