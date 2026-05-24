"""
Єдиний набір дефолтних податкових правил (орієнтир 2026).
Використовується як fallback у TaxService і для seed у БД.
"""

from typing import Any, Dict


def default_tax_rules_for_period(year: int, month: int) -> Dict[str, Any]:
    """Повний словник полів tax_rules для року/місяця."""
    return {
        "year": year,
        "month": month,
        "min_wage": 8650.0,
        "esv_value": 1902.34,
        "single_tax_g1": 332.80,
        "single_tax_g2": 1729.40,
        "fixed_military_tax": 864.70,
        "limit_g1": 1_444_049.0,
        "limit_g2": 7_211_598.0,
        "limit_g3": 10_091_049.0,
        "limit_g1_mzp_units": 167,
        "limit_g2_mzp_units": 834,
        "limit_g3_mzp_units": 1167,
        "income_tax_percent": 5.0,
        "income_tax_percent_vat": 3.0,
        "military_tax_percent": 1.0,
        "g4_rate_arable": 0.95,
        "g4_rate_water": 2.43,
        "g4_rate_closed_soil": 6.33,
        "vat_supply_threshold": 1_000_000.0,
    }


TAX_RULES_FIELD_KEYS = list(default_tax_rules_for_period(2026, 1).keys())
TAX_RULES_NUMERIC_KEYS = [k for k in TAX_RULES_FIELD_KEYS if k not in ("year", "month")]
