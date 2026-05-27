/**
 * Довідник правил квізу ФОП (read-only для адмінки).
 * Логіка — fopGroupQuizEngine.js (дві фази: допустимість → пріоритетна рекомендація).
 */

/** @typedef {'eligibility'|'recommendation'|'tax'|'pathing'|'questions'} QuizRuleType */

/**
 * @typedef {object} FopQuizRuleRow
 * @property {string} id
 * @property {1|2|3|4|'all'} group
 * @property {QuizRuleType} type
 * @property {string} condition
 * @property {string} effect
 * @property {string} [note]
 */

/** @type {{ id: QuizRuleType, label: string }[]} */
export const QUIZ_RULE_TYPE_LABELS = [
  { id: 'questions', label: 'Питання квізу' },
  { id: 'eligibility', label: 'Допустимість (фаза A)' },
  { id: 'recommendation', label: 'Рекомендація (фаза B)' },
  { id: 'tax', label: 'Розрахунок податку' },
  { id: 'pathing', label: 'Кроки квізу' },
];

/** @type {FopQuizRuleRow[]} */
export const FOP_GROUP_QUIZ_RULES_CATALOG = [
  {
    id: 'q-income',
    group: 'all',
    type: 'questions',
    condition: 'Проєктований річний дохід',
    effect: 'Ліміти 1–3 груп; поріг ПДВ (vat_supply_threshold)',
  },
  {
    id: 'q-employees',
    group: 'all',
    type: 'questions',
    condition: 'Наймані: 0 / 1–10 / 11+',
    effect: '1: лише 0; 2: до 10; 3: необмежено; 4 (типово): 0',
  },
  {
    id: 'q-activity',
    group: 'all',
    type: 'questions',
    condition: 'Вид діяльності',
    effect: '4 — agriculture; 1–2 — не сільгосп',
  },
  {
    id: 'q-zedvat',
    group: 'all',
    type: 'questions',
    condition: 'ЗЕД, ПДВ, B2B юрособи (загальна система)',
    effect: 'mustUseGroup3 → лише 3 група',
  },
  {
    id: 'q-g1',
    group: 1,
    type: 'questions',
    condition: 'Підтвердження виду для 1 групи',
    effect: 'Ринки / побутові послуги населенню',
  },
  {
    id: 'q-fx',
    group: 'all',
    type: 'questions',
    condition: 'Частка валютного доходу, %',
    effect: '> 0 → mustUseGroup3',
  },
  {
    id: 'q-land',
    group: 4,
    type: 'questions',
    condition: 'Площа, НГО, тип угідь',
    effect: 'Обов’язково для допустимості 4 групи',
  },
  {
    id: 'path-profile',
    group: 'all',
    type: 'pathing',
    condition: 'Завжди',
    effect: 'Крок «Ваш профіль» — дохід, найм, діяльність',
  },
  {
    id: 'path-flags',
    group: 'all',
    type: 'pathing',
    condition: 'Завжди',
    effect: 'Крок «Особливості» — ЗЕД/валюта, ПДВ, B2B, 1 група (за потреби)',
  },
  {
    id: 'path-land',
    group: 4,
    type: 'pathing',
    condition: 'activity === "agriculture"',
    effect: 'Крок «Сільгосп» — земля для 4 групи',
  },
  {
    id: 'must-g3',
    group: 3,
    type: 'recommendation',
    condition: 'ЗЕД OR fx>0 OR B2B загальна OR галочка ПДВ OR 11+ працівників',
    effect: 'Рекомендація 3 групи (режим requires_group3)',
  },
  {
    id: 'rec-agri',
    group: 4,
    type: 'recommendation',
    condition: 'agriculture + допустима 4',
    effect: 'Рекомендація 4 групи (режим agriculture)',
  },
  {
    id: 'rec-lowest-tax',
    group: 'all',
    type: 'recommendation',
    condition: 'Немає mustUseGroup3; допустимі 1–3',
    effect: 'Мінімальне оціночне річне навантаження (ЄП+ВЗ+ЄСВ ФОП); при рівності — нижчий номер (lowest_tax)',
  },
  {
    id: 'g1-employees',
    group: 1,
    type: 'eligibility',
    condition: 'employeesBand !== "0"',
    effect: 'Недопустима',
  },
  {
    id: 'g1-activity',
    group: 1,
    type: 'eligibility',
    condition: 'g1ActivityAllowed === false',
    effect: 'Недопустима',
  },
  {
    id: 'g1-income',
    group: 1,
    type: 'eligibility',
    condition: 'Дохід > limit_g1',
    effect: 'Недопустима',
  },
  {
    id: 'g1-agri',
    group: 1,
    type: 'eligibility',
    condition: 'activity === agriculture',
    effect: 'Недопустима',
  },
  {
    id: 'g1-must3',
    group: 1,
    type: 'eligibility',
    condition: 'mustUseGroup3',
    effect: 'Недопустима → 3 група',
  },
  {
    id: 'g2-employees',
    group: 2,
    type: 'eligibility',
    condition: 'employeesBand === "11+"',
    effect: 'Недопустима',
  },
  {
    id: 'g2-income',
    group: 2,
    type: 'eligibility',
    condition: 'Дохід > limit_g2',
    effect: 'Недопустима',
  },
  {
    id: 'g2-agri',
    group: 2,
    type: 'eligibility',
    condition: 'activity === agriculture',
    effect: 'Недопустима',
  },
  {
    id: 'g2-must3',
    group: 2,
    type: 'eligibility',
    condition: 'mustUseGroup3',
    effect: 'Недопустима → 3 група',
  },
  {
    id: 'g3-income',
    group: 3,
    type: 'eligibility',
    condition: 'Дохід > limit_g3',
    effect: 'Недопустима',
  },
  {
    id: 'g3-agri-land',
    group: 3,
    type: 'eligibility',
    condition: 'Сільгосп + земля + без найму',
    effect: 'Недопустима → пріоритет 4',
  },
  {
    id: 'g4-not-agri',
    group: 4,
    type: 'eligibility',
    condition: 'activity !== agriculture',
    effect: 'Недопустима',
  },
  {
    id: 'g4-employees',
    group: 4,
    type: 'eligibility',
    condition: 'employeesBand !== "0"',
    effect: 'Недопустима',
  },
  {
    id: 'g4-land',
    group: 4,
    type: 'eligibility',
    condition: 'Немає площі або НГО',
    effect: 'Недопустима',
  },
  {
    id: 'tax-g1',
    group: 1,
    type: 'tax',
    condition: 'Допустима',
    effect: '(ЄП + ВЗ фікс.)×12 + ЄСВ×12',
  },
  {
    id: 'tax-g2',
    group: 2,
    type: 'tax',
    condition: 'Допустима',
    effect: '(ЄП + ВЗ фікс.)×12 + ЄСВ×12',
  },
  {
    id: 'tax-g3',
    group: 3,
    type: 'tax',
    condition: 'Допустима',
    effect: '(ЄП% + ВЗ%)×дохід + ЄСВ (0 якщо esvCoveredElsewhere)',
  },
  {
    id: 'tax-g4',
    group: 4,
    type: 'tax',
    condition: 'Допустима',
    effect: 'НГО×га×ставка% + ВЗ×12 + ЄСВ×12',
  },
];

/**
 * @param {QuizRuleType|null} typeFilter
 * @param {number|'all'|null} groupFilter
 */
export function filterQuizRulesCatalog(typeFilter, groupFilter) {
  return FOP_GROUP_QUIZ_RULES_CATALOG.filter((row) => {
    if (typeFilter && row.type !== typeFilter) return false;
    if (groupFilter == null) return true;
    if (groupFilter === 'all') return row.group === 'all';
    return row.group === groupFilter || row.group === 'all';
  });
}
