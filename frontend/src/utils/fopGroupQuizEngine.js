/**
 * Квіз підбору групи ФОП (станом на 2026 р.).
 * Числа — з GET /tax/rules (quizContext); текстові пояснення — константи UI.
 *
 * ─── АЛГОРИТМ (дві фази) ───
 *
 * ФАЗА A — «Чи можна?» (допустимість кожної з груп 1–4)
 *   Для кожної групи перевіряються жорсткі умови з ПКУ / опису груп.
 *   Якщо хоча б одна умова не виконується — група недопустима (з текстом причини).
 *
 * ФАЗА B — «Що рекомендувати?» (пріоритетний ланцюжок, без балів)
 *   1) Сільгосп + заповнені дані землі + допустима 4 → рекомендація 4.
 *   2) Інакше, якщо профіль вимагає 3 групу (mustUseGroup3) → 3, якщо допустима.
 *   3) Інакше серед допустимих {1, 2, 3} → група з найменшим оціночним річним
 *      навантаженням (ЄП + ВЗ + ЄСВ ФОП); при рівності сум — нижчий номер групи.
 *
 * mustUseGroup3 (безальтернативні ознаки для 1–2 груп):
 *   • ЗЕД (експорт/імпорт) або будь-яка частка валютного доходу (лише 3 дозволяє валюту).
 *   • Послуги/товари юрособам на загальній системі оподаткування.
 *   • Користувач позначив планову реєстрацію платником ПДВ (галочка в квізі).
 *     Дохід ≥ порогу постачання (1 млн) сам по собі НЕ відсікає 1–2 групу — лише
 *     попередження (як VAT_REGISTRATION_REQUIRED у бекенді); платники 1–2 не є платниками ПДВ.
 *   • Понад 10 найманих працівників.
 *
 * ─── ПИТАННЯ КВІЗУ (відповіді → умови) ───
 *
 * | Питання | Поле | Вплив |
 * |---------|------|--------|
 * | Проєктований річний дохід | projectedAnnualIncomeUah | Ліміти 1/2/3; поріг ПДВ |
 * | Наймані працівники | employeesBand: 0 / 1-10 / 11+ | 1: лише 0; 2: ≤10; 3: 11+ |
 * | Вид діяльності | activity | 4: agriculture; 1: не сільгосп |
 * | ЗЕД | zedExport | mustUseGroup3; 1–2 недопустимі |
 * | ПДВ | expectsVatRegistration | mustUseGroup3; 1–2 недопустимі |
 * | B2B з юрособами (загальна система) | b2bLegalEntitiesGeneral | mustUseGroup3; 1–2 недопустимі |
 * | Підходить під 1 групу (ринок/побутові послуги) | g1ActivityAllowed | 1: обов’язково true |
 * | Частка валютного доходу, % | fxIncomeSharePercent | >0 → mustUseGroup3 |
 * | Площа угідь, га | landAreaHa | 4: обов’язково >0 |
 * | НГО землі, грн/га | normativeLandValuePerHa | 4: обов’язково >0 |
 * | Тип угідь | g4LandType | Розрахунок ЄП для 4 |
 * | ЄСВ вже сплачується | esvCoveredElsewhere | Лише оцінка податку для 3 |
 */
import { emergencyQuizRulesFromConstants } from '@/utils/taxRulesContext';

export const GROUP3_CONTEXT_NOTE =
  '3 група — найбільш гнучка серед спрощених: значні обороти, необмежена кількість найманих, співпраця з юрособами незалежно від системи оподаткування. Єдина серед груп, що дозволяє валютні надходження (IT, консалтинг, ЗЕД).';

export const QUIZ_STEP_ZEDVAT_INTRO =
  'Відповіді нижче визначають, чи можливі 1–2 групи: ЗЕД, валюта, ПДВ і робота з юрособами на загальній системі зазвичай означають лише 3 групу.';

export const GROUP3_FX_ZED_NOTE =
  '3 група — типовий вибір для ЗЕД і валютних надходжень. КВЕД і контракти звіряйте з актуальним законодавством.';

export const GROUP3_ZERO_INCOME_NOTE =
  'За відсутності доходу у звітному періоді зазвичай не нараховуються ЄП і військовий збір від бази «доход»; ЄСВ ФОП залишається — уточніть з бухгалтером.';

export const GROUP2_CONTEXT_NOTE =
  '2 група — наймасовіший рівень: послуги, HoReCa, мале виробництво, роздріб (B2C; обмежена B2B між платниками єдиного податку). Послуги юрособам на загальній системі — обмеження ПКУ.';

export const GROUP2_EMPLOYER_PAYROLL_NOTE =
  'З найманими: ПДФО 18%, військовий збір 5% із зарплати, ЄСВ 22% на фонд оплати праці — окремо від фіксованих платежів ФОП.';

export const GROUP4_CONTEXT_NOTE =
  '4 група — лише сільгосп за наявності земельних угідь; ліміти доходу 1–3 не застосовуються в тій самій логіці.';

export const GROUP4_EP_FROM_NORMATIVE_NOTE =
  'ЄП від нормативної оцінки землі: рілля/сіножаті/пасовища — 0,95%; водний фонд — 2,43%; закритий ґрунт — 6,33%.';

export const GROUP4_REPORTING_NOTE =
  'Звітність з ЄП за 4 групою — раз на рік, не пізніше 20 лютого наступного року (перевіряйте в ДПС).';

export const QUIZ_LEGAL_NOTE =
  'Квіз — спрощений орієнтир за правилами з сервера (GET /tax/rules). Реальний вибір залежить від КВЕД, місця торгівлі, перехідних правил. Узгодьте з бухгалтером.';

/** Короткий опис групи для екрану «на що звернути увагу» */
export const GROUP_FOCUS_HINTS = {
  1: 'Базовий рівень: без найму, невеликий дохід, ринок або побутові послуги.',
  2: 'Найпоширеніший варіант: послуги, торгівля, виробництво, до 10 працівників.',
  3: 'Універсальний: ЗЕД, валюта, юрособи, плановий ПДВ, понад 10 працівників.',
  4: 'Окремий режим для сільгоспу за наявності земельних угідь.',
};

/** @typedef {import('./taxRulesContext').mapApiTaxRulesToQuizContext extends Function ? ReturnType<typeof import('./taxRulesContext').mapApiTaxRulesToQuizContext> : object} QuizContext */

/**
 * @typedef {object} FopGroupQuizAnswers
 * @property {number} projectedAnnualIncomeUah
 * @property {'0'|'1-10'|'11+'} employeesBand
 * @property {'services'|'trade'|'production'|'agriculture'|'other'} activity
 * @property {number} landAreaHa
 * @property {number} normativeLandValuePerHa
 * @property {'arable_pasture'|'water'|'closed_soil'} g4LandType
 * @property {boolean} zedExport
 * @property {boolean} expectsVatRegistration
 * @property {boolean} b2bLegalEntitiesGeneral
 * @property {boolean} g1ActivityAllowed
 * @property {boolean} esvCoveredElsewhere
 * @property {number} fxIncomeSharePercent
 */

/** Спрощені кроки UI (3–4 екрани) */
export const FOP_GROUP_QUIZ_STEPS = [
  { id: 'profile', title: 'Профіль', fields: ['projectedAnnualIncomeUah', 'employeesBand', 'activity'] },
  {
    id: 'flags',
    title: 'Особливості бізнесу',
    fields: ['zedExport', 'fxIncomeSharePercent', 'expectsVatRegistration', 'b2bLegalEntitiesGeneral', 'g1ActivityAllowed'],
  },
  { id: 'land', title: 'Сільгосп (за потреби)', fields: ['landAreaHa', 'normativeLandValuePerHa', 'g4LandType'] },
];

/** Перелік питань для адмінки / документації */
export const FOP_GROUP_QUIZ_QUESTIONS = FOP_GROUP_QUIZ_STEPS;

function resolveCtx(quizContext) {
  return quizContext || emergencyQuizRulesFromConstants();
}

function annualIncome(answers) {
  return Math.max(0, Number(answers.projectedAnnualIncomeUah) || 0);
}

/** Користувач планує бути платником ПДВ — для 3 групи (ставка 3% ЄП тощо). */
function plansVatPayer(answers) {
  return !!answers.expectsVatRegistration;
}

/** Оборот від порогу обов’язкової реєстрації ПДВ — попередження, не автоматична 3 група. */
function exceedsVatSupplyThreshold(answers, ctx) {
  return annualIncome(answers) >= ctx.vatThreshold;
}

/** Валютні надходження / ЗЕД / B2B / 11+ / плановий ПДВ — лише 3 група */
function mustUseGroup3(answers, ctx) {
  if (answers.employeesBand === '11+') return true;
  if (answers.zedExport) return true;
  if (answers.b2bLegalEntitiesGeneral) return true;
  if (plansVatPayer(answers)) return true;
  if (Number(answers.fxIncomeSharePercent) > 0) return true;
  return false;
}

function hasLandForGroup4(answers) {
  const ha = Number(answers.landAreaHa) || 0;
  const norm = Number(answers.normativeLandValuePerHa) || 0;
  return ha > 0 && norm > 0;
}

// ─── Фаза A: допустимість ───

/** @param {FopGroupQuizAnswers} a @param {QuizContext} ctx */
function eligibleGroup1(a, ctx) {
  const income = annualIncome(a);
  if (a.employeesBand !== '0') {
    return { ok: false, reason: '1 група: заборонено використовувати найману працю (лише індивідуальна діяльність).' };
  }
  if (!a.g1ActivityAllowed) {
    return {
      ok: false,
      reason: '1 група: підходить для роздрібу з торговельних місць на ринках або побутових послуг населенню (ремонт взуття, пошив одягу тощо).',
    };
  }
  if (income > ctx.limits.g1) {
    return {
      ok: false,
      reason: `1 група: дохід перевищує ліміт ${ctx.limitMzpUnits.g1} МЗП (${ctx.limits.g1.toLocaleString('uk-UA')} грн).`,
    };
  }
  if (a.activity === 'agriculture') {
    return { ok: false, reason: '1 група: сільгосп — орієнтир 4 група (за землею) або 3 група.' };
  }
  if (mustUseGroup3(a, ctx)) {
    return {
      ok: false,
      reason: '1 група: ЗЕД, валюта, планова реєстрація ПДВ або B2B з юрособами на загальній системі — потрібна 3 група.',
    };
  }
  return { ok: true, reason: null };
}

/** @param {FopGroupQuizAnswers} a @param {QuizContext} ctx */
function eligibleGroup2(a, ctx) {
  const income = annualIncome(a);
  if (a.employeesBand === '11+') {
    return { ok: false, reason: '2 група: не більше 10 найманих працівників одночасно.' };
  }
  if (income > ctx.limits.g2) {
    return {
      ok: false,
      reason: `2 група: дохід перевищує ліміт ${ctx.limitMzpUnits.g2} МЗП (${ctx.limits.g2.toLocaleString('uk-UA')} грн).`,
    };
  }
  if (a.activity === 'agriculture') {
    return { ok: false, reason: '2 група: для сільгоспу — 4 група (за землею) або 3 група.' };
  }
  if (mustUseGroup3(a, ctx)) {
    return {
      ok: false,
      reason: '2 група: ЗЕД, валюта, планова реєстрація ПДВ або B2B з юрособами на загальній системі — потрібна 3 група.',
    };
  }
  return { ok: true, reason: null };
}

/** @param {FopGroupQuizAnswers} a @param {QuizContext} ctx */
function eligibleGroup3(a, ctx) {
  const income = annualIncome(a);
  if (income > ctx.limits.g3) {
    return {
      ok: false,
      reason: `3 група: дохід перевищує ліміт ${ctx.limitMzpUnits.g3} МЗП (${ctx.limits.g3.toLocaleString('uk-UA')} грн) — можлива загальна система.`,
    };
  }
  if (a.activity === 'agriculture' && hasLandForGroup4(a) && a.employeesBand === '0') {
    return {
      ok: false,
      reason: '3 група: за сільгоспом із земельними угіддями без найму типовий вибір — 4 група.',
    };
  }
  return { ok: true, reason: null };
}

/** @param {FopGroupQuizAnswers} a */
function eligibleGroup4(a) {
  if (a.activity !== 'agriculture') {
    return { ok: false, reason: '4 група: лише сільськогосподарська діяльність із відповідними земельними ділянками.' };
  }
  if (a.employeesBand !== '0') {
    return {
      ok: false,
      reason: '4 група: у типовій моделі спрощеної 4 групи наймані працівники не передбачені (уточніть з ПКУ).',
    };
  }
  if (!hasLandForGroup4(a)) {
    return {
      ok: false,
      reason: '4 група: вкажіть площу угідь (га) та нормативну грошову оцінку землі (грн/га).',
    };
  }
  return { ok: true, reason: null };
}

function checkEligibility(group, answers, ctx) {
  if (group === 1) return eligibleGroup1(answers, ctx);
  if (group === 2) return eligibleGroup2(answers, ctx);
  if (group === 3) return eligibleGroup3(answers, ctx);
  return eligibleGroup4(answers);
}

// ─── Фаза B: рекомендація ───

/**
 * @param {Array<{ group: number, eligible: boolean, estimatedAnnualTaxUah: number|null }>} groups
 * @param {number[]} candidateGroups
 * @returns {{ group: number, estimatedAnnualTaxUah: number }|null}
 */
function pickLowestTaxCandidate(groups, candidateGroups = [1, 2, 3]) {
  const feasible = groups.filter(
    (g) =>
      candidateGroups.includes(g.group) &&
      g.eligible &&
      g.estimatedAnnualTaxUah != null &&
      Number.isFinite(g.estimatedAnnualTaxUah)
  );
  if (!feasible.length) return null;

  const minTax = Math.min(...feasible.map((g) => g.estimatedAnnualTaxUah));
  const tied = feasible.filter((g) => g.estimatedAnnualTaxUah === minTax);
  return tied.reduce((best, cur) => (cur.group < best.group ? cur : best));
}

/**
 * @param {FopGroupQuizAnswers} answers
 * @param {Array<{ group: number, eligible: boolean, estimatedAnnualTaxUah: number|null }>} groups
 * @param {QuizContext} ctx
 * @returns {{ group: number|null, mode: string }}
 */
function pickRecommendedGroup(answers, groups, ctx) {
  const isEligible = (n) => groups.find((g) => g.group === n)?.eligible === true;

  if (answers.activity === 'agriculture' && isEligible(4)) {
    return { group: 4, mode: 'agriculture' };
  }

  if (mustUseGroup3(answers, ctx)) {
    if (isEligible(3)) return { group: 3, mode: 'requires_group3' };
    return { group: null, mode: 'none' };
  }

  const lowest = pickLowestTaxCandidate(groups);
  if (lowest) return { group: lowest.group, mode: 'lowest_tax' };

  return { group: null, mode: 'none' };
}

/**
 * М’яке формулювання результату: на які групи звернути увагу.
 * @param {number|null} recommendedGroup
 * @param {Array<{ group: number, eligible: boolean }>} groups
 * @param {string} recommendationMode
 */
export function buildQuizFocusSummary(recommendedGroup, groups, recommendationMode) {
  const eligibleRows = groups.filter((g) => g.eligible);

  let headline;
  if (!recommendedGroup) {
    headline = 'За цими відповідями жодна група не виглядає допустимою — перевірте дохід і обмеження.';
  } else if (recommendationMode === 'agriculture') {
    headline = `Насамперед розгляньте ${recommendedGroup} групу — типовий режим для сільгоспу з землею.`;
  } else if (recommendationMode === 'requires_group3') {
    headline = `Орієнтир — ${recommendedGroup} група: у профілі є ознаки, для яких 1–2 групи зазвичай не підходять.`;
  } else {
    headline = `Насамперед зверніть увагу на ${recommendedGroup} групу (серед допустимих — найменше оціночне податкове навантаження).`;
  }

  const groupsToConsider = [1, 2, 3, 4]
    .map((n) => {
      const row = groups.find((g) => g.group === n);
      if (!row?.eligible) return null;
      return {
        group: n,
        hint: GROUP_FOCUS_HINTS[n],
        isPrimary: n === recommendedGroup,
      };
    })
    .filter(Boolean);

  const alsoConsider = groupsToConsider
    .filter((g) => !g.isPrimary)
    .map((g) => g.group);

  return {
    primaryGroup: recommendedGroup,
    headline,
    groupsToConsider,
    alsoConsider,
    eligibleCount: eligibleRows.length,
  };
}

function formatTaxUah(n) {
  return `${Math.round(n).toLocaleString('uk-UA')} грн`;
}

/**
 * @param {FopGroupQuizAnswers} answers
 * @param {Array<{ group: number, eligible: boolean, estimatedAnnualTaxUah: number|null }>} groups
 * @param {QuizContext} ctx
 * @param {number|null} recommendedGroup
 * @param {string} recommendationMode
 */
function buildRecommendationReasons(answers, groups, ctx, recommendedGroup, recommendationMode) {
  const reasons = [];

  if (answers.activity === 'agriculture') {
    if (groups.find((g) => g.group === 4)?.eligible) {
      reasons.push('Сільгосп із земельними угіддями — пріоритет 4 групи (ЄП від нормативної оцінки землі).');
    } else {
      reasons.push('Сільгосп: для 4 групи потрібні площа та нормативна оцінка землі; інакше — 3 група.');
    }
  }

  if (answers.employeesBand === '0') {
    reasons.push('Без найму можлива 1 група за видом діяльності та лімітом доходу.');
  } else if (answers.employeesBand === '1-10') {
    reasons.push('1–10 найманих — 2 або 3 група залежно від доходу та ЗЕД/ПДВ/валюти.');
  } else if (answers.employeesBand === '11+') {
    reasons.push('Понад 10 найманих — серед спрощених лише 3 група.');
  }

  if (answers.zedExport) reasons.push('ЗЕД — лише 3 група дозволяє типову модель валютних операцій.');
  if (Number(answers.fxIncomeSharePercent) > 0) {
    reasons.push('Валютний дохід — лише 3 група серед груп спрощеної системи.');
  }
  if (answers.b2bLegalEntitiesGeneral) {
    reasons.push('Юрособи на загальній системі — 1–2 групи недопустимі, орієнтир 3 група.');
  }
  if (plansVatPayer(answers)) {
    reasons.push('Планується реєстрація платником ПДВ — 3 група (3% або 5% ЄП від доходу + облік ПДВ).');
  } else if (exceedsVatSupplyThreshold(answers, ctx)) {
    reasons.push(
      `Дохід від порогу обов’язкової реєстрації ПДВ (${ctx.vatThreshold.toLocaleString('uk-UA')} грн за 12 міс.) — перевірте, чи потрібна реєстрація; 1–2 групи залишаються неплатниками ПДВ, ліміт 2 групи — до ${ctx.limits.g2.toLocaleString('uk-UA')} грн.`
    );
  }

  if (recommendationMode === 'lowest_tax' && recommendedGroup != null) {
    const compared = groups
      .filter(
        (g) =>
          [1, 2, 3].includes(g.group) &&
          g.eligible &&
          g.estimatedAnnualTaxUah != null &&
          Number.isFinite(g.estimatedAnnualTaxUah)
      )
      .sort((a, b) => a.group - b.group);

    if (compared.length > 1) {
      const summary = compared
        .map((g) => `${g.group} група — ${formatTaxUah(g.estimatedAnnualTaxUah)}`)
        .join('; ');
      reasons.push(
        `Серед допустимих груп порівняно оціночне річне навантаження (ЄП + ВЗ + ЄСВ ФОП): ${summary}. Обрано ${recommendedGroup} групу — найменша сума.`
      );
    } else if (compared.length === 1) {
      reasons.push(
        `Оціночне річне навантаження (ЄП + ВЗ + ЄСВ ФОП) для ${recommendedGroup} групи — ${formatTaxUah(compared[0].estimatedAnnualTaxUah)}.`
      );
    }
    reasons.push(
      'Розрахунок не включає податки з фонду оплати праці найманих (ПДФО, ЄСВ роботодавця тощо).'
    );
  }

  return reasons;
}

// ─── Оцінка податкового навантаження (для таблиці результатів) ───

function annualFixed12(monthlySingle, monthlyMil) {
  return (monthlySingle + monthlyMil) * 12;
}

function annualEsvMonths(ctx, months = 12, covered = false) {
  if (covered) return 0;
  return ctx.esvMonthly * months;
}

/**
 * Оціночне річне навантаження (ЄП + ВЗ + типовий ЄСВ ФОП).
 * @param {number} group
 * @param {FopGroupQuizAnswers} answers
 * @param {QuizContext} quizContext
 */
export function estimateAnnualTaxLoad(group, answers, quizContext) {
  const ctx = resolveCtx(quizContext);
  const D = annualIncome(answers);
  const incPct = answers.expectsVatRegistration ? ctx.g3.epVat : ctx.g3.epNonVat;
  const milPct = ctx.g3.militaryPct;

  switch (group) {
    case 1: {
      const { single, military } = ctx.monthlyFixed.g1;
      return annualFixed12(single, military) + annualEsvMonths(ctx);
    }
    case 2: {
      const { single, military } = ctx.monthlyFixed.g2;
      return annualFixed12(single, military) + annualEsvMonths(ctx);
    }
    case 3: {
      const epMil = D * ((incPct + milPct) / 100);
      const esv = annualEsvMonths(ctx, 12, !!answers.esvCoveredElsewhere);
      return epMil + esv;
    }
    case 4: {
      const ha = Math.max(0, Number(answers.landAreaHa) || 0);
      const norm = Math.max(0, Number(answers.normativeLandValuePerHa) || 0);
      const lt = answers.g4LandType;
      const rate =
        lt && ctx.g4Rates[lt] != null ? ctx.g4Rates[lt] : ctx.g4Rates.arable_pasture;
      const landTaxAnnual = ha * norm * (rate / 100);
      const militaryAnnual = ctx.militaryFixedMonthly * 12;
      return landTaxAnnual + militaryAnnual + annualEsvMonths(ctx);
    }
    default:
      return Infinity;
  }
}

/**
 * @param {FopGroupQuizAnswers} answers
 * @param {QuizContext|null|undefined} quizContext
 */
export function evaluateFopGroupQuiz(answers, quizContext) {
  const ctx = resolveCtx(quizContext);

  const groups = [1, 2, 3, 4].map((g) => {
    const elig = checkEligibility(g, answers, ctx);
    const tax = elig.ok ? estimateAnnualTaxLoad(g, answers, ctx) : null;
    return {
      group: g,
      eligible: elig.ok,
      disqualifyReason: elig.ok ? null : elig.reason,
      estimatedAnnualTaxUah: tax,
    };
  });

  const { group: recommendedGroup, mode: recommendationMode } = pickRecommendedGroup(
    answers,
    groups,
    ctx
  );

  const recommended = groups.find((g) => g.group === recommendedGroup) ?? null;
  const recommendationReasons = buildRecommendationReasons(
    answers,
    groups,
    ctx,
    recommendedGroup,
    recommendationMode
  );

  const fxNote =
    Number(answers.fxIncomeSharePercent) > 0
      ? `Валютний дохід перераховується в гривні за курсом НБУ; для ПДВ окремо відстежують оборот (поріг ${ctx.vatThreshold.toLocaleString('uk-UA')} грн).`
      : null;

  const focusSummary = buildQuizFocusSummary(recommendedGroup, groups, recommendationMode);

  return {
    groups,
    recommendedGroup,
    recommendedTaxUah: recommended?.estimatedAnnualTaxUah ?? null,
    recommendationMode,
    recommendationReasons,
    focusSummary,
    fxNote,
    zedNote: answers.zedExport
      ? 'ЗЕД впливає на ПДВ, валютний контроль і звітність — уточніть окремо від ставок спрощеної системи.'
      : null,
    quizContext: ctx,
    mustUseGroup3: mustUseGroup3(answers, ctx),
    vatRegistrationWarning:
      !plansVatPayer(answers) && exceedsVatSupplyThreshold(answers, ctx),
  };
}
