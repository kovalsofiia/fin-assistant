"""Орієнтовний розрахунок загальної системи оподаткування (з/без ПДВ)."""

from typing import Any, Dict, Optional

# Ставки — орієнтир для порівняння сценаріїв (не заміна декларації)
PIT_RATE = 0.18
MILITARY_RATE_ON_INCOME = 0.05
VAT_RATE_ESTIMATE = 0.20
DEFAULT_VAT_REGISTRATION_THRESHOLD = 1_000_000.0


class GeneralTaxService:
    @staticmethod
    def vat_registration_required(
        gross_income_uah: float, threshold: Optional[float] = None
    ) -> bool:
        limit = threshold if threshold is not None else DEFAULT_VAT_REGISTRATION_THRESHOLD
        return gross_income_uah > limit

    @staticmethod
    def estimate_annual_tax(
        gross_income_uah: float,
        deductible_expenses_uah: float = 0.0,
        esv_annual_uah: float = 0.0,
        *,
        force_vat: Optional[bool] = None,
        vat_threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Загальна система:
        - база = max(0, дохід - витрати)
        - ПДФО 18% + військовий збір 5% від бази + ЄСВ
        - ПДВ 20% від gross лише тут: поріг 1 млн не стосується 3 групи спрощеної.
        """
        gross = max(0.0, float(gross_income_uah))
        expenses = max(0.0, float(deductible_expenses_uah))
        base = max(0.0, gross - expenses)

        vat_required = force_vat if force_vat is not None else GeneralTaxService.vat_registration_required(
            gross, vat_threshold
        )

        pit = base * PIT_RATE
        military = base * MILITARY_RATE_ON_INCOME
        esv = max(0.0, float(esv_annual_uah))
        vat_component = gross * VAT_RATE_ESTIMATE if vat_required else 0.0

        total = pit + military + esv + vat_component

        return {
            "tax_system": "general",
            "with_vat": vat_required,
            "gross_income_uah": round(gross, 2),
            "deductible_expenses_uah": round(expenses, 2),
            "taxable_base_uah": round(base, 2),
            "estimated_annual_tax_uah": round(total, 2),
            "breakdown": {
                "pit_uah": round(pit, 2),
                "military_tax_uah": round(military, 2),
                "esv_uah": round(esv, 2),
                "vat_estimate_uah": round(vat_component, 2),
            },
            "vat_threshold_uah": vat_threshold or DEFAULT_VAT_REGISTRATION_THRESHOLD,
            "note": (
                "Загальна система з обов’язковою реєстрацією ПДВ (оборот > 1 млн грн): "
                "додано орієнтовний компонент ПДВ 20% від валового доходу."
                if vat_required
                else "Загальна система без обов’язкового ПДВ за порогом обороту."
            ),
        }
