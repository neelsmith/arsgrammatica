"""
Tests for arsgrammatica/rendering.py's relationship-highlighting trio:
tokengraph_relationship_types(), relationship_edges(), and
tokengraph_to_relationship_html() -- built for an interactive notebook
(marimo/latin_syntaxer_relationships.py) that lets a user pick one
relationship label at a time and see its edges highlighted in the
passage's own colored-by-verbal-unit HTML display.
"""

import html as html_module

import pytest

from arsgrammatica.models import TokenAnalysis
from arsgrammatica.rendering import (
    RelationshipEdge,
    _NEUTRAL_FILL,
    _NEUTRAL_TEXT,
    relationship_edges,
    tokengraph_relationship_types,
    tokengraph_to_html,
    tokengraph_to_relationship_html,
)
from arsgrammatica.verbal_units import _VERBAL_UNIT_PALETTE


def _tok(id, token, tokentype, **kw):
    return TokenAnalysis(id=id, token=token, tokentype=tokentype, **kw)


# --- tokengraph_relationship_types() ---------------------------------------


def test_empty_tokengraph_has_no_relationship_types():
    assert tokengraph_relationship_types([]) == []


def test_tokens_with_no_relations_have_no_relationship_types():
    tg = [_tok("t0", "arma", "lexical"), _tok("t1", "virum", "lexical")]
    assert tokengraph_relationship_types(tg) == []


def test_distinct_relationship_labels_sorted_alphabetically():
    tg = [
        _tok("t0", "puer", "lexical", relatedtoken1="t1", relationship1="subject"),
        _tok("t1", "videt", "lexical", relatedtoken1="root", relationship1="unit verb"),
        _tok("t2", "puellam", "lexical", relatedtoken1="t1", relationship1="direct object"),
    ]
    assert tokengraph_relationship_types(tg) == ["direct object", "subject", "unit verb"]


def test_duplicate_relationship_labels_collapse_to_one_entry():
    tg = [
        _tok("t0", "puer", "lexical", relatedtoken1="t1", relationship1="subject"),
        _tok("t1", "videt", "lexical"),
        _tok("t2", "puella", "lexical", relatedtoken1="t1", relationship1="subject"),
    ]
    assert tokengraph_relationship_types(tg) == ["subject"]


def test_relationship2_values_are_included_too():
    # A coordinating conjunction sets BOTH relationship1 and relationship2
    # on the same token (the two-way relationship case) -- both values
    # must show up in the menu even though "arma"/"virum" each only use
    # relationship1.
    tg = [
        _tok("t0", "arma", "lexical", relatedtoken1="t3", relationship1="direct object"),
        _tok("t1", "virum", "lexical", relatedtoken1="t3", relationship1="direct object"),
        _tok(
            "t2", "que", "enclitic",
            relatedtoken1="t0", relationship1="coordinating conjunction",
            relatedtoken2="t1", relationship2="coordinating conjunction",
        ),
        _tok("t3", "cano", "lexical", relatedtoken1="root", relationship1="unit verb"),
    ]
    assert tokengraph_relationship_types(tg) == [
        "coordinating conjunction",
        "direct object",
        "unit verb",
    ]


# --- relationship_edges() ---------------------------------------------------


_ARMA_VIRUMQUE_CANO = [
    _tok("t0", "arma", "lexical", relatedtoken1="t3", relationship1="direct object"),
    _tok("t1", "virum", "lexical", relatedtoken1="t3", relationship1="direct object"),
    _tok(
        "t2", "que", "enclitic",
        relatedtoken1="t0", relationship1="coordinating conjunction",
        relatedtoken2="t1", relationship2="coordinating conjunction",
    ),
    _tok("t3", "cano", "lexical", relatedtoken1="root", relationship1="unit verb"),
    _tok("t4", ".", "punctuation"),
]


def test_relationship_edges_with_no_filter_returns_every_edge():
    edges, warnings = relationship_edges(_ARMA_VIRUMQUE_CANO)
    assert warnings == []
    # t0, t1 (direct object), t2 x2 (coordinating conjunction), t3 (unit verb) = 5
    assert len(edges) == 5


def test_relationship_edges_filter_keeps_only_matching_label():
    edges, warnings = relationship_edges(_ARMA_VIRUMQUE_CANO, relationship="direct object")
    assert warnings == []
    assert {(e.start_id, e.end_id) for e in edges} == {("t0", "t3"), ("t1", "t3")}
    assert all(e.relationship == "direct object" for e in edges)
    assert all(e.start_label and e.end_label for e in edges)


def test_relationship_edges_root_target_has_no_end_id_but_a_label():
    edges, warnings = relationship_edges(_ARMA_VIRUMQUE_CANO, relationship="unit verb")
    assert warnings == []
    assert len(edges) == 1
    edge = edges[0]
    assert edge.start_id == "t3"
    assert edge.start_label == "cano"
    assert edge.end_id is None
    assert edge.end_label == "root"


def test_relationship_edges_two_way_conjunction_produces_two_edges_from_same_start():
    edges, warnings = relationship_edges(_ARMA_VIRUMQUE_CANO, relationship="coordinating conjunction")
    assert warnings == []
    assert len(edges) == 2
    assert all(e.start_id == "t2" for e in edges)
    assert {e.end_id for e in edges} == {"t0", "t1"}


def test_relationship_edges_selecting_unattested_relationship_returns_nothing():
    edges, warnings = relationship_edges(_ARMA_VIRUMQUE_CANO, relationship="genitive")
    assert edges == []
    assert warnings == []


def test_relationship_edges_unresolved_target_id_warns_and_has_no_end_id():
    tg = [
        _tok("t0", "foo", "lexical", relatedtoken1="t99", relationship1="adverbial"),
    ]
    edges, warnings = relationship_edges(tg)
    assert len(edges) == 1
    edge = edges[0]
    assert edge.start_id == "t0"
    assert edge.end_id is None
    assert edge.end_label == "t99"  # falls back to the raw, unresolved id
    assert len(warnings) == 1
    assert "t0" in warnings[0] and "t99" in warnings[0] and "adverbial" in warnings[0]


def test_relationship_edges_implied_token_start_gets_a_placeholder_label():
    # "implied sum" has no surface text of its own (tok.token is None) --
    # its start_label should fall back to token_label()'s placeholder
    # ("elided sum"), not crash on None.
    tg = [
        _tok(
            "t0", None, "implied sum",
            relatedtoken1="t1", relationship1="auxiliary",
            verbalunitid="t1",
        ),
        _tok("t1", "facti", "lexical"),
    ]
    edges, warnings = relationship_edges(tg)
    assert warnings == []
    assert len(edges) == 1
    assert edges[0].start_label == "elided sum"
    assert edges[0].end_id == "t1"
    assert edges[0].end_label == "facti"


# --- tokengraph_to_relationship_html() --------------------------------------


def test_relationship_html_with_no_selection_matches_plain_html_plus_css():
    html_out, warnings = tokengraph_to_relationship_html(_ARMA_VIRUMQUE_CANO, relationship=None)
    assert warnings == []
    assert html_out.startswith("<style>")
    # Strip the leading CSS block and the ag-rel-passage typography
    # wrapper -- what's left should be byte-for-byte what
    # tokengraph_to_html() itself produces, since relationship=None marks
    # nothing.
    plain = tokengraph_to_html(_ARMA_VIRUMQUE_CANO)
    assert html_out.endswith(f'<div class="ag-rel-passage">{plain}</div>')


def test_relationship_html_unselected_relationship_adds_no_highlight_classes():
    html_out, _w = tokengraph_to_relationship_html(_ARMA_VIRUMQUE_CANO, relationship=None)
    body = html_out.split("</style>", 1)[1]
    assert "ag-rel-start" not in body
    assert "ag-rel-end" not in body


def test_relationship_html_marks_start_underline_and_end_box():
    html_out, warnings = tokengraph_to_relationship_html(
        _ARMA_VIRUMQUE_CANO, relationship="direct object"
    )
    assert warnings == []
    # t0 ("arma") and t1 ("virum") are starts; t3 ("cano") is the shared end.
    assert 'id="tok-t0"' in html_out
    assert 'id="tok-t3"' in html_out
    # Extract each span's class attribute crudely (good enough for a unit
    # test on output we just generated ourselves).
    def class_of(token_id):
        marker = f'id="tok-{token_id}"'
        start = html_out.index(marker)
        span_start = html_out.rindex("<span", 0, start)
        span_end = html_out.index(">", start)
        return html_out[span_start:span_end]

    assert "ag-rel-start" in class_of("t0")
    assert "ag-rel-end" not in class_of("t0")
    assert "ag-rel-end" in class_of("t3")
    assert "ag-rel-start" not in class_of("t3")


def test_relationship_html_title_only_shows_selected_relationship_edges():
    # t3 ("cano") is the END of two "direct object" edges AND the START of
    # its own "unit verb" edge to root. Selecting "direct object" should
    # show ONLY the direct-object lines in its tooltip -- never the unit
    # verb one, even though assign_verbal_units()/cano's own relationship1
    # field really is "unit verb".
    html_out, _w = tokengraph_to_relationship_html(_ARMA_VIRUMQUE_CANO, relationship="direct object")
    marker = 'id="tok-t3"'
    start = html_out.index(marker)
    title_start = html_out.index('title="', start) + len('title="')
    title_end = html_out.index('"', title_start)
    title = html_module.unescape(html_out[title_start:title_end])
    assert "arma - direct object - cano" in title
    assert "virum - direct object - cano" in title
    assert "unit verb" not in title


def test_relationship_html_multiple_edges_on_one_node_join_with_newline():
    # t2 ("que") is the start of BOTH coordinating-conjunction edges.
    html_out, _w = tokengraph_to_relationship_html(
        _ARMA_VIRUMQUE_CANO, relationship="coordinating conjunction"
    )
    marker = 'id="tok-t2"'
    start = html_out.index(marker)
    title_start = html_out.index('title="', start) + len('title="')
    title_end = html_out.index('"', title_start)
    title = html_module.unescape(html_out[title_start:title_end])
    lines = title.split("\n")
    assert len(lines) == 2
    assert "que - coordinating conjunction - arma" in lines
    assert "que - coordinating conjunction - virum" in lines


def test_relationship_html_selecting_unattested_relationship_is_a_no_op():
    html_out, warnings = tokengraph_to_relationship_html(_ARMA_VIRUMQUE_CANO, relationship="genitive")
    assert warnings == []
    body = html_out.split("</style>", 1)[1]
    assert "ag-rel-start" not in body
    assert "ag-rel-end" not in body


def test_relationship_html_escapes_special_characters_in_tooltip_and_text():
    tg = [
        _tok(
            "t0", 'A&B"', "lexical",
            relatedtoken1="t1", relationship1="apposition",
        ),
        _tok("t1", "C<D", "lexical"),
    ]
    html_out, _w = tokengraph_to_relationship_html(tg, relationship="apposition")
    # Token text is escaped ('&' -> '&amp;', '"' -> '&quot;') both in the
    # visible span content and in the title attribute -- never leaked raw.
    assert "A&amp;B&quot;" in html_out
    assert '<span id="tok-t1"' in html_out
    assert "C&lt;D" in html_out
    assert 'A&B"' not in html_out


def test_relationship_html_tooltip_is_css_only_not_just_native_title():
    # The hover bubble is drawn by .ag-rel-tip:hover::after (CSS generated
    # content pulling from data-tooltip) -- native `title` is still set too,
    # but only as a harmless fallback, since it turned out not to reliably
    # pop up once this HTML is embedded inside a host page's own DOM (e.g. a
    # marimo notebook cell) rather than opened as a bare page. Both
    # attributes must carry the identical text.
    html_out, _w = tokengraph_to_relationship_html(_ARMA_VIRUMQUE_CANO, relationship="direct object")
    css_block = html_out.split("</style>", 1)[0]
    assert ".ag-rel-tip" in css_block
    assert "content: attr(data-tooltip)" in css_block
    assert ':hover::after' in css_block

    marker = 'id="tok-t0"'
    start = html_out.index(marker)
    span_end = html_out.index(">", start)
    span_tag = html_out[html_out.rindex("<span", 0, start):span_end]
    assert "ag-rel-tip" in span_tag

    def attr_value(name, tag):
        needle = f'{name}="'
        i = tag.index(needle) + len(needle)
        j = tag.index('"', i)
        return tag[i:j]

    assert attr_value("data-tooltip", span_tag) == attr_value("title", span_tag)
    assert attr_value("data-tooltip", span_tag) == "arma - direct object - cano"


def test_relationship_html_root_edge_has_no_box_but_still_gets_underline_and_title():
    html_out, warnings = tokengraph_to_relationship_html(_ARMA_VIRUMQUE_CANO, relationship="unit verb")
    assert warnings == []
    marker = 'id="tok-t3"'
    start = html_out.index(marker)
    span_end = html_out.index(">", start)
    span_tag = html_out[html_out.rindex("<span", 0, start):span_end]
    assert "ag-rel-start" in span_tag
    assert "ag-rel-end" not in span_tag
    title_start = html_out.index('title="', start) + len('title="')
    title_end = html_out.index('"', title_start)
    assert html_module.unescape(html_out[title_start:title_end]) == "cano - unit verb - root"


# --- neutralizing non-participating tokens' colors -------------------------
#
# tokengraph_to_relationship_html() flattens a colored token to a neutral
# gray, instead of showing its ordinary verbal-unit color, once a
# `relationship` is selected AND that token isn't one of the selected
# relationship's own edge endpoints -- so the selected edges pop by
# contrast against a flattened passage. Built for the same notebook's
# existing relationship dropdown: picking a value re-renders this
# function with that value, no new UI involved.

_TWO_CLAUSES_WITH_OBJECT = [
    _tok("t0", "puer", "lexical", relatedtoken1="t1", relationship1="subject"),
    _tok("t1", "videt", "lexical", verbalunitid="t1"),
    _tok("t2", "puellam", "lexical", relatedtoken1="t1", relationship1="direct object"),
    _tok("t3", ",", "punctuation"),
    _tok("t4", "canis", "lexical", relatedtoken1="t5", relationship1="subject"),
    _tok("t5", "latrat", "lexical", verbalunitid="t5"),
    _tok("t6", ".", "punctuation"),
]


def _style_of(html_out, token_id):
    """Crudely extract one token's <span ...> opening tag (good enough for
    output generated in these tests) -- same convention as class_of()
    above."""
    marker = f'id="tok-{token_id}"'
    start = html_out.index(marker)
    span_start = html_out.rindex("<span", 0, start)
    span_end = html_out.index(">", start)
    return html_out[span_start:span_end]


def test_relationship_html_neutralizes_colored_tokens_outside_the_selection():
    # Selecting "subject" highlights puer->videt and canis->latrat (both
    # edges' endpoints keep their own verbal-unit color), but "puellam" --
    # colored (same verbal unit as puer/videt) as a *direct object*, not a
    # subject -- gets flattened to the neutral color even though it shares
    # videt's own clause/color.
    html_out, warnings = tokengraph_to_relationship_html(
        _TWO_CLAUSES_WITH_OBJECT, relationship="subject"
    )
    assert warnings == []

    fill0, _s0, text0 = _VERBAL_UNIT_PALETTE[0]
    fill1, _s1, text1 = _VERBAL_UNIT_PALETTE[1]

    assert f"background-color: {fill0}" in _style_of(html_out, "t0")  # puer
    assert f"background-color: {fill0}" in _style_of(html_out, "t1")  # videt
    assert f"background-color: {fill1}" in _style_of(html_out, "t4")  # canis
    assert f"background-color: {fill1}" in _style_of(html_out, "t5")  # latrat

    puellam_style = _style_of(html_out, "t2")
    assert f"background-color: {_NEUTRAL_FILL}" in puellam_style
    assert f"color: {_NEUTRAL_TEXT}" in puellam_style
    assert fill0 not in puellam_style
    assert text0 not in puellam_style


def test_relationship_html_no_selection_keeps_every_token_at_full_color():
    # Same fixture, nothing selected: "puellam" keeps its ordinary
    # verbal-unit color -- neutralizing only happens once a relationship is
    # actually picked.
    html_out, _w = tokengraph_to_relationship_html(_TWO_CLAUSES_WITH_OBJECT, relationship=None)
    fill0, _s0, _t0 = _VERBAL_UNIT_PALETTE[0]
    puellam_style = _style_of(html_out, "t2")
    assert f"background-color: {fill0}" in puellam_style
    assert _NEUTRAL_FILL not in puellam_style


def test_relationship_html_unattested_relationship_does_not_neutralize_anything():
    # Selecting a relationship this passage never attests ("genitive") is
    # documented as a pure no-op -- identical to relationship=None -- so it
    # must NOT flatten every colored token to neutral gray just because
    # nothing matched.
    html_out, warnings = tokengraph_to_relationship_html(
        _TWO_CLAUSES_WITH_OBJECT, relationship="genitive"
    )
    assert warnings == []
    plain, _w = tokengraph_to_relationship_html(_TWO_CLAUSES_WITH_OBJECT, relationship=None)
    assert html_out == plain
    assert _NEUTRAL_FILL not in html_out


def test_relationship_html_empty_tokengraph_returns_just_the_css():
    html_out, warnings = tokengraph_to_relationship_html([], relationship=None)
    assert warnings == []
    assert html_out == tokengraph_to_relationship_html([], relationship=None)[0]
    assert "<style>" in html_out
    assert "ag-rel-start" not in html_out.replace("<style>", "", 1).split("</style>")[-1]
