from typing import List, Optional, Dict
from datetime import date
from models.common import FopGroup, TaxSystem, ActivityType, ReportingPeriod
from models.setting import FopSettingsBase

from core.constants import (
    MIN_ESV, 
    SINGLE_TAX_G1, 
    SINGLE_TAX_G2, 
    FIXED_MILITARY_TAX,
    LIMIT_G1,
    LIMIT_G2,
    LIMIT_G3
)

class TaxService:
    @staticmethod
    def verify_group_restrictions(settings: FopSettingsBase, annual_income: float) -> List[str]:
        errors = []
        
        # Group 1
        if settings.fop_group == FopGroup.GROUP_1:
            if annual_income > LIMIT_G1:
                errors.append(f"GROUP_1_VIOLATION: Income exceeds UAH {LIMIT_G1:,.0f}")
            if settings.has_employees:
                errors.append("GROUP_1_VIOLATION: Employees are prohibited")
                
        # Group 2
        elif settings.fop_group == FopGroup.GROUP_2:
            if annual_income > LIMIT_G2:
                errors.append(f"GROUP_2_LIMIT_EXCEEDED: Income exceeds UAH {LIMIT_G2:,.0f}")
            if settings.employees_count > 10:
                errors.append("GROUP_2_LIMIT_EXCEEDED: Number of employees exceeds 10")
                
        # Group 3
        elif settings.fop_group == FopGroup.GROUP_3:
            if annual_income > LIMIT_G3:
                errors.append(f"AUTO_TRANSITION_GENERAL: Income exceeds UAH {LIMIT_G3:,.0f}. Transition to general system required.")
                
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
        
        # Limit Approach Warning (90%)
        limit = 0
        if settings.fop_group == FopGroup.GROUP_1: limit = LIMIT_G1
        elif settings.fop_group == FopGroup.GROUP_2: limit = LIMIT_G2
        elif settings.fop_group == FopGroup.GROUP_3: limit = LIMIT_G3
        
        if limit > 0 and annual_income >= (limit * 0.9):
            warnings.append("LIMIT_APPROACHING")
            
        # VAT Registration Warning
        if not settings.is_vat_payer and annual_income > 1000000.0:
            warnings.append("VAT_REGISTRATION_REQUIRED")
            
        return warnings

    @staticmethod
    def calculate_taxes(settings: FopSettingsBase, income: float, period: ReportingPeriod = ReportingPeriod.MONTH) -> Dict:
        # Base ESV is always charged even if income is zero
        esv = MIN_ESV
        
        single_tax = 0.0
        military_tax = 0.0
        vat = None
        
        if settings.fop_group == FopGroup.GROUP_1:
            single_tax = SINGLE_TAX_G1
            military_tax = FIXED_MILITARY_TAX
            
        elif settings.fop_group == FopGroup.GROUP_2:
            single_tax = SINGLE_TAX_G2
            military_tax = FIXED_MILITARY_TAX
            
        elif settings.fop_group == FopGroup.GROUP_3:
            # Single Tax: use percent from settings or fallback to 3%/5%
            rate = (settings.income_tax_percent / 100.0) if settings.income_tax_percent is not None else (0.03 if settings.is_vat_payer else 0.05)
            single_tax = income * rate
            # Military tax: use percent from settings or fallback to 1% for G3
            mil_rate = (settings.military_tax_percent / 100.0) if settings.military_tax_percent is not None else 0.01
            military_tax = income * mil_rate
            
        elif settings.fop_group == FopGroup.GROUP_4:
            # Single tax — normative monetary valuation of land × land area × rate
            # Using 0.95% as a common rate if not specified (range 0.09% - 1.8%)
            land_value = settings.normative_land_value or 0.0
            area = settings.land_area_ha or 0.0
            single_tax = (land_value * area * 0.0095) / 12 # Monthly share of annual tax
            military_tax = FIXED_MILITARY_TAX

        # Adjust for period
        months = 1
        if period == ReportingPeriod.QUARTER: months = 3
        elif period == ReportingPeriod.YEAR: months = 12
        
        return {
            "single_tax": round(single_tax * months, 2),
            "esv": round(esv * months, 2),
            "military_tax": round(military_tax * months, 2),
            "vat": vat,
            "total_monthly_tax": round(single_tax + esv + military_tax, 2),
            "total_quarterly_tax": round((single_tax + esv + military_tax) * 3, 2),
            "total_annual_tax": round((single_tax + esv + military_tax) * 12, 2)
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
