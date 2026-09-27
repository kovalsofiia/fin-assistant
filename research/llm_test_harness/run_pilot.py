"""Пілотний експеримент: N моделей генерують pytest-тести для backend/agent/drafts.py.

Для кожної (модель, повтор): один запит до OpenRouter → витяг коду → запуск у пісочниці
проти оригінального модуля (correctness, coverage) і проти 7 мутантів (mutation score).
Результат — по одному рядку JSON у results/runs.jsonl і зведення в results/summary.csv.

Використання (з кореня репозиторію):
    backend/.venv/bin/python research/llm_test_harness/run_pilot.py                # усі моделі з config.PILOT_MODELS
    backend/.venv/bin/python research/llm_test_harness/run_pilot.py grok sonnet    # лише моделі, чия label містить ці підрядки

Результати дописуються в results/runs.jsonl (не перезаписують попередні запуски —
можна докидати нові моделі окремими викликами), а results/summary.csv щоразу
перезбирається з УСІХ накопичених записів.

Ключ моделі береться з backend/.env (LLM_API_KEY, LLM_BASE_URL) — цей скрипт лише
завантажує його в змінні середовища процесу і ніколи не друкує.
"""
import csv
import json
import statistics
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parent
REPO_ROOT = HARNESS_DIR.parents[1]
RESULTS_DIR = HARNESS_DIR / "results"
GENERATED_DIR = RESULTS_DIR / "generated"

sys.path.insert(0, str(HARNESS_DIR))
sys.path.insert(0, str(REPO_ROOT / "backend"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO_ROOT / "backend/.env")

import httpx  # noqa: E402
from openai import OpenAI  # noqa: E402

import config  # noqa: E402
import mutants  # noqa: E402
import sandbox  # noqa: E402
from extract import NoCodeFoundError, extract_python_code  # noqa: E402
from prompts import build_prompt  # noqa: E402

import os  # noqa: E402

LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")


def _do_call(client: OpenAI, model: config.ModelSpec, prompt: str):
    return client.chat.completions.create(
        model=model.id,
        messages=[{"role": "user", "content": prompt}],
        temperature=config.TEMPERATURE,
        timeout=config.REQUEST_TIMEOUT_S,
    )


# Спостерігали (2026-09-27): запуск цього скрипта як ФОНОВОГО/відв'язаного процесу
# (nohup ... & або backgrounded shell job) робив виклики до OpenRouter аномально повільними
# (за одним запитом минуло 10+ хвилин без відповіді) — але той самий запит з тим самим кодом
# у ПЕРЕДНЬОМУ плані виконувався за 30-50с, і це підтвердилося для кількох різних моделей
# (DeepSeek, Claude Sonnet 5), тобто причина не в конкретному провайдері, а в тому, як це
# середовище розробки обробляє мережу для фонових процесів. Явний httpx-клієнт із тайм-аутом
# на кожній фазі з'єднання (connect/read/write/pool, enforced на рівні сокета) і
# ThreadPoolExecutor як другий рубіж захисту лишаються в коді як загальне посилення
# надійності — вони не є вичерпним рішенням для фонового запуску: практичний висновок
# (docs/practice/03-pilot-results.md) — цей скрипт варто запускати в передньому плані.
_HTTP_CLIENT = httpx.Client(timeout=httpx.Timeout(connect=10.0, read=config.REQUEST_TIMEOUT_S, write=10.0, pool=10.0))
_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="llm-call")


def call_model(client: OpenAI, model: config.ModelSpec, prompt: str) -> dict:
    """Один виклик моделі. Повертає {content, prompt_tokens, completion_tokens, latency_s} або {error}."""
    started = time.monotonic()
    future = _EXECUTOR.submit(_do_call, client, model, prompt)
    try:
        response = future.result(timeout=config.REQUEST_TIMEOUT_S + 30)
    except FutureTimeoutError:
        return {
            "error": f"Жорсткий тайм-аут {config.REQUEST_TIMEOUT_S + 30}с — провайдер не відповів",
            "latency_s": round(time.monotonic() - started, 2),
        }
    except Exception as exc:  # мережа/провайдер — фіксуємо як помилку запуску, не падаємо
        return {"error": f"{type(exc).__name__}: {exc}", "latency_s": round(time.monotonic() - started, 2)}

    latency_s = time.monotonic() - started
    usage = response.usage
    return {
        "content": response.choices[0].message.content or "",
        "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
        "completion_tokens": getattr(usage, "completion_tokens", 0) or 0,
        "latency_s": round(latency_s, 2),
    }


def evaluate_test_file(original_source: str, test_source: str) -> dict:
    """Ганяє test_source у пісочниці проти оригіналу (з покриттям) і проти кожного мутанта.

    Мутаційне тестування має сенс лише для test suite, який повністю проходить на оригіналі
    (стандартна вимога mutation testing: спершу «зелений» набір тестів, потім — мутанти).
    Якщо частина тестів уже падає на оригіналі (неправильні очікування в самих тестах) або
    файл узагалі не збирається — кожен прогін проти мутанта «падає» так само, незалежно від
    того, чи мутант справді зламав логіку, і mutation_score = 1.0 був би оманливим. У цих
    випадках мутаційне тестування пропускається, а mutation_score = None.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        sandbox.build_sandbox(root, original_source, test_source)
        baseline = sandbox.run_tests(root, with_coverage=True)

    baseline_all_passing = not baseline["collection_error"] and baseline["failed"] == 0 and baseline["errors"] == 0
    if not baseline_all_passing:
        return {"baseline": baseline, "mutation_results": [], "mutation_score": None}

    mutation_results = []
    for mutant in mutants.MUTANTS:
        mutated_source = mutants.apply_mutant(original_source, mutant)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sandbox.build_sandbox(root, mutated_source, test_source)
            result = sandbox.run_tests(root, with_coverage=False)
        killed = result["failed"] > 0 or result["errors"] > 0
        mutation_results.append({"mutant_id": mutant.id, "killed": killed})

    killed_count = sum(1 for m in mutation_results if m["killed"])
    return {
        "baseline": baseline,
        "mutation_results": mutation_results,
        "mutation_score": round(killed_count / len(mutants.MUTANTS), 3),
    }


def run_one(client, model: config.ModelSpec, repeat: int, original_source: str, prompt: str) -> dict:
    run_id = f"{model.label.replace(' ', '_')}_r{repeat}"
    call = call_model(client, model, prompt)
    record = {
        "model_id": model.id,
        "model_label": model.label,
        "repeat": repeat,
        "run_id": run_id,
        "latency_s": call.get("latency_s"),
    }
    if "error" in call:
        record.update(status="api_error", error=call["error"])
        return record

    prompt_tokens, completion_tokens = call["prompt_tokens"], call["completion_tokens"]
    record.update(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=round(config.estimate_cost_usd(model, prompt_tokens, completion_tokens), 6),
    )

    try:
        test_source = extract_python_code(call["content"])
    except NoCodeFoundError as exc:
        record.update(status="no_code_extracted", error=str(exc))
        return record

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    (GENERATED_DIR / f"{run_id}.py").write_text(test_source)

    evaluation = evaluate_test_file(original_source, test_source)
    baseline = evaluation["baseline"]
    coverage = baseline.get("coverage") or {}
    record.update(
        status="evaluated",
        collection_error=baseline["collection_error"],
        tests_passed=baseline["passed"],
        tests_failed=baseline["failed"],
        tests_errors=baseline["errors"],
        pass_rate=round(baseline["passed"] / max(baseline["passed"] + baseline["failed"], 1), 3)
        if not baseline["collection_error"]
        else 0.0,
        line_coverage_pct=coverage.get("percent_covered"),
        branch_coverage_missing=coverage.get("missing_branches"),
        mutation_score=evaluation["mutation_score"],
        mutation_details=evaluation["mutation_results"],
    )
    return record


def _avg(values: list, digits: int) -> float:
    """statistics.mean, що ігнорує None (метрика не застосовна для частини прогонів) і не падає на порожньому."""
    present = [v for v in values if v is not None]
    return round(statistics.mean(present), digits) if present else None


def summarize(records: list) -> list:
    """Одна зведена стрічка на модель: середні метрики + стабільність (розмах між повторами)."""
    rows = []
    by_model = {}
    for r in records:
        by_model.setdefault(r["model_label"], []).append(r)

    for label, runs in by_model.items():
        evaluated = [r for r in runs if r["status"] == "evaluated"]
        mutation_scores = [r["mutation_score"] for r in evaluated if r["mutation_score"] is not None]
        row = {
            "model": label,
            "runs": len(runs),
            "evaluated_runs": len(evaluated),
            "avg_pass_rate": _avg([r["pass_rate"] for r in evaluated], 3),
            "avg_line_coverage_pct": _avg([r["line_coverage_pct"] for r in evaluated], 1),
            "avg_mutation_score": _avg(mutation_scores, 3),
            "mutation_score_stability_range": round(max(mutation_scores) - min(mutation_scores), 3)
            if len(mutation_scores) > 1
            else None,
            "avg_latency_s": _avg([r["latency_s"] for r in runs], 2),
            "total_cost_usd": round(sum(r.get("cost_usd", 0) for r in runs), 6),
        }
        rows.append(row)
    return rows


def select_models(argv: list) -> list:
    """Усі PILOT_MODELS, або лише ті, чия label містить один із аргументів (без урахування регістру)."""
    if not argv:
        return config.PILOT_MODELS
    needles = [a.lower() for a in argv]
    selected = [m for m in config.PILOT_MODELS if any(n in m.label.lower() for n in needles)]
    unmatched = [n for n in needles if not any(n in m.label.lower() for m in config.PILOT_MODELS)]
    if unmatched:
        print(f"Попередження: жодна модель не відповідає підрядку(ам): {', '.join(unmatched)}")
    return selected


def _load_existing_records(runs_path: Path) -> list:
    if not runs_path.exists():
        return []
    return [json.loads(line) for line in runs_path.read_text().splitlines() if line.strip()]


def main():
    if not LLM_API_KEY:
        print("LLM_API_KEY не знайдено в backend/.env — зупинка.")
        sys.exit(1)

    models = select_models(sys.argv[1:])
    if not models:
        print("Жодної моделі для запуску (перевірте аргументи).")
        sys.exit(1)

    original_source = sandbox.read_original_source()
    prompt = build_prompt(original_source)
    client = OpenAI(
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
        timeout=config.REQUEST_TIMEOUT_S,
        max_retries=1,
        http_client=_HTTP_CLIENT,
    )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    runs_path = RESULTS_DIR / "runs.jsonl"
    new_records = []
    # Дописуємо (append), а не перезаписуємо: результати попередніх запусків з інших моделей
    # не губляться. Кожен запис пишеться одразу після прогону — якщо один провайдер зависне
    # чи впаде, уже зібрані результати цього ж виклику скрипта теж не втрачаються.
    with runs_path.open("a", encoding="utf-8") as f:
        for model in models:
            for repeat in range(1, config.REPEATS_PER_MODEL + 1):
                print(f"-> {model.label} (повтор {repeat}/{config.REPEATS_PER_MODEL})...", flush=True)
                record = run_one(client, model, repeat, original_source, prompt)
                print(f"   {record['status']}"
                      + (f" pass_rate={record.get('pass_rate')} mutation_score={record.get('mutation_score')}"
                         if record["status"] == "evaluated" else f" error={record.get('error')}"))
                new_records.append(record)
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                f.flush()

    all_records = _load_existing_records(runs_path)
    summary_rows = summarize(all_records)
    with (RESULTS_DIR / "summary.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()) if summary_rows else [])
        writer.writeheader()
        writer.writerows(summary_rows)

    total_cost = sum(r.get("cost_usd", 0) for r in new_records)
    print(f"\nГотово. {len(new_records)} нових запусків, вартість цього виклику ≈ ${total_cost:.4f}")
    print(f"Усього в runs.jsonl: {len(all_records)} записів.")
    print(f"Деталі: {runs_path}\nЗведення: {RESULTS_DIR / 'summary.csv'}")


if __name__ == "__main__":
    main()
