"""
Движок підбору групи ФОП (фази A/B).

Критичні правила:
- is_b2b_or_foreign → блокує 1 та 2 групи.
- employees_count > 0 → блокує 1 групу; > 10 → блокує 2 групу.
- projectedAnnualIncomeUah > L_x → блокує групу x (1, 2, 3).
- 3 група: ПДВ лише за добровільним прапорцем (expectsVatRegistration), не від 1 млн.
- 1 млн грн (vatThreshold) → обов'язкове ПДВ лише на загальній системі.
- Дохід > L₃ (абсолютний ліміт спрощеної) → 15% з перевищення, втрата спрощеної,
  перехід на загальну з наступного кварталу → там обов'язкове ПДВ (> 1 млн).
"""

# Ставка ЄП з суми перевищення абсолютного ліміту спрощеної (орієнтир ПКУ)
SIMPLIFIED_EXCESS_RATE = 0.15

from typing import Any, Dict, List, Optional, Tuple

from services.quiz_context import emergency_quiz_rules_from_constants

GROUP_FOCUS_HINTS = {
    1: "Базовий рівень: без найму, невеликий дохід, ринок або побутові послуги.",
    2: "Найпоширеніший варіант: послуги, торгівля, виробництво, до 10 працівників.",
    3: "Універсальний: ЗЕД, валюта, юрособи, плановий ПДВ, понад 10 працівників.",
    4: "Окремий режим для сільгоспу за наявності земельних угідь.",
}

B2B_FOREIGN_BLOCK_REASON = (
    "B2B / іноземні замовники (is_b2b_or_foreign): 1–2 групи недопустимі — "
    "типовий вибір 3 група (IT, QA, ЗЕД, валютні надходження)."
)


def _annual_income(answers: Dict[str, Any]) -> float:
    return max(0.0, float(answers.get("projectedAnnualIncomeUah") or 0))


def _employees_count(answers: Dict[str, Any]) -> int:
    if answers.get("employeesCount") is not None:
        return max(0, int(answers["employeesCount"]))
    band = answers.get("employeesBand")
    if band == "0":
        return 0
    if band == "1-10":
        return 1
    if band == "11+":
        return 11
    return 0


def is_b2b_or_foreign(answers: Dict[str, Any]) -> bool:
    """Робота з юрособами на загальній системі або іноземними замовниками."""
    if answers.get("isB2bOrForeign") is not None:
        return bool(answers["isB2bOrForeign"])
    return bool(answers.get("is_b2b_or_foreign"))


def _plans_vat_payer(answers: Dict[str, Any]) -> bool:
    """Добровільний платник ПДВ на 3 групі (налаштування is_vat_payer)."""
    return bool(answers.get("expectsVatRegistration"))


def g3_effective_vat_payer(answers: Dict[str, Any]) -> bool:
    """3 група: ставка 3% ЄП лише якщо користувач сам увімкнув ПДВ. Дохід не форсує ПДВ."""
    return _plans_vat_payer(answers)


def exceeds_simplified_absolute_limit(
    answers: Dict[str, Any], ctx: Dict[str, Any]
) -> bool:
    """Перевищення глобального ліміту спрощеної (напр. 1167 МЗП / L₃)."""
    return _annual_income(answers) > ctx["limits"]["g3"]


def requires_general_system_transition(
    answers: Dict[str, Any], ctx: Dict[str, Any]
) -> bool:
    return exceeds_simplified_absolute_limit(answers, ctx)


def vat_mandatory_on_general_system(
    answers: Dict[str, Any], ctx: Dict[str, Any]
) -> bool:
    """Поріг 1 млн — лише для загальної системи (не для 3 групи спрощеної)."""
    return _annual_income(answers) > ctx["vatThreshold"]


def simplified_excess_tax_uah(answers: Dict[str, Any], ctx: Dict[str, Any]) -> float:
    income = _annual_income(answers)
    limit = ctx["limits"]["g3"]
    if income <= limit:
        return 0.0
    return round((income - limit) * SIMPLIFIED_EXCESS_RATE, 2)


def must_use_group3(answers: Dict[str, Any], ctx: Dict[str, Any]) -> bool:
    if is_b2b_or_foreign(answers):
        return True
    if _employees_count(answers) > 10:
        return True
    if _plans_vat_payer(answers):
        return True
    return False


def _has_land_for_group4(answers: Dict[str, Any]) -> bool:
    ha = float(answers.get("landAreaHa") or 0)
    norm = float(answers.get("normativeLandValuePerHa") or 0)
    return ha > 0 and norm > 0


def _income_exceeds_limit(income: float, limit: float, group: int, ctx: Dict[str, Any]) -> Tuple[bool, str]:
    if income > limit:
        units = ctx["limitMzpUnits"][f"g{group}"]
        return (
            True,
            f"{group} група: дохід перевищує ліміт {units} МЗП ({limit:,.0f} грн).",
        )
    return False, ""


def _eligible_group1(answers: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    income = _annual_income(answers)
    employees = _employees_count(answers)

    if employees > 0:
        return False, f"1 група: заборонено найману працю (зараз {employees} працівник(ів))."
    if is_b2b_or_foreign(answers):
        return False, B2B_FOREIGN_BLOCK_REASON
    if not answers.get("g1ActivityAllowed", True):
        return (
            False,
            "1 група: підходить для роздрібу з торговельних місць на ринках або побутових послуг населенню.",
        )
    exceeded, reason = _income_exceeds_limit(income, ctx["limits"]["g1"], 1, ctx)
    if exceeded:
        return False, reason
    if answers.get("activity") == "agriculture":
        return False, "1 група: сільгосп — орієнтир 4 група (за землею) або 3 група."
    return True, None


def _eligible_group2(answers: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    income = _annual_income(answers)
    employees = _employees_count(answers)

    if employees > 10:
        return False, f"2 група: не більше 10 найманих (зараз {employees})."
    if is_b2b_or_foreign(answers):
        return False, B2B_FOREIGN_BLOCK_REASON
    exceeded, reason = _income_exceeds_limit(income, ctx["limits"]["g2"], 2, ctx)
    if exceeded:
        return False, reason
    if answers.get("activity") == "agriculture":
        return False, "2 група: для сільгоспу — 4 група (за землею) або 3 група."
    return True, None


def _eligible_group3(answers: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    income = _annual_income(answers)
    exceeded, reason = _income_exceeds_limit(income, ctx["limits"]["g3"], 3, ctx)
    if exceeded:
        return (
            False,
            reason
            + " Перевищення абсолютного ліміту спрощеної: 15% з надлишку, "
            "з наступного кварталу — загальна система з обов’язковим ПДВ.",
        )
    if (
        answers.get("activity") == "agriculture"
        and _has_land_for_group4(answers)
        and _employees_count(answers) == 0
    ):
        return False, "3 група: за сільгоспом із земельними угіддями без найму типовий вибір — 4 група."
    return True, None


def _eligible_group4(answers: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    if answers.get("activity") != "agriculture":
        return False, "4 група: лише сільськогосподарська діяльність із відповідними земельними ділянками."
    if _employees_count(answers) != 0:
        return False, "4 група: у типовій моделі спрощеної 4 групи наймані працівники не передбачені (уточніть з ПКУ)."
    if not _has_land_for_group4(answers):
        return False, "4 група: вкажіть площу угідь (га) та нормативну грошову оцінку землі (грн/га)."
    return True, None


def _check_eligibility(group: int, answers: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    if group == 1:
        return _eligible_group1(answers, ctx)
    if group == 2:
        return _eligible_group2(answers, ctx)
    if group == 3:
        return _eligible_group3(answers, ctx)
    return _eligible_group4(answers)


def build_criteria_summary(answers: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    income = _annual_income(answers)
    employees = _employees_count(answers)
    b2b = is_b2b_or_foreign(answers)
    return {
        "projected_annual_income_uah": round(income, 2),
        "limits_uah": {
            "g1": ctx["limits"]["g1"],
            "g2": ctx["limits"]["g2"],
            "g3": ctx["limits"]["g3"],
        },
        "income_within_limits": {
            "g1": income <= ctx["limits"]["g1"],
            "g2": income <= ctx["limits"]["g2"],
            "g3": income <= ctx["limits"]["g3"],
        },
        "employees_count": employees,
        "employees_blocks_g1": employees > 0,
        "employees_blocks_g2": employees > 10,
        "is_b2b_or_foreign": b2b,
        "blocks_groups_1_and_2": b2b,
        "must_use_group3": must_use_group3(answers, ctx),
        "exceeds_simplified_absolute_limit": exceeds_simplified_absolute_limit(
            answers, ctx
        ),
        "requires_general_transition": requires_general_system_transition(
            answers, ctx
        ),
        "g3_vat_voluntary": g3_effective_vat_payer(answers),
        "vat_mandatory_if_general": vat_mandatory_on_general_system(answers, ctx),
    }


def estimate_annual_tax_load(group: int, answers: Dict[str, Any], ctx: Dict[str, Any]) -> float:
    d = _annual_income(answers)
    inc_pct = ctx["g3"]["epVat"] if g3_effective_vat_payer(answers) else ctx["g3"]["epNonVat"]
    mil_pct = ctx["g3"]["militaryPct"]

    if group == 1:
        fixed = ctx["monthlyFixed"]["g1"]
        return (fixed["single"] + fixed["military"]) * 12 + _annual_esv(ctx, answers)
    if group == 2:
        fixed = ctx["monthlyFixed"]["g2"]
        return (fixed["single"] + fixed["military"]) * 12 + _annual_esv(ctx, answers)
    if group == 3:
        ep_mil = d * ((inc_pct + mil_pct) / 100.0)
        return ep_mil + _annual_esv(ctx, answers)
    if group == 4:
        ha = max(0.0, float(answers.get("landAreaHa") or 0))
        norm = max(0.0, float(answers.get("normativeLandValuePerHa") or 0))
        lt = answers.get("g4LandType") or "arable_pasture"
        rate = ctx["g4Rates"].get(lt, ctx["g4Rates"]["arable_pasture"])
        land_tax = ha * norm * (rate / 100.0)
        return land_tax + ctx["militaryFixedMonthly"] * 12 + _annual_esv(ctx, answers)
    return float("inf")


def _annual_esv(ctx: Dict[str, Any], answers: Dict[str, Any]) -> float:
    if answers.get("esvCoveredElsewhere"):
        return 0.0
    return ctx["esvMonthly"] * 12


def _pick_lowest_tax_candidate(
    groups: List[Dict[str, Any]], candidate_groups: Optional[List[int]] = None
) -> Optional[Dict[str, Any]]:
    candidates = candidate_groups or [1, 2, 3]
    feasible = [
        g
        for g in groups
        if g["group"] in candidates
        and g["eligible"]
        and g.get("estimatedAnnualTaxUah") is not None
    ]
    if not feasible:
        return None
    min_tax = min(g["estimatedAnnualTaxUah"] for g in feasible)
    tied = [g for g in feasible if g["estimatedAnnualTaxUah"] == min_tax]
    return min(tied, key=lambda g: g["group"])


def _pick_recommended_group(
    answers: Dict[str, Any], groups: List[Dict[str, Any]], ctx: Dict[str, Any]
) -> Tuple[Optional[int], str]:
    def is_eligible(n: int) -> bool:
        row = next((g for g in groups if g["group"] == n), None)
        return bool(row and row["eligible"])

    if answers.get("activity") == "agriculture" and is_eligible(4):
        return 4, "agriculture"

    if must_use_group3(answers, ctx):
        if is_eligible(3):
            return 3, "requires_group3"
        return None, "none"

    lowest = _pick_lowest_tax_candidate(groups)
    if lowest:
        return lowest["group"], "lowest_tax"
    return None, "none"


def _build_focus_summary(
    recommended_group: Optional[int], groups: List[Dict[str, Any]], mode: str
) -> Dict[str, Any]:
    eligible_rows = [g for g in groups if g["eligible"]]

    if not recommended_group:
        headline = "Жодна група не відповідає умовам — перевірте дохід, найм і B2B/іноземних замовників."
    elif mode == "agriculture":
        headline = f"Рекомендована {recommended_group} група — типовий режим для сільгоспу з землею."
    elif mode == "requires_group3":
        headline = (
            f"Рекомендована {recommended_group} група: B2B/іноземні клієнти, "
            f"найм понад 10 або ПДВ — 1–2 групи недоступні."
        )
    else:
        headline = (
            f"Рекомендована {recommended_group} група — найменше оціночне податкове навантаження "
            f"серед допустимих."
        )

    groups_to_consider = []
    for n in (1, 2, 3, 4):
        row = next((g for g in groups if g["group"] == n), None)
        if not row or not row["eligible"]:
            continue
        groups_to_consider.append(
            {
                "group": n,
                "hint": GROUP_FOCUS_HINTS[n],
                "isPrimary": n == recommended_group,
            }
        )

    return {
        "primaryGroup": recommended_group,
        "headline": headline,
        "groupsToConsider": groups_to_consider,
        "alsoConsider": [g["group"] for g in groups_to_consider if not g["isPrimary"]],
        "eligibleCount": len(eligible_rows),
    }


def _format_tax_uah(n: float) -> str:
    return f"{round(n):,}".replace(",", " ") + " грн"


def _build_recommendation_reasons(
    answers: Dict[str, Any],
    groups: List[Dict[str, Any]],
    ctx: Dict[str, Any],
    recommended_group: Optional[int],
    mode: str,
) -> List[str]:
    reasons: List[str] = []
    employees = _employees_count(answers)
    income = _annual_income(answers)

    if is_b2b_or_foreign(answers):
        reasons.append(B2B_FOREIGN_BLOCK_REASON)

    if employees > 0:
        reasons.append(f"Наймані працівники: {employees} — 1 група недоступна.")
    if employees > 10:
        reasons.append(f"Наймані працівники: {employees} — 2 група недоступна.")

    for g in (1, 2, 3):
        if income > ctx["limits"][f"g{g}"]:
            reasons.append(
                f"Дохід {income:,.0f} грн > ліміт {g} групи ({ctx['limits'][f'g{g}']:,.0f} грн)."
            )

    if answers.get("activity") == "agriculture":
        g4 = next((g for g in groups if g["group"] == 4), None)
        if g4 and g4["eligible"]:
            reasons.append("Сільгосп із землею — пріоритет 4 групи.")
        else:
            reasons.append("Сільгосп без даних землі — орієнтир 3 група.")

    if requires_general_system_transition(answers, ctx):
        excess = simplified_excess_tax_uah(answers, ctx)
        reasons.append(
            f"Дохід перевищив абсолютний ліміт спрощеної ({ctx['limits']['g3']:,.0f} грн): "
            f"орієнтовно {excess:,.0f} грн за ставкою 15% з перевищення; "
            "з наступного кварталу — загальна система, далі обов’язкове ПДВ (оборот > 1 млн грн)."
        )
    elif _plans_vat_payer(answers):
        reasons.append(
            "Платник ПДВ на 3 групі (добровільно): ЄП 3% + облік ПДВ; дохід не змушує реєструватися."
        )

    if mode == "lowest_tax" and recommended_group is not None:
        compared = sorted(
            [
                g
                for g in groups
                if g["group"] in (1, 2, 3)
                and g["eligible"]
                and g.get("estimatedAnnualTaxUah") is not None
            ],
            key=lambda g: g["group"],
        )
        if len(compared) > 1:
            summary = "; ".join(
                f"{g['group']} — {_format_tax_uah(g['estimatedAnnualTaxUah'])}" for g in compared
            )
            reasons.append(f"Порівняння навантаження: {summary}. Обрано {recommended_group} групу.")
        reasons.append("Без податків на ФОП найму (ПДФО, ЄСВ роботодавця).")

    return reasons


def evaluate_fop_group_recommendation(
    answers: Dict[str, Any], quiz_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    ctx = quiz_context or emergency_quiz_rules_from_constants()
    criteria = build_criteria_summary(answers, ctx)

    groups: List[Dict[str, Any]] = []
    for g in (1, 2, 3, 4):
        ok, reason = _check_eligibility(g, answers, ctx)
        tax = estimate_annual_tax_load(g, answers, ctx) if ok else None
        groups.append(
            {
                "group": g,
                "eligible": ok,
                "disqualifyReason": reason,
                "estimatedAnnualTaxUah": round(tax, 2) if tax is not None else None,
            }
        )

    recommended_group, mode = _pick_recommended_group(answers, groups, ctx)
    recommended = next((g for g in groups if g["group"] == recommended_group), None)

    fx_pct = float(answers.get("fxIncomeSharePercent") or 0)
    fx_note = (
        f"Валютний дохід за курсом НБУ; поріг ПДВ — {ctx['vatThreshold']:,.0f} грн."
        if fx_pct > 0
        else None
    )

    return _package_evaluation(
        answers, ctx, groups, recommended_group, mode, criteria, fx_note
    )


def _package_evaluation(
    answers: Dict[str, Any],
    ctx: Dict[str, Any],
    groups: List[Dict[str, Any]],
    recommended_group: Optional[int],
    mode: str,
    criteria: Dict[str, Any],
    fx_note: Optional[str],
) -> Dict[str, Any]:
    recommended = next((g for g in groups if g["group"] == recommended_group), None)
    return {
        "groups": groups,
        "recommendedGroup": recommended_group,
        "recommendedTaxUah": recommended["estimatedAnnualTaxUah"] if recommended else None,
        "recommendationMode": mode,
        "recommendationReasons": _build_recommendation_reasons(
            answers, groups, ctx, recommended_group, mode
        ),
        "focusSummary": _build_focus_summary(recommended_group, groups, mode),
        "criteria": criteria,
        "fxNote": fx_note,
        "mustUseGroup3": must_use_group3(answers, ctx),
        "simplifiedLimitTransitionWarning": requires_general_system_transition(
            answers, ctx
        ),
        # 1 млн → ПДВ лише після переходу на загальну (доход уже > L₃ > 1 млн)
        "vatRegistrationWarning": requires_general_system_transition(answers, ctx),
        "simplifiedTransition": {
            "exceeded_absolute_limit": requires_general_system_transition(
                answers, ctx
            ),
            "limit_uah": ctx["limits"]["g3"],
            "excess_income_uah": round(
                max(0.0, _annual_income(answers) - ctx["limits"]["g3"]), 2
            ),
            "excess_tax_15pct_uah": simplified_excess_tax_uah(answers, ctx),
            "general_vat_mandatory_after_transition": vat_mandatory_on_general_system(
                answers, ctx
            ),
        },
    }


def finalize_evaluation_after_kved(
    evaluation: Dict[str, Any],
    answers: Dict[str, Any],
    ctx: Dict[str, Any],
    kved_validation: Dict[str, Any],
) -> Dict[str, Any]:
    """Застосовує блокування КВЕД і перераховує рекомендацію."""
    from services.kved_validation_service import KvedValidationService

    groups = KvedValidationService.apply_kved_blocks_to_groups(
        evaluation.get("groups") or [], kved_validation
    )
    criteria = evaluation.get("criteria") or build_criteria_summary(answers, ctx)
    fx_note = evaluation.get("fxNote")

    if kved_validation.get("blocks_simplified_system"):
        mode = "general_only_kved"
        recommended_group = None
        focus = {
            "primaryGroup": None,
            "headline": (
                "За обраними КВЕД спрощена система (групи 1–4) недоступна — "
                "орієнтир лише загальна система оподаткування."
            ),
            "groupsToConsider": [],
            "alsoConsider": [],
            "eligibleCount": 0,
        }
        reasons = list(evaluation.get("recommendationReasons") or [])
        reasons.insert(0, kved_validation.get("simplified_block_reason") or "")
        packaged = _package_evaluation(
            answers, ctx, groups, recommended_group, mode, criteria, fx_note
        )
        packaged["focusSummary"] = focus
        packaged["recommendationReasons"] = reasons
        packaged["kvedBlocksSimplified"] = True
        return packaged

    recommended_group, mode = _pick_recommended_group(answers, groups, ctx)
    packaged = _package_evaluation(
        answers, ctx, groups, recommended_group, mode, criteria, fx_note
    )
    packaged["kvedBlocksSimplified"] = False
    if kved_validation.get("blocked_groups"):
        reasons = list(packaged.get("recommendationReasons") or [])
        for scope, key in (
            ("спрощена", "simplified_violations"),
            ("1 група", "group_1_violations"),
            ("2 група", "group_2_violations"),
        ):
            hits = kved_validation.get(key) or []
            if hits:
                codes = ", ".join(h["user_code"] for h in hits[:3])
                reasons.append(f"КВЕД обмежує {scope}: {codes}")
        packaged["recommendationReasons"] = reasons
    return packaged


# Зворотна сумісність
evaluate_fop_group_quiz = evaluate_fop_group_recommendation
