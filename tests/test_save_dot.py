"""
Tests for save_dot() -- dot.py's file-writing wrapper around
tokengraph_to_dot(). Same regression this session already fixed for its
Mermaid-side sibling save_mermaid() (see test_save_mermaid.py): the
function existed in dot.py but was never re-exported from
arsgrammatica/__init__.py, so `from arsgrammatica import save_dot` raised
ImportError even though the function worked fine.
"""

import pytest

from arsgrammatica import save_dot, tokengraph_to_dot
from conftest import run_gold_example
from fixtures.gold_examples import GOLD_EXAMPLES


def test_importable_from_top_level_package():
    """`from arsgrammatica import save_dot` must work -- it's a public
    function, and dot.py's other top-level functions (tokengraph_to_dot,
    compute_graph_depths, max_graph_depth) are all already re-exported from
    __init__.py this same way."""
    import arsgrammatica

    assert arsgrammatica.save_dot is save_dot
    assert "save_dot" in arsgrammatica.__all__


def test_writes_the_same_diagram_tokengraph_to_dot_would_return(tmp_path):
    example = next(e for e in GOLD_EXAMPLES if e.slug == "unit_verb_hercules_cum")
    tokens, result = run_gold_example(example)

    expected_diagram, expected_warnings = tokengraph_to_dot(result.tokengraph)

    out_path = tmp_path / "diagram.dot"
    warnings = save_dot(result.tokengraph, str(out_path))

    assert warnings == expected_warnings
    assert out_path.read_text(encoding="utf-8") == expected_diagram + "\n"


def test_passes_through_orientation_and_coloring_kwargs(tmp_path):
    example = next(e for e in GOLD_EXAMPLES if e.slug == "unit_verb_hercules_cum")
    tokens, result = run_gold_example(example)

    out_path = tmp_path / "diagram.dot"
    save_dot(
        result.tokengraph,
        str(out_path),
        orientation="LR",
        color_by_verbal_unit=False,
    )

    written = out_path.read_text(encoding="utf-8")
    assert "rankdir=LR" in written
    assert "fillcolor=" not in written


def test_passes_through_depth(tmp_path):
    """save_dot()'s own extra parameter over save_mermaid() -- depth
    filtering (see notes/dot_diagrams.md's "Depth filtering" section).
    depth=0 keeps only root verbal-unit anchors."""
    example = next(e for e in GOLD_EXAMPLES if e.slug == "unit_verb_hercules_cum")
    tokens, result = run_gold_example(example)

    full_diagram, _warnings = tokengraph_to_dot(result.tokengraph)
    root_only_diagram, _warnings = tokengraph_to_dot(result.tokengraph, depth=0)
    assert len(root_only_diagram) < len(full_diagram)

    out_path = tmp_path / "diagram.dot"
    save_dot(result.tokengraph, str(out_path), depth=0)
    assert out_path.read_text(encoding="utf-8") == root_only_diagram + "\n"


def test_returns_warnings_list_for_a_warning_producing_example():
    """Confirms save_dot() actually surfaces tokengraph_to_dot()'s own
    warnings rather than swallowing them -- picks whichever gold example is
    known to produce at least one warning, skipping if none do (this
    codebase's gold fixtures are meant to be warning-free; this is a
    defensive check, not a claim that one currently exists)."""
    for example in GOLD_EXAMPLES:
        tokens, result = run_gold_example(example)
        _diagram, warnings = tokengraph_to_dot(result.tokengraph)
        if warnings:
            import tempfile
            import os

            fd, path = tempfile.mkstemp(suffix=".dot")
            os.close(fd)
            try:
                returned = save_dot(result.tokengraph, path)
                assert returned == warnings
            finally:
                os.remove(path)
            return
    pytest.skip("no gold example currently produces a tokengraph_to_dot() warning")
