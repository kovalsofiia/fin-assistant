from typing import List, Optional, Dict
from datetime import date
from models.common import FopGroup, TaxSystem, ActivityType, ReportingPeriod
from models.setting import FopSettingsBase

from core.database import supabase
from core.constants import (
    SINGLE_TAX_G1, 
    SINGLE_TAX_G2, 
    FIXED_MILITARY_TAX,
    LIMIT_G1,
    LIMIT_G2,
    LIMIT_G3,
    MIN_ESV
)

ESV_MONTHLY_2025 = MIN_ESV # Alias for clarity

class TaxService:
    @staticmethod
    def verify_group_restrictions(settings: FopSettingsBase, annual_income: float) -> List[str]:
        errors = []
        today = date.today()
        rules = TaxService.get_tax_rules(today.year, today.month)
        
        # Group 1
        if settings.fop_group == FopGroup.GROUP_1:
            limit = rules.get("limit_g1", LIMIT_G1)
            if annual_income > limit:
                errors.append(f"GROUP_1_VIOLATION: Income exceeds UAH {limit:,.0f}")
            if settings.has_employees:
                errors.append("GROUP_1_VIOLATION: Employees are prohibited")
                
        # Group 2
        elif settings.fop_group == FopGroup.GROUP_2:
            limit = rules.get("limit_g2", LIMIT_G2)
            if annual_income > limit:
                errors.append(f"GROUP_2_LIMIT_EXCEEDED: Income exceeds UAH {limit:,.0f}")
            if settings.employees_count > 10:
                errors.append("GROUP_2_LIMIT_EXCEEDED: Number of employees exceeds 10")
                
        # Group 3
        elif settings.fop_group == FopGroup.GROUP_3:
            limit = rules.get("limit_g3", LIMIT_G3)
            if annual_income > limit:
                errors.append(f"AUTO_TRANSITION_GENERAL: Income exceeds UAH {limit:,.0f}. Transition to general system required.")
                
        # Group 4
        elif settings.fop_group == FopGroup.GROUP_4:
            if settings.activity_type != ActivityType.AGRICULTURE:
                errors.append("GROUP_4_INVALID_ACTIVITY: Exclusively agricultural activity required")
            if settings.has_employees:
                errors.append("GROUP_4_VIOLATION: Employees are prohibited")
            if (settings.land_area_ha or 0) <= 0:
                errors.append("GROUP_4_INVALID_LAND: Land area must be greater than 0")

        return errors

    @staticmethod
    def get_warnings(settings: FopSettingsBase, annual_income: float) -> List[str]:
        warnings = []
        today = date.today()
        rules = TaxService.get_tax_rules(today.year, today.month)
        
        # Limit Approach Warning (90%)
        limit = 0
        if settings.fop_group == FopGroup.GROUP_1: limit = rules.get("limit_g1", LIMIT_G1)
        elif settings.fop_group == FopGroup.GROUP_2: limit = rules.get("limit_g2", LIMIT_G2)
        elif settings.fop_group == FopGroup.GROUP_3: limit = rules.get("limit_g3", LIMIT_G3)
        
        if limit > 0 and annual_income >= (limit * 0.9):
            warnings.append("LIMIT_APPROACHING")
            
        # VAT Registration Warning
        if not settings.is_vat_payer and annual_income > 1000000.0:
            warnings.append("VAT_REGISTRATION_REQUIRED")
            
        return warnings

    @staticmethod
    def get_tax_rules(year: int, month: int) -> Dict:
        """
        Отримує всі правила оподаткування для конкретного періоду.
        Ці дані використовуються і для ESV, і для лімітів, і для ставок G1/G2.
        """
        # Базові константи як фундамент
        fallback_rules = {
            "year": year,
            "month": month,
            "esv_value": 1760.00 if year < 2026 else 1902.34,
            "single_tax_g1": SINGLE_TAX_G1,
            "single_tax_g2": SINGLE_TAX_G2,
            "fixed_military_tax": FIXED_MILITARY_TAX,
            "limit_g1": LIMIT_G1,
            "limit_g2": LIMIT_G2,
            "limit_g3": LIMIT_G3
        }
        
        try:
            res = supabase.table("tax_rules")\
                .select("*")\
                .eq("year", int(year))\
                .eq("month", int(month))\
                .execute()
            
            if res.data and len(res.data) > 0:
                # Зливаємо отримані дані з дефолтами (на випадок якщо в БД NULL в окремих полях)
                db_rule = res.data[0]
                for key in fallback_rules:
                    if key in db_rule and db_rule[key] is not None:
                        fallback_rules[key] = float(db_rule[key])
                return fallback_rules
                
        except Exception as e:
            print(f"DEBUG: Error fetching tax rules from DB for {year}-{month}: {e}")
        
        return fallback_rules

    @staticmethod
    def get_esv_rate(user_id: str, settings: FopSettingsBase, year: int, month: int) -> float:
        """
        Отримує ставку ЄСВ на конкретний місяць з урахуванням оверрайдів.
        """
        try:
            # 1. User Override (Пріоритет №1)
            user_override = supabase.table("user_esv_overrides")\
                .select("value")\
                .eq("user_id", user_id)\
                .eq("year", int(year))\
                .eq("month", int(month))\
                .execute()
            
            if user_override.data:
                val = user_override.data[0].get("value")
                if val is not None:
                    return float(val)
        except Exception as e:
            print(f"DEBUG: Error in get_esv_rate override check: {e}")

        # 2. Глобальні правила (Пріоритет №2)
        rules = TaxService.get_tax_rules(year, month)
        base_esv = float(rules.get("esv_value", 1760.00))
        
        # 3. Перевірка налаштувань користувача (для майбутніх періодів)
        today = date.today()
        if (year > today.year) or (year == today.year and month >= today.month):
            if settings.esv_value and settings.esv_value > 0:
                return float(settings.esv_value)
        
        return base_esv

    @staticmethod
    def calculate_taxes(
        user_id: str,
        settings: FopSettingsBase, 
        income: float, 
        period: ReportingPeriod = ReportingPeriod.MONTH,
        calc_date: Optional[date] = None
    ) -> Dict:
        # Дата для розрахунку (за замовчуванням сьогодні)
        d = calc_date or date.today()
        
        # Визначаємо кількість місяців у періоді
        months_to_calc = 1
        if period == ReportingPeriod.QUARTER: months_to_calc = 3
        elif period == ReportingPeriod.YEAR: months_to_calc = 12
        
        total_single_tax = 0.0
        total_military_tax = 0.0
        total_esv = 0.0
        vat = None
        
        # Розраховуємо податки для кожного місяця окремо, враховуючи можливі зміни ставок
        for i in range(months_to_calc):
            # Рахуємо рік та місяць для кожної ітерації
            curr_m = d.month + i
            curr_y = d.year + (curr_m - 1) // 12
            curr_m = (curr_m - 1) % 12 + 1
            
            # Отримуємо правила для конкретного місяця
            rules = TaxService.get_tax_rules(curr_y, curr_m)
            
            # 1. ЄСВ
            total_esv += TaxService.get_esv_rate(user_id, settings, curr_y, curr_m)
            
            # 2. Єдиний податок та Військовий збір
            if settings.fop_group == FopGroup.GROUP_1:
                total_single_tax += rules.get("single_tax_g1", SINGLE_TAX_G1)
                total_military_tax += rules.get("fixed_military_tax", FIXED_MILITARY_TAX)
                
            elif settings.fop_group == FopGroup.GROUP_2:
                total_single_tax += rules.get("single_tax_g2", SINGLE_TAX_G2)
                total_military_tax += rules.get("fixed_military_tax", FIXED_MILITARY_TAX)
                
            elif settings.fop_group == FopGroup.GROUP_3:
                # Для 3-ї групи податки залежать від доходу за весь період
                # Ми ділимо дохід порівну між місяцями для спрощення розрахунку за місяць
                monthly_income = income / months_to_calc
                
                # Single Tax: use percent from settings or fallback to 3%/5%
                rate = (settings.income_tax_percent / 100.0) if settings.income_tax_percent is not None else (0.03 if settings.is_vat_payer else 0.05)
                total_single_tax += monthly_income * rate
                
                # Military tax: use percent from settings or fallback to 1% for G3
                mil_rate = (settings.military_tax_percent / 100.0) if settings.military_tax_percent is not None else 0.01
                total_military_tax += monthly_income * mil_rate
                
            elif settings.fop_group == FopGroup.GROUP_4:
                # Single tax — normative monetary valuation of land × land area × rate
                land_value = settings.normative_land_value or 0.0
                area = settings.land_area_ha or 0.0
                rate = (settings.income_tax_percent / 100.0) if settings.income_tax_percent is not None else 0.0095
                # Частка річного податку на 1 місяць
                total_single_tax += (land_value * area * rate) / 12
                total_military_tax += rules.get("fixed_military_tax", FIXED_MILITARY_TAX)

        return {
            "single_tax": round(total_single_tax, 2),
            "esv": round(total_esv, 2),
            "military_tax": round(total_military_tax, 2),
            "vat": vat,
            # Оціночні значення для інформативності
            "total_monthly_tax": round((total_single_tax + total_esv + total_military_tax) / months_to_calc, 2),
            "total_period_tax": round(total_single_tax + total_esv + total_military_tax, 2)
        }

    @staticmethod
    def get_payment_calendar() -> List[Dict]:
        """
        Генерує календар платежів на 2025 рік.
        Дедлайни: до 20-го числа наступного періоду.
        """
        return [
            {"event": "ЄСВ (Єдиний соціальний внесок)", "deadline": "Щомісяця, до 20-го числа", "group": "Усі (1, 2, 3, 4)"},
            {"event": "Єдиний податок", "deadline": "Щомісяця, до 20-го числа", "group": "1, 2"},
            {"event": "Єдиний податок", "deadline": "Щокварталу, до 20-го числа", "group": "3"},
            {"event": "Єдиний податок (нарахована частка)", "deadline": "Раз на рік", "group": "4"},
            {"event": "Військовий збір (фіксований)", "deadline": "Щомісяця, до 20-го числа", "group": "1, 2, 4"},
            {"event": "Військовий збір (1% від доходу)", "deadline": "Щокварталу, до 20-го числа", "group": "3"},
        ]
