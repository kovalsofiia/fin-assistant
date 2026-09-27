"""Ізольована пісочниця для запуску згенерованих тестів проти drafts.py або його мутанта.

Пісочниця — мінімальний пакет {agent/drafts.py, core/constants.py} без решти backend
(без FastAPI, Supabase, openai): drafts.py залежить лише від стандартної бібліотеки й
core.constants.MIN_TRANSACTION_AMOUNT, тож тести виконуються миттєво й без мережі.
"""
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DRAFTS_SOURCE_PATH = REPO_ROOT / "backend/agent/drafts.py"
CONSTANTS_SOURCE_PATH = REPO_ROOT / "backend/core/constants.py"
PYTHON = REPO_ROOT / "backend/.venv/bin/python"

_SUMMARY_RE = re.compile(
    r"=+ (?:(?P<failed>\d+) failed, )?(?:(?P<passed>\d+) passed)?,?\s*(?:(?P<errors>\d+) error)?"
)


def read_original_source() -> str:
    return DRAFTS_SOURCE_PATH.read_text()


def build_sandbox(root: Path, drafts_source: str, test_source: str) -> None:
    """Створює в root: agent/{__init__.py, drafts.py}, core/{__init__.py, constants.py}, tests/test_generated.py."""
    (root / "agent").mkdir(parents=True, exist_ok=True)
    (root / "core").mkdir(parents=True, exist_ok=True)
    (root / "tests").mkdir(parents=True, exist_ok=True)
    (root / "agent/__init__.py").write_text("")
    (root / "agent/drafts.py").write_text(drafts_source)
    (root / "core/__init__.py").write_text("")
    (root / "core/constants.py").write_text(CONSTANTS_SOURCE_PATH.read_text())
    (root / "tests/__init__.py").write_text("")
    (root / "tests/test_generated.py").write_text(test_source)


def _parse_pytest_summary(output: str) -> dict:
    """Евристика над підсумковим рядком pytest (`-q`, напр. '16 passed in 0.01s' або '3 passed, 1 failed in 0.02s')."""
    lines = [l.strip() for l in output.splitlines() if l.strip()]
    line = next((l for l in reversed(lines) if re.search(r"\bin [\d.]+s\b", l) or "no tests ran" in l), "")
    passed = int(m.group(1)) if (m := re.search(r"(\d+) passed", line)) else 0
    failed = int(m.group(1)) if (m := re.search(r"(\d+) failed", line)) else 0
    errors = int(m.group(1)) if (m := re.search(r"(\d+) error", line)) else 0
    return {"passed": passed, "failed": failed, "errors": errors, "summary_line": line}


def run_tests(root: Path, with_coverage: bool = False) -> dict:
    """Запускає tests/test_generated.py в пісочниці. Ніколи не кидає — помилки виконання йдуть у результат."""
    env_cwd = str(root)
    if with_coverage:
        cmd = [
            str(PYTHON),
            "-m",
            "coverage",
            "run",
            "--branch",
            "--source=agent.drafts",
            "-m",
            "pytest",
            "tests/test_generated.py",
            "-q",
            "-p",
            "no:cacheprovider",
        ]
    else:
        cmd = [str(PYTHON), "-m", "pytest", "tests/test_generated.py", "-q", "-p", "no:cacheprovider"]

    proc = subprocess.run(cmd, cwd=env_cwd, capture_output=True, text=True, timeout=60)
    result = _parse_pytest_summary(proc.stdout)
    result["returncode"] = proc.returncode
    result["stdout_tail"] = "\n".join(proc.stdout.splitlines()[-15:])
    result["stderr_tail"] = "\n".join(proc.stderr.splitlines()[-15:])
    result["collection_error"] = "collected 0 items" in proc.stdout or "ERROR" in proc.stdout[:200]

    if with_coverage and proc.returncode in (0, 1):
        cov_proc = subprocess.run(
            [str(PYTHON), "-m", "coverage", "json", "-o", "-"], cwd=env_cwd, capture_output=True, text=True
        )
        result["coverage"] = _extract_coverage_percent(cov_proc.stdout)
    elif with_coverage:
        result["coverage"] = None
    return result


def _extract_coverage_percent(coverage_json_text: str) -> dict:
    import json

    try:
        data = json.loads(coverage_json_text)
        totals = data["totals"]
        return {
            "percent_covered": totals["percent_covered"],
            "num_statements": totals["num_statements"],
            "missing_lines": totals["missing_lines"],
            "num_branches": totals.get("num_branches", 0),
            "missing_branches": totals.get("missing_branches", 0),
        }
    except Exception:
        return None
