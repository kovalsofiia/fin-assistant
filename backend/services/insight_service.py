from datetime import date, datetime, timedelta
from statistics import pstdev
from typing import Dict, List, Optional, Tuple

from core.database import supabase


class InsightService:
    @staticmethod
    def _parse_date(value: str) -> date:
        return datetime.fromisoformat(value).date()

    @staticmethod
    def _to_iso(value: date) -> str:
        return value.isoformat()

    @staticmethod
    def _safe_float(value) -> float:
        try:
            return float(value or 0)
        except Exception:
            return 0.0

    @staticmethod
    def _period_bounds(start_date: date, end_date: date) -> Tuple[date, date]:
        if end_date < start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        return start_date, end_date

    @staticmethod
    def _previous_period(start_date: date, end_date: date) -> Tuple[date, date]:
        days = (end_date - start_date).days + 1
        prev_end = start_date - timedelta(days=1)
        prev_start = prev_end - timedelta(days=days - 1)
        return prev_start, prev_end

    @staticmethod
    def _load_transactions(user_id: str, start_date: date, end_date: date) -> List[Dict]:
        res = (
            supabase.table("transactions")
            .select("transaction_amount, transaction_type, category_id, transaction_date")
            .eq("user_id", user_id)
            .gte("transaction_date", InsightService._to_iso(start_date))
            .lte("transaction_date", InsightService._to_iso(end_date))
            .execute()
        )
        return res.data or []

    @staticmethod
    def _load_category_names(user_id: str) -> Dict[str, str]:
        res = (
            supabase.table("categories")
            .select("id, name, user_id")
            .or_(f"user_id.is.null,user_id.eq.{user_id}")
            .execute()
        )
        names: Dict[str, str] = {}
        for row in (res.data or []):
            category_id = row.get("id")
            name = row.get("name")
            if category_id and name:
                names[category_id] = name
        return names

    @staticmethod
    def _load_budget_limits(user_id: str) -> Dict[str, float]:
        res = supabase.table("budgets").select("category_id, amount").eq("user_id", user_id).execute()
        limits: Dict[str, float] = {}
        for row in (res.data or []):
            cat_id = row.get("category_id")
            amount = InsightService._safe_float(row.get("amount"))
            if cat_id and amount > 0:
                limits[cat_id] = max(limits.get(cat_id, 0.0), amount)
        return limits

    @staticmethod
    def _aggregate_expenses(transactions: List[Dict]) -> Dict[str, Dict]:
        by_category: Dict[str, Dict] = {}
        for tx in transactions:
            if tx.get("transaction_type") != "expense":
                continue
            cat_id = tx.get("category_id") or "uncategorized"
            amount = InsightService._safe_float(tx.get("transaction_amount"))
            tx_date = tx.get("transaction_date")

            bucket = by_category.setdefault(cat_id, {"spent": 0.0, "daily": {}})
            bucket["spent"] += amount
            if tx_date:
                bucket["daily"][tx_date] = bucket["daily"].get(tx_date, 0.0) + amount
        return by_category

    @staticmethod
    def _sum_by_type(transactions: List[Dict], tx_type: str) -> float:
        return round(
            sum(
                InsightService._safe_float(tx.get("transaction_amount"))
                for tx in transactions
                if tx.get("transaction_type") == tx_type
            ),
            2,
        )

    @staticmethod
    def _volatility_score(daily_map: Dict[str, float]) -> float:
        values = list(daily_map.values())
        if len(values) < 2:
            return 0.0
        mean_val = sum(values) / len(values)
        if mean_val <= 0:
            return 0.0
        coefficient = pstdev(values) / mean_val
        return min(100.0, max(0.0, coefficient * 100))

    @staticmethod
    def _score_category(share_pct: float, delta_pct: float, budget_usage_pct: Optional[float], volatility_score: float) -> float:
        share_score = min(100.0, max(0.0, share_pct))
        growth_score = min(100.0, max(0.0, delta_pct if delta_pct > 0 else 0.0))
        if budget_usage_pct is None:
            budget_score = 0.0
        else:
            budget_score = min(100.0, max(0.0, budget_usage_pct - 100.0))

        score = (
            0.35 * share_score
            + 0.25 * growth_score
            + 0.25 * budget_score
            + 0.15 * volatility_score
        )
        return round(min(100.0, max(0.0, score)), 1)

    @staticmethod
    def _severity(score: float) -> str:
        if score >= 70:
            return "high"
        if score >= 40:
            return "medium"
        return "low"

    @staticmethod
    def _fmt_uah(amount: float) -> str:
        value = round(amount, 2)
        if value == int(value):
            text = f"{int(value):,}".replace(",", " ")
        else:
            whole, frac = f"{value:,.2f}".split(".")
            text = f"{whole.replace(',', ' ')},{frac}"
        return f"{text} грн"

    @staticmethod
    def _conclusion(category_name: str, spent_current: float, delta_pct: float, share_pct: float, budget_usage_pct: Optional[float]) -> str:
        parts = [f"За обраний період на {category_name} пішло {InsightService._fmt_uah(spent_current)}."]

        if share_pct >= 10:
            parts.append(f"Це {round(share_pct, 1)}% усіх ваших витрат.")
        elif share_pct > 0:
            parts.append(f"Частка серед усіх витрат: {round(share_pct, 1)}%.")

        if delta_pct > 5:
            parts.append(f"Порівняно з минулим періодом витрати зросли на {round(delta_pct, 1)}%.")
        elif delta_pct < -5:
            parts.append(f"Порівняно з минулим періодом витрати зменшились на {abs(round(delta_pct, 1))}%.")
        elif spent_current > 0 and delta_pct != 0:
            parts.append(f"До минулого періоду зміна невелика ({round(delta_pct, 1)}%).")

        if budget_usage_pct is not None and budget_usage_pct > 100:
            parts.append(f"Ліміт бюджету перевищено на {round(budget_usage_pct - 100, 1)}%.")
        elif budget_usage_pct is not None and budget_usage_pct >= 85:
            parts.append(f"Від запланованого бюджету вже використано {round(budget_usage_pct, 1)}%.")

        return " ".join(parts)

    @staticmethod
    def _recommendations(category_name: str, spent_current: float, delta_pct: float, budget_usage_pct: Optional[float]) -> List[str]:
        recs: List[str] = []
        if budget_usage_pct is not None and budget_usage_pct > 100:
            target = round(spent_current * 0.9, 2)
            recs.append(
                f"Можливо, варто підняти ліміт до {InsightService._fmt_uah(target)} "
                f"і раз на тиждень перевіряти, чи не виходите за межі в {category_name}."
            )
        if delta_pct > 20:
            recs.append(
                f"Загляньте в три найбільші платежі в {category_name}. "
                "Зазвичай саме вони дають такий стрибок."
            )
        if not recs:
            recs.append(
                f"У {category_name} зараз усе спокійно. "
                "Раз на тиждень вистачить короткого перегляду витрат."
            )
        return recs[:2]

    @staticmethod
    def build_insights(user_id: str, start_date_raw: str, end_date_raw: str) -> Dict:
        start_date = InsightService._parse_date(start_date_raw)
        end_date = InsightService._parse_date(end_date_raw)
        start_date, end_date = InsightService._period_bounds(start_date, end_date)
        prev_start, prev_end = InsightService._previous_period(start_date, end_date)

        current_txs = InsightService._load_transactions(user_id, start_date, end_date)
        previous_txs = InsightService._load_transactions(user_id, prev_start, prev_end)
        category_names = InsightService._load_category_names(user_id)
        budget_limits = InsightService._load_budget_limits(user_id)

        total_income = InsightService._sum_by_type(current_txs, "income")
        total_expense = InsightService._sum_by_type(current_txs, "expense")
        savings_rate = 0.0 if total_income <= 0 else round(((total_income - total_expense) / total_income) * 100, 1)

        current_expenses = InsightService._aggregate_expenses(current_txs)
        previous_expenses = InsightService._aggregate_expenses(previous_txs)

        insights: List[Dict] = []
        for category_id, data in current_expenses.items():
            spent_current = round(data["spent"], 2)
            spent_prev = round(previous_expenses.get(category_id, {}).get("spent", 0.0), 2)
            delta_abs = round(spent_current - spent_prev, 2)
            delta_pct = round((delta_abs / spent_prev) * 100, 1) if spent_prev > 0 else (100.0 if spent_current > 0 else 0.0)
            share_pct = round((spent_current / total_expense) * 100, 1) if total_expense > 0 else 0.0

            budget_limit = budget_limits.get(category_id)
            budget_usage_pct = round((spent_current / budget_limit) * 100, 1) if budget_limit and budget_limit > 0 else None
            volatility = InsightService._volatility_score(data["daily"])
            score = InsightService._score_category(share_pct, delta_pct, budget_usage_pct, volatility)
            severity = InsightService._severity(score)

            category_name = category_names.get(category_id, "Без категорії")
            insight = {
                "category_id": category_id,
                "category_name": category_name,
                "spent_current": spent_current,
                "spent_previous": spent_prev,
                "delta_abs": delta_abs,
                "delta_pct": delta_pct,
                "share_of_total": share_pct,
                "budget_usage_pct": budget_usage_pct,
                "risk_score": score,
                "severity": severity,
                "conclusion": InsightService._conclusion(category_name, spent_current, delta_pct, share_pct, budget_usage_pct),
                "recommendations": InsightService._recommendations(category_name, spent_current, delta_pct, budget_usage_pct),
            }
            insights.append(insight)

        insights.sort(key=lambda x: x["risk_score"], reverse=True)

        top3_share = round(sum(i["share_of_total"] for i in insights[:3]), 1) if insights else 0.0
        global_recommendations: List[str] = []
        if top3_share >= 70:
            global_recommendations.append(
                "Більшість грошей йде в три категорії. "
                "Якщо хочете витрачати менше, почніть переглядати витрати саме там."
            )
        if savings_rate < 10 and total_income > 0:
            global_recommendations.append(
                "Після всіх витрат залишається мало. "
                "Подивіться категорії з найвищим ризиком і спробуйте скоротити їх хоча б на 10%."
            )
        if not global_recommendations:
            global_recommendations.append(
                "Картина витрат виглядає рівною. "
                "Раз на тиждень переглядайте топ-категорії, цього зазвичай достатньо."
            )

        return {
            "summary": {
                "start_date": InsightService._to_iso(start_date),
                "end_date": InsightService._to_iso(end_date),
                "previous_start_date": InsightService._to_iso(prev_start),
                "previous_end_date": InsightService._to_iso(prev_end),
                "total_income": total_income,
                "total_expense": total_expense,
                "savings_rate": savings_rate,
                "top3_concentration": top3_share,
            },
            "category_insights": insights,
            "global_recommendations": global_recommendations,
        }
