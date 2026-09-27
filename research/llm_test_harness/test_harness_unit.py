"""Юніт-тести самого харнесу (без звернень до мережі): extract, mutants, sandbox-парсер."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

from extract import NoCodeFoundError, extract_python_code
from mutants import MUTANTS, apply_mutant
from run_pilot import _avg, evaluate_test_file, summarize
from sandbox import _parse_pytest_summary


def test_extract_single_fenced_block():
    text = "Ось тести:\n```python\ndef test_x():\n    assert True\n```\nГотово."
    assert extract_python_code(text) == "def test_x():\n    assert True\n"


def test_extract_picks_longest_block_when_multiple():
    text = "```python\nimport pytest\n```\n\nА ось повний файл:\n\n```python\nimport pytest\n\n\ndef test_a():\n    pass\n```"
    code = extract_python_code(text)
    assert "def test_a()" in code


def test_extract_fence_without_language_tag():
    text = "```\ndef test_y():\n    assert 1 == 1\n```"
    assert "def test_y" in extract_python_code(text)


def test_extract_raises_when_no_code_block():
    with pytest.raises(NoCodeFoundError):
        extract_python_code("Вибачте, не можу згенерувати тести.")


def test_all_mutants_apply_exactly_once_and_change_source():
    original = Path(__file__).resolve().parents[2] / "backend/agent/drafts.py"
    source = original.read_text()
    seen = set()
    for mutant in MUTANTS:
        mutated = apply_mutant(source, mutant)
        assert mutated != source
        compile(mutated, mutant.id, "exec")
        seen.add(mutant.id)
    assert len(seen) == len(MUTANTS)  # унікальні id


def test_parse_pytest_summary_passed_only():
    result = _parse_pytest_summary("......\n16 passed in 0.01s\n")
    assert result == {"passed": 16, "failed": 0, "errors": 0, "summary_line": "16 passed in 0.01s"}


def test_parse_pytest_summary_mixed():
    result = _parse_pytest_summary(".....F\n5 passed, 1 failed in 0.02s\n")
    assert result["passed"] == 5
    assert result["failed"] == 1


def test_parse_pytest_summary_collection_error():
    result = _parse_pytest_summary("ImportError: cannot import name 'x'\n1 error in 0.01s\n")
    assert result["errors"] == 1
    assert result["passed"] == 0


def test_reference_test_suite_kills_six_of_seven_mutants():
    original = Path(__file__).resolve().parents[2] / "backend/agent/drafts.py"
    test_source = Path(__file__).resolve().parents[2] / "backend/tests/test_drafts.py"

    evaluation = evaluate_test_file(original.read_text(), test_source.read_text())

    assert evaluation["baseline"]["collection_error"] is False
    assert evaluation["baseline"]["passed"] == 16
    assert evaluation["baseline"]["coverage"]["percent_covered"] == 100.0
    assert evaluation["mutation_score"] == pytest.approx(6 / 7, abs=0.001)  # округлено до 3 знаків у evaluate_test_file
    killed = {m["mutant_id"] for m in evaluation["mutation_results"] if m["killed"]}
    assert killed == {m.id for m in MUTANTS} - {"m5_is_fop_not_bool"}


def test_broken_test_file_skips_mutation_scoring_instead_of_inflating_it():
    """Регресія: файл, що не збирається, раніше отримував mutation_score=1.0 (усі мутанти
    'вбито' лише тому, що кожен прогін падає однаково — і проти оригіналу, і проти мутанта)."""
    original = Path(__file__).resolve().parents[2] / "backend/agent/drafts.py"

    evaluation = evaluate_test_file(original.read_text(), "def test_broken(:\n    pass\n")

    assert evaluation["baseline"]["collection_error"] is True
    assert evaluation["mutation_score"] is None
    assert evaluation["mutation_results"] == []


def test_avg_ignores_none_and_handles_all_none():
    assert _avg([1.0, None, 3.0], 2) == 2.0
    assert _avg([None, None], 2) is None
    assert _avg([], 2) is None


def test_summarize_handles_mixed_statuses_without_crashing():
    records = [
        {
            "model_label": "M",
            "status": "evaluated",
            "pass_rate": 1.0,
            "line_coverage_pct": 100.0,
            "mutation_score": None,  # файл не збирався
            "latency_s": 1.0,
            "cost_usd": 0.001,
        },
        {"model_label": "M", "status": "api_error", "latency_s": 0.5, "cost_usd": 0.0},
    ]

    rows = summarize(records)

    assert rows == [
        {
            "model": "M",
            "runs": 2,
            "evaluated_runs": 1,
            "avg_pass_rate": 1.0,
            "avg_line_coverage_pct": 100.0,
            "avg_mutation_score": None,
            "mutation_score_stability_range": None,
            "avg_latency_s": 0.75,
            "total_cost_usd": 0.001,
        }
    ]
