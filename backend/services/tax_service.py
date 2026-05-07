from typing import List, Optional, Dict
from datetime import date
from models.common import FopGroup, TaxSystem, ActivityType, ReportingPeriod
from models.setting import FopSettingsBase

from core.database import supabase
from core.constants import (
    SINGLE_TAX_G1, 
    SINGLE_TAX_G2, 
    FIXED_MILITARY_TAX,
    MIN_ESV,
    MIN_ESV_2025,
    MIN_ESV_2026,
    LIMIT_G1,
    LIMIT_G2,
    LIMIT_G3,
    DEFAULT_G3_RATE,
    DEFAULT_G3_VAT_RATE,
    DEFAULT_G4_RATE,
    DEFAULT_MILITARY_RATE
)

ESV_MONTHLY_2025 = MIN_ESV # Alias for clarity

class TaxService:
    _rules_cache: Dict[str, Dict] = {}

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
        Результати кешуються в пам'яті для прискорення масових розрахунків.
        """
        cache_key = f"{year}-{month}"
        if cache_key in TaxService._rules_cache:
            return TaxService._rules_cache[cache_key]

        # Базові константи як фундамент
        fallback_rules = {
            "year": year,
            "month": month,
            "esv_value": MIN_ESV_2025 if year < 2026 else MIN_ESV_2026,
            "single_tax_g1": SINGLE_TAX_G1,
            "single_tax_g2": SINGLE_TAX_G2,
            "fixed_military_tax": FIXED_MILITARY_TAX,
            "limit_g1": LIMIT_G1,
            "limit_g2": LIMIT_G2,
            "limit_g3": LIMIT_G3,
            "income_tax_percent": None, # Will be determined by group-specific defaults
            "military_tax_percent": DEFAULT_MILITARY_RATE
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
                
                TaxService._rules_cache[cache_key] = fallback_rules
                return fallback_rules
                
        except Exception as e:
            print(f"DEBUG: Error fetching tax rules from DB for {year}-{month}: {e}")
        
        # Ми також кешуємо дефолтні значення, щоб не смикати БД повторно при невдачі
        TaxService._rules_cache[cache_key] = fallback_rules
        return fallback_rules

    @staticmethod
    def get_tax_rates(user_id: str, settings: FopSettingsBase, year: int, month: int) -> Dict[str, float]:
        """
        Отримує відсоткові ставки податків (Єдиний та Військовий) з урахуванням оверрайдів.
        """
        # Дефолтні значення на основі групи та ПДВ
        default_income_rate = DEFAULT_G3_RATE
        if settings.fop_group == FopGroup.GROUP_3:
            default_income_rate = DEFAULT_G3_VAT_RATE if settings.is_vat_payer else DEFAULT_G3_RATE
        elif settings.fop_group == FopGroup.GROUP_4:
            default_income_rate = DEFAULT_G4_RATE
            
        default_military_rate = DEFAULT_MILITARY_RATE

        rates = {
            "income_tax_percent": default_income_rate,
            "military_tax_percent": default_military_rate,
            "fixed_military_tax": FIXED_MILITARY_TAX
        }

        try:
            # 1. Глобальні правила (Пріорітет №2 - якщо система змінить дефолти для всіх)
            rules = TaxService.get_tax_rules(year, month)
            if rules.get("income_tax_percent") is not None:
                rates["income_tax_percent"] = rules["income_tax_percent"]
            if rules.get("military_tax_percent") is not None:
                rates["military_tax_percent"] = rules["military_tax_percent"]
            if rules.get("fixed_military_tax") is not None:
                rates["fixed_military_tax"] = rules["fixed_military_tax"]

            # 2. User Overrides (Пріорітет №1)
            user_override = supabase.table("user_tax_overrides")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("year", int(year))\
                .eq("month", int(month))\
                .execute()
            
            if user_override.data:
                ov = user_override.data[0]
                if ov.get("income_tax_percent") is not None:
                    rates["income_tax_percent"] = float(ov["income_tax_percent"])
                if ov.get("military_tax_percent") is not None:
                    rates["military_tax_percent"] = float(ov["military_tax_percent"])
                if ov.get("fixed_military_tax") is not None:
                    rates["fixed_military_tax"] = float(ov["fixed_military_tax"])
                return rates

        except Exception as e:
            print(f"DEBUG: Error in get_tax_rates: {e}")

        # 3. Поточні налаштування (для майбутніх періодів або якщо немає оверрайдів)
        today = date.today()
        if (year > today.year) or (year == today.year and month >= today.month):
            if settings.income_tax_percent is not None:
                rates["income_tax_percent"] = float(settings.income_tax_percent)
            if settings.military_tax_percent is not None:
                rates["military_tax_percent"] = float(settings.military_tax_percent)

        return rates

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
        base_esv = float(rules.get("esv_value", MIN_ESV))
        
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
        calc_date: Optional[date] = None,
        income_by_month: Optional[Dict[str, float]] = None,
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
            
            # Перевірка дати реєстрації (Правило: якщо > 20 числа, то з наступного місяця)
            is_taxable_month = True
            if settings.registration_date:
                reg_date = settings.registration_date
                # Визначаємо перший місяць, за який треба платити
                if reg_date.day > 20:
                    # Починаємо з наступного місяця
                    first_payable_year = reg_date.year + (reg_date.month // 12)
                    first_payable_month = (reg_date.month % 12) + 1
                else:
                    # Починаємо з поточного місяця
                    first_payable_year = reg_date.year
                    first_payable_month = reg_date.month
                
                # Порівнюємо поточний місяць розрахунку з першим платним місяцем
                if (curr_y < first_payable_year) or (curr_y == first_payable_year and curr_m < first_payable_month):
                    is_taxable_month = False
            
            if not is_taxable_month:
                continue # Пропускаємо місяць повністю (ні ЄСВ, ні ЄП, ні ВЗ)
            
            # 1. ЄСВ
            total_esv += TaxService.get_esv_rate(user_id, settings, curr_y, curr_m)
            
            # 2. Єдиний податок та Військовий збір
            rates = TaxService.get_tax_rates(user_id, settings, curr_y, curr_m)
            
            if settings.fop_group in [FopGroup.GROUP_1, FopGroup.GROUP_2]:
                tax_key = "single_tax_g1" if settings.fop_group == FopGroup.GROUP_1 else "single_tax_g2"
                tax_default = SINGLE_TAX_G1 if settings.fop_group == FopGroup.GROUP_1 else SINGLE_TAX_G2
                total_single_tax += rules.get(tax_key, tax_default)
                total_military_tax += rates["fixed_military_tax"]
                
            elif settings.fop_group == FopGroup.GROUP_3:
                # Для 3-ї групи податки залежать від фактичного доходу у відповідному місяці періоду.
                # Якщо є деталізація по місяцях, використовуємо її; інакше - рівномірний fallback.
                month_key = f"{curr_y}-{curr_m:02d}"
                if income_by_month is not None:
                    monthly_income = float(income_by_month.get(month_key, 0.0))
                else:
                    monthly_income = income / months_to_calc
                
                # Single Tax
                total_single_tax += monthly_income * (rates["income_tax_percent"] / 100.0)
                
                # Military tax
                total_military_tax += monthly_income * (rates["military_tax_percent"] / 100.0)
                
            elif settings.fop_group == FopGroup.GROUP_4:
                land_value = settings.normative_land_value or 0.0
                area = settings.land_area_ha or 0.0
                total_single_tax += (land_value * area * (rates["income_tax_percent"] / 100.0)) / 12
                total_military_tax += rates["fixed_military_tax"]

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
