"""
Tests for save_mermaid() -- mermaid.py's file-writing wrapper around
tokengraph_to_mermaid(). It existed in mermaid.py but was never re-exported
from arsgrammatica/__init__.py, so `from arsgrammatica import save_mermaid`
raised ImportError even though the function worked fine; that's the
regression test_importable_from_top_level_package() below guards against.
"""

import pytest

from arsgrammatica import save_mermaid, tokengraph_to_mermaid
from conftest import run_gold_example
from fixtures.gold_examples import GOLD_EXAMPLES


def test_importable_from_top_level_package():
    """`from arsgrammatica import save_mermaid` must work -- it's a public
    function, and mermaid.py's other two top-level functions
    (tokengraph_to_mermaid, token_label) are both already re-exported from
    __init__.py this same way."""
    import arsgrammatica

    assert arsgrammatica.save_mermaid is save_mermaid
    assert "save_mermaid" in arsgrammatica.__all__


def test_writes_the_same_diagram_tokengraph_to_mermaid_would_return(tmp_path):
    example = next(e for e in GOLD_EXAMPLES if e.slug == "unit_verb_hercules_cum")
    tokens, result = run_gold_example(example)

    expected_diagram, expected_warnings = tokengraph_to_mermaid(result.tokengraph)

    out_path = tmp_path / "diagram.mmd"
    warnings = save_mermaid(result.tokengraph, str(out_path))

    assert warnings == expected_warnings
    assert out_path.read_text(encoding="utf-8") == expected_diagram + "\n"


def test_passes_through_orientation_and_coloring_kwargs(tmp_path):
    example = next(e for e in GOLD_EXAMPLES if e.slug == "unit_verb_hercules_cum")
    tokens, result = run_gold_example(example)

    out_path = tmp_path / "diagram.mmd"
    save_mermaid(
        result.tokengraph,
        str(out_path),
        orientation="LR",
        color_by_verbal_unit=False,
    )

    written = out_path.read_text(encoding="utf-8")
    assert written.startswith("graph LR")
    assert "classDef" not in written


def test_returns_warnings_list_for_a_warning_producing_example():
    """Confirms save_mermaid() actually surfaces tokengraph_to_mermaid()'s
    own warnings rather than swallowing them -- picks whichever gold
    example is known to produce at least one warning, skipping if none do
    (this codebase's gold fixtures are meant to be warning-free; this is a
    defensive check, not a claim that one currently exists)."""
    for example in GOLD_EXAMPLES:
        tokens, result = run_gold_example(example)
        _diagram, warnings = tokengraph_to_mermaid(result.tokengraph)
        if warnings:
            import tempfile
            import os

            fd, path = tempfile.mkstemp(suffix=".mmd")
            os.close(fd)
            try:
                returned = save_mermaid(result.tokengraph, path)
                assert returned == warnings
            finally:
                os.remove(path)
            return
    pytest.skip("no gold example currently produces a tokengraph_to_mermaid() warning")
