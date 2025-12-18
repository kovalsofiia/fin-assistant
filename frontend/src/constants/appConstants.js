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

  // Дефолтні податкові налаштування (якщо API недоступне)
  DEFAULT_TAXES: {
    GROUP_3_PERCENT: 5.0,
    MILITARY_PERCENT: 1.5,
    ESV_VALUE: 1760.0,
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
  }
};