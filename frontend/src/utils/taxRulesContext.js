import { APP_CONSTANTS } from '@/constants/appConstants';

/** Fallback, якщо API недоступне (узгоджено з APP_CONSTANTS). */
export function emergencyQuizRulesFromConstants() {
  const d = APP_CONSTANTS.TAX_DEFAULTS;
  return mapApiTaxRulesToQuizContext({
    limit_g1: d.LIMIT_G1,
    limit_g2: d.LIMIT_G2,
    limit_g3: d.LIMIT_G3,
    limit_g1_mzp_units: d.LIMIT_G1_MZP_UNITS,
    limit_g2_mzp_units: d.LIMIT_G2_MZP_UNITS,
    limit_g3_mzp_units: d.LIMIT_G3_MZP_UNITS,
    single_tax_g1: d.SINGLE_TAX_G1,
    single_tax_g2: d.SINGLE_TAX_G2,
    fixed_military_tax: d.FIXED_MILITARY_TAX,
    esv_value: d.ESV_VALUE,
    income_tax_percent: d.INCOME_TAX_G3,
    income_tax_percent_vat: d.INCOME_TAX_G3_VAT,
    military_tax_percent: d.MILITARY_TAX_PERCENT,
    g4_rate_arable: d.G4_RATE_ARABLE,
    g4_rate_water: d.G4_RATE_WATER,
    g4_rate_closed_soil: d.G4_RATE_CLOSED_SOIL,
    vat_supply_threshold: d.VAT_SUPPLY_THRESHOLD,
    min_wage: d.MIN_WAGE,
  });
}

/**
 * Мапінг відповіді GET /tax/rules → контекст для квізу та UI.
 * @param {Record<string, unknown>|null|undefined} api
 */
export function mapApiTaxRulesToQuizContext(api) {
  if (!api || typeof api !== 'object') {
    return emergencyQuizRulesFromConstants();
  }

  const num = (v, fallback = 0) => {
    const n = Number(v);
    return Number.isFinite(n) ? n : fallback;
  };

  const military = num(api.fixed_military_tax, APP_CONSTANTS.TAX_DEFAULTS.FIXED_MILITARY_TAX);

  return {
    limits: {
      g1: num(api.limit_g1, APP_CONSTANTS.TAX_DEFAULTS.LIMIT_G1),
      g2: num(api.limit_g2, APP_CONSTANTS.TAX_DEFAULTS.LIMIT_G2),
      g3: num(api.limit_g3, APP_CONSTANTS.TAX_DEFAULTS.LIMIT_G3),
    },
    limitMzpUnits: {
      g1: num(api.limit_g1_mzp_units, APP_CONSTANTS.TAX_DEFAULTS.LIMIT_G1_MZP_UNITS),
      g2: num(api.limit_g2_mzp_units, APP_CONSTANTS.TAX_DEFAULTS.LIMIT_G2_MZP_UNITS),
      g3: num(api.limit_g3_mzp_units, APP_CONSTANTS.TAX_DEFAULTS.LIMIT_G3_MZP_UNITS),
    },
    monthlyFixed: {
      g1: {
        single: num(api.single_tax_g1, APP_CONSTANTS.TAX_DEFAULTS.SINGLE_TAX_G1),
        military,
      },
      g2: {
        single: num(api.single_tax_g2, APP_CONSTANTS.TAX_DEFAULTS.SINGLE_TAX_G2),
        military,
      },
    },
    esvMonthly: num(api.esv_value, APP_CONSTANTS.TAX_DEFAULTS.ESV_VALUE),
    vatThreshold: num(api.vat_supply_threshold, APP_CONSTANTS.TAX_DEFAULTS.VAT_SUPPLY_THRESHOLD),
    g3: {
      epNonVat: num(api.income_tax_percent, APP_CONSTANTS.TAX_DEFAULTS.INCOME_TAX_G3),
      epVat: num(api.income_tax_percent_vat, APP_CONSTANTS.TAX_DEFAULTS.INCOME_TAX_G3_VAT),
      militaryPct: num(api.military_tax_percent, APP_CONSTANTS.TAX_DEFAULTS.MILITARY_TAX_PERCENT),
    },
    g4Rates: {
      arable_pasture: num(api.g4_rate_arable, APP_CONSTANTS.TAX_DEFAULTS.G4_RATE_ARABLE),
      water: num(api.g4_rate_water, APP_CONSTANTS.TAX_DEFAULTS.G4_RATE_WATER),
      closed_soil: num(api.g4_rate_closed_soil, APP_CONSTANTS.TAX_DEFAULTS.G4_RATE_CLOSED_SOIL),
    },
    militaryFixedMonthly: military,
    minWage: num(api.min_wage, APP_CONSTANTS.TAX_DEFAULTS.MIN_WAGE),
  };
}
