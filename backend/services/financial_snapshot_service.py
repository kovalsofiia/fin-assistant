"""Агрегація фінансових операцій для податкової рекомендації (крок 1)."""

from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from core.database import supabase


class FinancialSnapshotService:
    @staticmethod
    def _parse_date(value: str) -> date:
        return date.fromisoformat(value[:10])

    @staticmethod
    def _month_key(d: date) -> str:
        return f"{d.year}-{d.month:02d}"

    @staticmethod
    def default_period(reference: Optional[date] = None) -> Tuple[date, date]:
        """Календарний рік, в якому знаходиться reference (за замовчуванням — сьогодні)."""
        ref = reference or date.today()
        return date(ref.year, 1, 1), date(ref.year, 12, 31)

    @staticmethod
    def build_snapshot(
        user_id: str,
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        if end_date < start_date:
            raise ValueError("end_date must be >= start_date")

        res = (
            supabase.table("transactions")
            .select(
                "transaction_amount, transaction_type, transaction_date, "
                "is_fop, is_foreign_currency, currency_code"
            )
            .eq("user_id", user_id)
            .gte("transaction_date", start_date.isoformat())
            .lte("transaction_date", end_date.isoformat())
            .execute()
        )
        rows: List[Dict] = res.data or []

        income_fop_by_month: Dict[str, float] = {}
        income_total = 0.0
        income_fop = 0.0
        income_personal = 0.0
        fx_income_uah = 0.0
        expense_fop = 0.0
        expense_personal = 0.0
        months_with_fop_income: set[str] = set()

        for tx in rows:
            amount = float(tx.get("transaction_amount") or 0)
            tx_type = tx.get("transaction_type")
            is_fop = tx.get("is_fop", True)
            if is_fop is None:
                is_fop = True

            if tx_type == "income":
                income_total += amount
                if is_fop:
                    income_fop += amount
                    date_str = str(tx.get("transaction_date", ""))[:10]
                    if date_str:
                        mk = date_str[:7]
                        if len(mk) == 7:
                            income_fop_by_month[mk] = income_fop_by_month.get(mk, 0.0) + amount
                            months_with_fop_income.add(mk)
                    is_fx = bool(tx.get("is_foreign_currency")) or (
                        str(tx.get("currency_code") or "UAH").upper() != "UAH"
                    )
                    if is_fx:
                        fx_income_uah += amount
                else:
                    income_personal += amount
            elif tx_type == "expense":
                if is_fop:
                    expense_fop += amount
                else:
                    expense_personal += amount

        fop_income_period = sum(income_fop_by_month.values())
        months_count = len(months_with_fop_income)

        projected_annual, projection_method = FinancialSnapshotService._project_annual_income(
            income_fop_by_month, start_date, end_date
        )

        fx_share = round((fx_income_uah / income_fop) * 100, 1) if income_fop > 0 else 0.0
        confidence = FinancialSnapshotService._confidence(months_count, start_date, end_date)

        return {
            "period": {
                "from": start_date.isoformat(),
                "to": end_date.isoformat(),
            },
            "income_total_uah": round(income_total, 2),
            "income_fop_uah": round(income_fop, 2),
            "income_personal_uah": round(income_personal, 2),
            "fx_income_uah": round(fx_income_uah, 2),
            "fx_income_share_percent": fx_share,
            "expense_fop_uah": round(expense_fop, 2),
            "expense_personal_uah": round(expense_personal, 2),
            "income_fop_by_month": {k: round(v, 2) for k, v in sorted(income_fop_by_month.items())},
            "fop_income_in_period_uah": round(fop_income_period, 2),
            "months_with_fop_income": months_count,
            "projected_annual_income_uah": round(projected_annual, 2),
            "projection_method": projection_method,
            "confidence": confidence,
        }

    @staticmethod
    def _project_annual_income(
        income_by_month: Dict[str, float],
        start_date: date,
        end_date: date,
    ) -> Tuple[float, str]:
        total = sum(income_by_month.values())
        if not income_by_month:
            return 0.0, "no_data"

        # Повний календарний рік у межах періоду
        if start_date.month == 1 and start_date.day == 1 and end_date.month == 12 and end_date.day == 31:
            if start_date.year == end_date.year:
                return total, "calendar_year_actual"

        months_in_range = FinancialSnapshotService._months_between(start_date, end_date)
        if months_in_range <= 0:
            return total, "partial_sum"

        if len(income_by_month) >= months_in_range:
            return total, "period_sum"

        # Екстраполяція: середній місячний × 12
        avg_monthly = total / max(len(income_by_month), 1)
        return avg_monthly * 12, "extrapolated_12m"

    @staticmethod
    def _months_between(start_date: date, end_date: date) -> int:
        return (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month) + 1

    @staticmethod
    def _confidence(months_with_data: int, start_date: date, end_date: date) -> str:
        span = FinancialSnapshotService._months_between(start_date, end_date)
        if months_with_data >= 12 or (span >= 12 and months_with_data >= 10):
            return "high"
        if months_with_data >= 6:
            return "medium"
        return "low"
