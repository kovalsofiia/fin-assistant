"""Збір snapshot + профіль ФОП + КВЕД → рекомендація групи / загальна система."""

from datetime import date
from typing import Any, Dict, List, Optional

from core.database import supabase
from models.common import ActivityType
from models.setting import FopSettingsBase
from services.financial_snapshot_service import FinancialSnapshotService
from services.fop_group_engine import (
    evaluate_fop_group_recommendation,
    finalize_evaluation_after_kved,
    is_b2b_or_foreign,
)
from services.general_tax_service import GeneralTaxService
from services.kved_validation_service import KvedValidationService
from services.quiz_context import map_api_tax_rules_to_quiz_context
from services.tax_service import TaxService


class FopRecommendationService:
    @staticmethod
    def resolve_is_b2b_or_foreign(
        settings: Optional[FopSettingsBase],
        snapshot: Dict[str, Any],
        manual: Dict[str, Any],
    ) -> bool:
        if manual.get("is_b2b_or_foreign") is not None:
            return bool(manual["is_b2b_or_foreign"])

        from_settings = bool(settings.is_zed) if settings else False
        from_fx = float(snapshot.get("fx_income_share_percent") or 0) > 0
        return from_settings or from_fx

    @staticmethod
    def _employees_count(settings: Optional[FopSettingsBase]) -> int:
        if not settings:
            return 0
        count = int(settings.employees_count or 0)
        if settings.has_employees and count == 0:
            return 1
        return max(0, count)

    @staticmethod
    def _activity_from_settings(settings: Optional[FopSettingsBase]) -> str:
        if not settings or not settings.activity_type:
            return "services"
        val = settings.activity_type
        if isinstance(val, ActivityType):
            return val.value
        return str(val)

    @staticmethod
    def build_answers_from_data(
        snapshot: Dict[str, Any],
        settings: Optional[FopSettingsBase],
        manual: Dict[str, Any],
    ) -> Dict[str, Any]:
        employees_count = FopRecommendationService._employees_count(settings)
        land_ha = float(settings.land_area_ha or 0) if settings else 0.0
        norm_per_ha = float(settings.normative_land_value or 0) if settings else 0.0
        b2b_foreign = FopRecommendationService.resolve_is_b2b_or_foreign(
            settings, snapshot, manual
        )

        return {
            "projectedAnnualIncomeUah": snapshot["projected_annual_income_uah"],
            "employeesCount": employees_count,
            "employeesBand": (
                "0"
                if employees_count == 0
                else ("11+" if employees_count > 10 else "1-10")
            ),
            "activity": FopRecommendationService._activity_from_settings(settings),
            "landAreaHa": land_ha,
            "normativeLandValuePerHa": norm_per_ha,
            "g4LandType": manual.get("g4_land_type") or "arable_pasture",
            "isB2bOrForeign": b2b_foreign,
            "is_b2b_or_foreign": b2b_foreign,
            "expectsVatRegistration": bool(settings.is_vat_payer) if settings else False,
            "g1ActivityAllowed": True,
            "esvCoveredElsewhere": bool(settings.esv_covered_by_primary_employment)
            if settings
            else False,
            "fxIncomeSharePercent": snapshot["fx_income_share_percent"],
        }

    @staticmethod
    def _inferred_signals(
        answers: Dict[str, Any],
        settings: Optional[FopSettingsBase],
        snapshot: Dict[str, Any],
        kved_validation: Dict[str, Any],
    ) -> list:
        signals = []
        if is_b2b_or_foreign(answers):
            parts = []
            if settings and settings.is_zed:
                parts.append("ЗЕД у профілі")
            if float(snapshot.get("fx_income_share_percent") or 0) > 0:
                parts.append(f"валютний дохід {snapshot['fx_income_share_percent']}%")
            if not parts:
                parts.append("позначено вручну")
            signals.append(
                {"code": "is_b2b_or_foreign", "label": "B2B / іноземні: " + ", ".join(parts)}
            )
        ec = int(answers.get("employeesCount") or 0)
        if ec > 0:
            signals.append({"code": "employees", "label": f"Наймані: {ec}"})
        if answers.get("expectsVatRegistration"):
            signals.append({"code": "vat", "label": "Платник ПДВ"})
        if kved_validation.get("blocks_simplified_system"):
            signals.append(
                {
                    "code": "kved_simplified_blocked",
                    "label": "КВЕД забороняє спрощену систему",
                }
            )
        elif not kved_validation.get("has_kveds"):
            signals.append(
                {
                    "code": "kved_missing",
                    "label": "КВЕД не вказані — додайте в налаштуваннях",
                }
            )
        return signals

    @staticmethod
    def _pick_overall_recommendation(
        evaluation: Dict[str, Any],
        general: Dict[str, Any],
        kved_validation: Dict[str, Any],
    ) -> Dict[str, Any]:
        simplified_group = evaluation.get("recommendedGroup")
        simplified_tax = evaluation.get("recommendedTaxUah")
        general_tax = general.get("estimated_annual_tax_uah")

        if kved_validation.get("blocks_simplified_system"):
            return {
                "recommended_tax_system": "general",
                "recommended_fop_group": None,
                "recommended_annual_tax_uah": general_tax,
                "reason": "kved_blocks_simplified",
            }

        if simplified_group is None and general_tax is not None:
            criteria = evaluation.get("criteria") or {}
            reason = (
                "simplified_absolute_limit_exceeded"
                if criteria.get("requires_general_transition")
                else "no_simplified_group_eligible"
            )
            return {
                "recommended_tax_system": "general",
                "recommended_fop_group": None,
                "recommended_annual_tax_uah": general_tax,
                "reason": reason,
            }

        if (
            simplified_tax is not None
            and general_tax is not None
            and general_tax < simplified_tax
        ):
            return {
                "recommended_tax_system": "general",
                "recommended_fop_group": None,
                "recommended_annual_tax_uah": general_tax,
                "reason": "general_lower_tax",
            }

        return {
            "recommended_tax_system": "simplified",
            "recommended_fop_group": simplified_group,
            "recommended_annual_tax_uah": simplified_tax,
            "reason": "simplified_best",
        }

    @staticmethod
    def recommend(
        user_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        manual: Optional[Dict[str, Any]] = None,
        user_kveds: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        manual = manual or {}
        if not start_date or not end_date:
            start_date, end_date = FinancialSnapshotService.default_period()

        snapshot = FinancialSnapshotService.build_snapshot(user_id, start_date, end_date)

        settings_res = (
            supabase.table("fop_settings").select("*").eq("user_id", user_id).execute()
        )
        settings = (
            FopSettingsBase(**settings_res.data[0]) if settings_res.data else None
        )

        codes = user_kveds if user_kveds is not None else KvedValidationService.load_user_kved_codes(
            user_id
        )
        kved_validation = KvedValidationService.validate_user_kveds(codes)

        answers = FopRecommendationService.build_answers_from_data(
            snapshot, settings, manual
        )

        ref = end_date
        rules = TaxService.get_tax_rules(ref.year, ref.month)
        ctx = map_api_tax_rules_to_quiz_context(rules)

        raw_evaluation = evaluate_fop_group_recommendation(answers, ctx)
        evaluation = finalize_evaluation_after_kved(
            raw_evaluation, answers, ctx, kved_validation
        )

        esv_annual = 0.0
        if not answers.get("esvCoveredElsewhere"):
            esv_annual = float(ctx.get("esvMonthly", 0)) * 12

        projected_income = float(snapshot["projected_annual_income_uah"])
        force_general_vat = projected_income > float(ctx.get("limits", {}).get("g3", 0))
        general_estimate = GeneralTaxService.estimate_annual_tax(
            gross_income_uah=projected_income,
            deductible_expenses_uah=snapshot.get("expense_fop_uah", 0),
            esv_annual_uah=esv_annual,
            force_vat=force_general_vat if force_general_vat else None,
            vat_threshold=float(ctx.get("vatThreshold", 1_000_000)),
        )

        overall = FopRecommendationService._pick_overall_recommendation(
            evaluation, general_estimate, kved_validation
        )

        current_group = int(settings.fop_group) if settings and settings.fop_group else None
        savings = None
        if (
            overall.get("recommended_tax_system") == "simplified"
            and current_group
            and evaluation.get("groups")
        ):
            cur_row = next(
                (g for g in evaluation["groups"] if g["group"] == current_group), None
            )
            rec_tax = evaluation.get("recommendedTaxUah")
            cur_tax = cur_row.get("estimatedAnnualTaxUah") if cur_row else None
            if cur_tax is not None and rec_tax is not None:
                savings = round(cur_tax - rec_tax, 2)

        return {
            "snapshot": snapshot,
            "answers_used": answers,
            "kved_validation": kved_validation,
            "inferred_flags": {
                "signals": FopRecommendationService._inferred_signals(
                    answers, settings, snapshot, kved_validation
                ),
                "must_use_group3": evaluation.get("mustUseGroup3"),
            },
            "evaluation": evaluation,
            "general_system": general_estimate,
            "overall_recommendation": overall,
            "current_fop_group": current_group,
            "comparison": {
                "recommended_group": overall.get("recommended_fop_group"),
                "recommended_tax_system": overall.get("recommended_tax_system"),
                "potential_annual_savings_uah": savings,
                "matches_current_group": (
                    current_group == overall.get("recommended_fop_group")
                    if overall.get("recommended_tax_system") == "simplified"
                    else None
                ),
            },
            "disclaimer": (
                "Орієнтовний розрахунок за операціями, КВЕД і налаштуваннями. "
                "3 група: ПДВ добровільно (5% або 3%+ПДВ). Поріг 1 млн — обов’язкове ПДВ на загальній. "
                "Перевищення ліміту спрощеної — перехід на загальну. Узгодьте з бухгалтером."
            ),
            "simplified_transition": evaluation.get("simplifiedTransition"),
        }
