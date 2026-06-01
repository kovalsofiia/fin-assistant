"""Мапінг tax_rules (API/БД) → контекст квізу (узгоджено з frontend taxRulesContext.js)."""

from typing import Any, Dict

from core.constants import (
    DEFAULT_G3_RATE,
    DEFAULT_G3_VAT_RATE,
    DEFAULT_G4_RATE,
    DEFAULT_MILITARY_RATE,
    FIXED_MILITARY_TAX,
    LIMIT_G1,
    LIMIT_G2,
    LIMIT_G3,
    MIN_ESV_2026,
    MIN_WAGE_2026,
    SINGLE_TAX_G1,
    SINGLE_TAX_G2,
)
from core.tax_rules_defaults import default_tax_rules_for_period


def _num(value: Any, fallback: float = 0.0) -> float:
    try:
        n = float(value)
        return n if n == n else fallback  # noqa: PLR0124 — NaN check
    except (TypeError, ValueError):
        return fallback


def emergency_quiz_rules_from_constants() -> Dict[str, Any]:
    return map_api_tax_rules_to_quiz_context(default_tax_rules_for_period(2026, 1))


def map_api_tax_rules_to_quiz_context(api: Dict[str, Any] | None) -> Dict[str, Any]:
    if not api or not isinstance(api, dict):
        return emergency_quiz_rules_from_constants()

    military = _num(api.get("fixed_military_tax"), FIXED_MILITARY_TAX)

    return {
        "limits": {
            "g1": _num(api.get("limit_g1"), LIMIT_G1),
            "g2": _num(api.get("limit_g2"), LIMIT_G2),
            "g3": _num(api.get("limit_g3"), LIMIT_G3),
        },
        "limitMzpUnits": {
            "g1": int(_num(api.get("limit_g1_mzp_units"), 167)),
            "g2": int(_num(api.get("limit_g2_mzp_units"), 834)),
            "g3": int(_num(api.get("limit_g3_mzp_units"), 1167)),
        },
        "monthlyFixed": {
            "g1": {
                "single": _num(api.get("single_tax_g1"), SINGLE_TAX_G1),
                "military": military,
            },
            "g2": {
                "single": _num(api.get("single_tax_g2"), SINGLE_TAX_G2),
                "military": military,
            },
        },
        "esvMonthly": _num(api.get("esv_value"), MIN_ESV_2026),
        "vatThreshold": _num(api.get("vat_supply_threshold"), 1_000_000.0),
        "g3": {
            "epNonVat": _num(api.get("income_tax_percent"), DEFAULT_G3_RATE),
            "epVat": _num(api.get("income_tax_percent_vat"), DEFAULT_G3_VAT_RATE),
            "militaryPct": _num(api.get("military_tax_percent"), DEFAULT_MILITARY_RATE),
        },
        "g4Rates": {
            "arable_pasture": _num(api.get("g4_rate_arable"), DEFAULT_G4_RATE),
            "water": _num(api.get("g4_rate_water"), 2.43),
            "closed_soil": _num(api.get("g4_rate_closed_soil"), 6.33),
        },
        "militaryFixedMonthly": military,
        "minWage": _num(api.get("min_wage"), MIN_WAGE_2026),
    }
