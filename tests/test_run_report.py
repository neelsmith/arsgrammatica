"""
Tests for run_report.py's FailedPassage/format_warnings_report()/
write_warnings_report() -- the shared "warnings.txt" report the
multi-passage analysis scripts (utilities/analyze_ctsdata_to_files.py,
utilities/analyze_tokendata_to_files.py, utilities/analyze_w_diagrams.py,
utilities/analyze_tokendata_w_diagrams.py) all write once a run finishes,
listing every passage that failed outright plus the run's total LM cost.

Mirrors test_lm_cost.py's own style: no dspy involved, `lm_history` is just
a list of dict-like entries with a `cost` key (exactly the shape
`format_warnings_report()` hands straight to `summarize_lm_cost()`), so
gold fixtures are hand-built dicts rather than anything DummyLM-driven.
"""

from pathlib import Path

from arsgrammatica import FailedPassage, format_warnings_report, write_warnings_report


def test_no_failures_says_so_explicitly_rather_than_being_silently_empty():
    report = format_warnings_report([], [])
    assert "No passages failed to analyze." in report
    assert "LM cost: no LM calls yet" in report


def test_no_failures_still_reports_a_real_cost():
    report = format_warnings_report([], [{"cost": 0.02}, {"cost": None}])
    assert "No passages failed to analyze." in report
    assert "$0.0200 across 1 call" in report
    assert "1 more call" in report


def test_one_failure_uses_singular_wording_and_names_it():
    failed = [FailedPassage("sentence starting at 'urn:cts:...:1.1'", "boom")]
    report = format_warnings_report(failed, [])
    assert "1 passage failed to analyze:" in report
    assert "1 passages" not in report
    assert "- sentence starting at 'urn:cts:...:1.1': boom" in report
    assert "LM cost: no LM calls yet" in report


def test_multiple_failures_are_all_listed_in_order():
    failed = [
        FailedPassage("sentence starting at 'urn:cts:...:1.1'", "first error"),
        FailedPassage("sentence starting at 'urn:cts:...:1.2'", "second error"),
        FailedPassage("sentence starting at 'urn:cts:...:1.3'", "third error"),
    ]
    report = format_warnings_report(failed, [{"cost": 0.01}])
    assert "3 passages failed to analyze:" in report
    lines = report.splitlines()
    failure_lines = [l for l in lines if l.startswith("  - ")]
    assert failure_lines == [
        "  - sentence starting at 'urn:cts:...:1.1': first error",
        "  - sentence starting at 'urn:cts:...:1.2': second error",
        "  - sentence starting at 'urn:cts:...:1.3': third error",
    ]
    assert "$0.0100 across 1 call" in report


def test_write_warnings_report_writes_the_same_text_and_returns_the_path(tmp_path):
    failed = [FailedPassage("sentence starting at 'x'", "oops")]
    lm_history = [{"cost": 0.05}]
    out_path = tmp_path / "warnings.txt"

    returned = write_warnings_report(out_path, failed, lm_history)

    assert returned == Path(out_path)
    written_text = out_path.read_text(encoding="utf-8")
    assert written_text == format_warnings_report(failed, lm_history)
    assert "oops" in written_text
    assert "$0.0500 across 1 call" in written_text


def test_write_warnings_report_overwrites_an_existing_file(tmp_path):
    out_path = tmp_path / "warnings.txt"
    out_path.write_text("stale content from a previous run\n", encoding="utf-8")

    write_warnings_report(out_path, [], [])

    written_text = out_path.read_text(encoding="utf-8")
    assert "stale content" not in written_text
    assert "No passages failed to analyze." in written_text


def test_write_warnings_report_accepts_a_plain_string_path(tmp_path):
    out_path = str(tmp_path / "warnings.txt")
    returned = write_warnings_report(out_path, [], [])
    assert returned == Path(out_path)
    assert Path(out_path).exists()
