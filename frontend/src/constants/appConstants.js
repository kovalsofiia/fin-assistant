export const APP_CONSTANTS = {
  // Кольори (використовуються для динамічних стилів)
  COLORS: {
    PRIMARY: '#2563EB', // blue-600
    BACKGROUND: '#F8FAFC', // slate-50
    TEXT_MAIN: '#1E293B', // slate-800
    TEXT_ACCENT: '#1E3A8A', // blue-900
    SUCCESS: '#10B981',
    DANGER: '#EF4444',
  },

  // Тексти для UI
  LABELS: {
    INCOME: 'Дохід',
    EXPENSE: 'Витрата',
    CURRENCY_UAH: 'UAH',
    CURRENCY_USD: 'USD',
    CURRENCY_EUR: 'EUR',
  },

  // Список категорій за замовчуванням (для створення нових юзерів)
  DEFAULT_CATEGORIES: [
    { name: 'Продаж товарів', type: 'income' },
    { name: 'Послуги (IT/Маркетинг)', type: 'income' },
    { name: 'Оренда', type: 'expense' },
    { name: 'Податки', type: 'expense' },
    { name: 'Банківські послуги', type: 'expense' },
    { name: 'Зарплата', type: 'expense' },
  ],

  // Обмеження
  VALIDATION: {
    MIN_AMOUNT: 0.01,
    MAX_DESC_LENGTH: 150,
  },

  // Податкові константи (fallback; джерело істини — GET /tax/rules)
  TAX_DEFAULTS: {
    MIN_WAGE: 8650.0,
    ESV_VALUE: 1902.34,
    SINGLE_TAX_G1: 332.8,
    SINGLE_TAX_G2: 1729.4,
    FIXED_MILITARY_TAX: 864.7,
    LIMIT_G1: 1_444_049,
    LIMIT_G2: 7_211_598,
    LIMIT_G3: 10_091_049,
    LIMIT_G1_MZP_UNITS: 167,
    LIMIT_G2_MZP_UNITS: 834,
    LIMIT_G3_MZP_UNITS: 1167,
    INCOME_TAX_G3: 5.0,
    INCOME_TAX_G3_VAT: 3.0,
    MILITARY_TAX_PERCENT: 1.0,
    G4_RATE_ARABLE: 0.95,
    G4_RATE_WATER: 2.43,
    G4_RATE_CLOSED_SOIL: 6.33,
    VAT_SUPPLY_THRESHOLD: 1_000_000,
  },

  /** Орієнтовні строки сплати для підказок у віджеті податків */
  PAYMENT_TERM_HINTS: {
    1: 'Щомісяця, до 20-го числа наступного місяця',
    2: 'Щомісяця, до 20-го числа наступного місяця',
    3: 'Щокварталу, до 20-го числа наступного кварталу',
    4: 'За річним циклом; див. календар звітності',
  },
};