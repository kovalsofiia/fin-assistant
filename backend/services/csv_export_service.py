import csv
import io
from datetime import date, datetime
from typing import Dict, List, Optional

from core.database import supabase
class CsvExportService:
    UTF8_BOM = "\ufeff"

    @staticmethod
    def _to_csv(rows: List[Dict], fieldnames: List[str]) -> str:
        buffer = io.StringIO()
        buffer.write(CsvExportService.UTF8_BOM)
        writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})
        return buffer.getvalue()

    @staticmethod
    def _load_category_map(user_id: str) -> Dict[str, str]:
        res = (
            supabase.table("categories")
            .select("id, name, user_id")
            .or_(f"user_id.is.null,user_id.eq.{user_id}")
            .execute()
        )
        return {str(r["id"]): r.get("name", "") for r in (res.data or []) if r.get("id")}

    @staticmethod
    def export_transactions(
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> str:
        query = (
            supabase.table("transactions")
            .select(
                "transaction_id, transaction_date, transaction_type, transaction_amount, "
                "category_id, is_fop, currency_code, amount_original, exchange_rate, notes"
            )
            .eq("user_id", user_id)
            .order("transaction_date", desc=False)
        )
        if start_date:
            query = query.gte("transaction_date", start_date)
        if end_date:
            query = query.lte("transaction_date", end_date)

        txs = query.execute().data or []
        cat_map = CsvExportService._load_category_map(user_id)

        rows = []
        for tx in txs:
            rows.append(
                {
                    "date": tx.get("transaction_date", ""),
                    "type": tx.get("transaction_type", ""),
                    "amount_uah": tx.get("transaction_amount", 0),
                    "category": cat_map.get(str(tx.get("category_id")), ""),
                    "is_fop": "так" if tx.get("is_fop", True) else "ні",
                    "currency": tx.get("currency_code", "UAH"),
                    "amount_original": tx.get("amount_original") or "",
                    "exchange_rate": tx.get("exchange_rate") or "",
                    "description": (tx.get("notes") or "").replace("\n", " "),
                    "transaction_id": tx.get("transaction_id", ""),
                }
            )

        return CsvExportService._to_csv(
            rows,
            [
                "date",
                "type",
                "amount_uah",
                "category",
                "is_fop",
                "currency",
                "amount_original",
                "exchange_rate",
                "description",
                "transaction_id",
            ],
        )

    @staticmethod
    def export_financial_report(
        user_id: str,
        start_date: str,
        end_date: str,
    ) -> str:
        query = (
            supabase.table("transactions")
            .select("transaction_amount, transaction_type, category_id, is_fop")
            .eq("user_id", user_id)
            .gte("transaction_date", start_date)
            .lte("transaction_date", end_date)
        )
        txs = query.execute().data or []
        cat_map = CsvExportService._load_category_map(user_id)

        by_category: Dict[str, Dict[str, float]] = {}
        total_income = 0.0
        total_expense = 0.0
        fop_income = 0.0

        for tx in txs:
            amount = float(tx.get("transaction_amount", 0) or 0)
            cat_id = str(tx.get("category_id") or "uncategorized")
            cat_name = cat_map.get(cat_id, "Без категорії")
            bucket = by_category.setdefault(
                cat_name,
                {"income": 0.0, "expense": 0.0},
            )
            is_fop = tx.get("is_fop", True) if tx.get("is_fop") is not None else True
            if tx.get("transaction_type") == "income":
                bucket["income"] += amount
                total_income += amount
                if is_fop:
                    fop_income += amount
            else:
                bucket["expense"] += amount
                total_expense += amount

        rows = [
            {
                "section": "Підсумок",
                "category": "Усі",
                "income_uah": round(total_income, 2),
                "expense_uah": round(total_expense, 2),
                "net_uah": round(total_income - total_expense, 2),
                "fop_income_uah": round(fop_income, 2),
                "period_start": start_date,
                "period_end": end_date,
            }
        ]
        for cat_name, vals in sorted(by_category.items()):
            rows.append(
                {
                    "section": "Категорія",
                    "category": cat_name,
                    "income_uah": round(vals["income"], 2),
                    "expense_uah": round(vals["expense"], 2),
                    "net_uah": round(vals["income"] - vals["expense"], 2),
                    "fop_income_uah": "",
                    "period_start": start_date,
                    "period_end": end_date,
                }
            )

        return CsvExportService._to_csv(
            rows,
            [
                "section",
                "category",
                "income_uah",
                "expense_uah",
                "net_uah",
                "fop_income_uah",
                "period_start",
                "period_end",
            ],
        )

    @staticmethod
    def export_tax_history(user_id: str, year: Optional[int] = None) -> str:
        query = (
            supabase.table("tax_records")
            .select("year, month, fop_income, esv, income_tax, military_tax, is_paid")
            .eq("user_id", user_id)
            .order("year", desc=False)
            .order("month", desc=False)
        )
        if year:
            query = query.eq("year", year)

        records = query.execute().data or []
        rows = []
        for r in records:
            total_tax = round(
                float(r.get("esv", 0) or 0)
                + float(r.get("income_tax", 0) or 0)
                + float(r.get("military_tax", 0) or 0),
                2,
            )
            rows.append(
                {
                    "year": r.get("year", ""),
                    "month": r.get("month", ""),
                    "fop_income_uah": r.get("fop_income", 0),
                    "single_tax_uah": r.get("income_tax", 0),
                    "esv_uah": r.get("esv", 0),
                    "military_tax_uah": r.get("military_tax", 0),
                    "total_tax_uah": total_tax,
                    "is_paid": "так" if r.get("is_paid") else "ні",
                }
            )

        return CsvExportService._to_csv(
            rows,
            [
                "year",
                "month",
                "fop_income_uah",
                "single_tax_uah",
                "esv_uah",
                "military_tax_uah",
                "total_tax_uah",
                "is_paid",
            ],
        )

    @staticmethod
    def filename(export_type: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
        stamp = datetime.now().strftime("%Y%m%d")
        if export_type == "transactions":
            return f"fop_transactions_{start_date or 'all'}_{end_date or 'all'}_{stamp}.csv"
        if export_type == "report":
            return f"fop_report_{start_date}_{end_date}_{stamp}.csv"
        if export_type == "tax_history":
            return f"fop_tax_history_{stamp}.csv"
        return f"fop_export_{stamp}.csv"
