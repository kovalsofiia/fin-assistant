"""Перерахунок mutation_score у вже зібраних results/runs.jsonl без повторних викликів API.

Потрібен, коли логіка оцінювання (evaluate_test_file) зміниться заднім числом: сирі
mutation_details у кожному записі не чіпаються, лише правило "коли mutation_score
рахувати" застосовується наново, і summary.csv перезбирається.
"""
import csv
import json
import sys
from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parent
RESULTS_DIR = HARNESS_DIR / "results"
sys.path.insert(0, str(HARNESS_DIR))

from run_pilot import summarize  # noqa: E402


def rescore(record: dict) -> dict:
    if record.get("status") != "evaluated":
        return record
    baseline_all_passing = (
        not record["collection_error"] and record["tests_failed"] == 0 and record["tests_errors"] == 0
    )
    if not baseline_all_passing:
        record["mutation_score"] = None
        record["mutation_details"] = []
    return record


def main():
    runs_path = RESULTS_DIR / "runs.jsonl"
    records = [json.loads(line) for line in runs_path.read_text().splitlines() if line.strip()]
    records = [rescore(r) for r in records]

    with runs_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    summary_rows = summarize(records)
    with (RESULTS_DIR / "summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()) if summary_rows else [])
        writer.writeheader()
        writer.writerows(summary_rows)
    print(f"Перераховано {len(records)} записів. Зведення: {RESULTS_DIR / 'summary.csv'}")


if __name__ == "__main__":
    main()
