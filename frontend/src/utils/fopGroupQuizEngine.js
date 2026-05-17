/**
 * Орієнтовний підбір групи ФОП для квізу (українська спрощена система, орієнтир 2026 р.).
 * Джерела для лімітів і фіксованих платежів: індексація від мінімальної зарплати / офіційні повідомлення ДПС.
 * Уточнюйте актуальні суми в ДПС та ПКУ на дату — це навчальний/планувальний інструмент, не юридична консультація.
 */

/**
 * Річні ліміти доходу (грн), 2026 — індексація від МЗП (кратності у податковому законодавстві).
 * 1 група: 167 × МЗП → 1 444 049 грн.
 * 2 група: 834 × МЗП → 7 211 598 грн.
 * 3 група: 1167 × МЗП → 10 091 049 грн.
 */
export const LIMITS_ANNUAL_UAH_2026 = {
  g1: 1_444_049,
  g2: 7_211_598,
  g3: 10_091_049,
};

/** Для довідки в UI / дипломі: ліміт 1 групи виражений через кратність МЗП */
export const GROUP1_INCOME_LIMIT_MIN_WAGE_UNITS_2026 = 167;

/** Ліміт 2 групи: 834 МЗП (2026) */
export const GROUP2_INCOME_LIMIT_MIN_WAGE_UNITS_2026 = 834;

/** Ліміт 3 групи: 1167 МЗП (2026) */
export const GROUP3_INCOME_LIMIT_MIN_WAGE_UNITS_2026 = 1167;

/**
 * 3 група: універсальна модель для великих оборотів, без штатного ліміту «10 осіб», робота з юрособами на будь-якій системі оподаткування (за правилами ПКУ).
 */
export const GROUP3_CONTEXT_NOTE =
  '3 група — найбільш гнучка серед спрощених: значні обороти, можливість мати необмежену кількість найманих працівників (із загальними трудовими та звітними вимогами), безперешкодна співпраця з юридичними особами незалежно від їхньої системи оподаткування. Часто обирають IT, консалтинг, ЗЕД — узгоджуйте КВЕД і контракти з бухгалтером.';

/** Валюта / ЗЕД — узгоджено з тезою диплому; повний спектр операцій за іншими групами перевіряйте за ПКУ. */
export const GROUP3_FX_ZED_NOTE =
  'За поширеними підприємницькими та навчальними формулюваннями саме 3 групу розглядають як ключову для значних оборотів, валютних надходжень та ЗЕД (зокрема IT, консалтинг). Облік доходу в іноземній валюті та відповідність обраній групі завжди звіряйте з актуальним законодавством і роз\'ясненнями ДПС.';

/** За відсотковою моделлю: без доходу зазвичай немає бази для ЄП та ВЗ від доходу; ЄСВ ФОП — окреме зобов\'язання. */
export const GROUP3_ZERO_INCOME_NOTE =
  'За відсутності доходу у звітному періоді зазвичай не виникає нарахування єдиного податку та військового збору від бази «доходу»; залишаються зобов\'язання щодо ЄСВ ФОП відповідно до статусу платника — уточнюйте з бухгалтером.';

/** Ставки для UI квізу (3 група; ПДВ нараховується окремо для платників ПДВ). */
export const GROUP3_EP_PERCENT_NON_VAT = 5;
export const GROUP3_EP_PERCENT_VAT_PAYER = 3;
export const GROUP3_MILITARY_PERCENT_OF_INCOME = 1;

/**
 * Довідково для квізу / диплому: типові межі застосування 2 групи (узгоджуйте з актуальним переліком КВЕД / контрагентів).
 */
export const GROUP2_CONTEXT_NOTE =
  '2 група — наймасовіший рівень спрощеної системи: ширші можливості масштабування порівняно з 1 групою. Типово — послуги, ресторанний бізнес, мале виробництво, роздрібна торгівля (B2C; обмежена співпраця з іншими платниками єдиного податку). Надання послуг юридичним особам на загальній системі оподаткування обмежене за правилами ПКУ — уточнюйте перелік і контрагентів.';

/** Наймані працівники: обов’язки роботодавця (не входять у спрощену формулу ЄП ФОП у квізі). */
export const GROUP2_EMPLOYER_PAYROLL_NOTE =
  'Якщо є наймані працівники, роботодавець утримує з їхньої зарплати ПДФО (18%) та військовий збір (5%) і нараховує на фонд оплати праці ЄСВ (22%) — це окремий блок зобов’язань від фіксованих платежів самого ФОП на спрощеній системі.';

/**
 * Місячні фіксовані платежі для 1–2 груп (грн/міс), 2026.
 * 1 група: ЄП фіксовано 332,80 грн (10% від прожиткового мінімуму для відповідних груп населення — за правилами ПКУ),
 * незалежно від фактичного доходу в межах ліміту; ВЗ фіксовано 864,70 грн (10% від МЗП).
 * 2 група: ЄП фіксовано 1729,40 грн (20% від прожиткового мінімуму — за правилами ПКУ), незалежно від доходу в межах ліміту;
 * ВЗ — 864,70 грн (10% від МЗП).
 */
export const MONTHLY_FIXED_UAH_2026 = {
  g1: { single: 332.8, military: 864.7 },
  g2: { single: 1729.4, military: 864.7 },
};

/**
 * 4 група: окремий режим лише для сільськогосподарської діяльності.
 * Доступ зазвичай визначають за наявністю сільгосп угідь / земель водного фонду у власності чи користуванні, а не за обсягом доходу (узгоджуйте з ПКУ).
 */
export const GROUP4_CONTEXT_NOTE =
  'Четверта група відокремлена від інших і призначена виключно для діяльності в агросекторі. Умови доступу базуються на наявності відповідних земельних ділянок (угідь, водний фонд тощо), а не на лімітах доходу в тій самій логіці, що для 1–3 груп.';

/** ЄП від нормативної грошової оцінки: різні відсотки залежно від категорії земель (ПКУ). */
export const GROUP4_EP_FROM_NORMATIVE_NOTE =
  'Стратегія нарахування єдиного податку прив’язана до нормативної грошової оцінки землі: для ріллі, сіножатей і пасовищ коефіцієнт 0,95%; для земель водного фонду — 2,43%; для угідь у закритому ґрунті (наприклад тепличні комплекси) — 6,33%.';

/** Відсоток від нормативної оцінки 1 га на рік (модель квізу). */
export const GROUP4_NORMATIVE_RATE_PCT = {
  /** Рілля, сіножаті, пасовища */
  arable_pasture: 0.95,
  /** Землі водного фонду */
  water: 2.43,
  /** Закритий ґрунт (теплиці тощо) */
  closed_soil: 6.33,
};

/** Фіксований військовий збір (грн/міс): 10% від МЗП — у моделі той самий показник, що для фіксованого ВЗ інших груп (орієнтир 2026). */
export const GROUP4_MILITARY_FIXED_MONTHLY_UAH = MONTHLY_FIXED_UAH_2026.g1.military;

/** Річний фіксований ВЗ у грошовому вираженні (12 × 864,70) — для довідки в дипломі. */
export const GROUP4_MILITARY_FIXED_ANNUAL_UAH = GROUP4_MILITARY_FIXED_MONTHLY_UAH * 12;

/** Річна звітність та строки — загальна теза для навчального тексту. */
export const GROUP4_REPORTING_NOTE =
  'Звітність щодо єдиного податку за 4 групою зазвичай подається один раз на рік, не пізніше 20 лютого року, наступного за звітним, з розрахунком податку на поточний рік (форму та актуальні дедлайни перевіряйте в ДПС).';

/** ЄСВ ФОП щомісяця: 22% від МЗП → 1902,34 грн (2026, орієнтир як у проєкті) */
export const ESV_MONTHLY_UAH_2026 = 1902.34;

export const VAT_SUPPLY_THRESHOLD_UAH = 1_000_000;

export const QUIZ_LEGAL_NOTE =
  'Квіз використовує спрощені формули та орієнтовні константи на 2026 рік. Реальний вибір групи залежить від КВЕД, місця торгівлі, ЗЕД, ПДВ, перехідних правил і рішень податкової. Обов’язково узгодьте з бухгалтером.';

/**
 * @typedef {Object} FopQuizAnswers
 * @property {number} projectedAnnualIncomeUah
 * @property {number} fxIncomeSharePercent - частка валютного доходу (інформативно)
 * @property {'0'|'1-10'|'11+'} employeesBand
 * @property {'services'|'trade'|'production'|'agriculture'|'other'} activity
 * @property {boolean} zedExport
 * @property {boolean} expectsVatRegistration - очікування обороту для ПДВ / вже платник
 * @property {boolean} g1ActivityAllowed - чи підходить діяльність під обмеження 1 групи
 * @property {boolean} esvCoveredElsewhere - ЄСВ з основного місця (лише для орієнтиру Г3 у квізі)
 * @property {number} landAreaHa - для 4 групи
 * @property {number} normativeLandValuePerHa - грн/га
 * @property {'arable_pasture'|'water'|'closed_soil'} [g4LandType] - категорія землі для коефіцієнта 4 групи
 */

function annualFixed12(monthlySingle, monthlyMil) {
  return (monthlySingle + monthlyMil) * 12;
}

function annualEsvMonths(months = 12, covered = false) {
  if (covered) return 0;
  return ESV_MONTHLY_UAH_2026 * months;
}

/**
 * Оціночний річний податковий навантаж (спрощено): ЄП + ВЗ + типовий ЄСВ ФОП.
 * 3 група: ЄП 5% від доходу (неплатник ПДВ) або 3% + ПДВ (платник ПДВ — ПДВ окремо в обліку); військовий збір 1% від доходу; ЄСВ фіксовано від МЗП.
 * 4 група: ЄП ≈ нормативна оцінка × площа × (ставка % за видом угідь) на рік; ВЗ фіксовано 864,70 грн/міс; ЄСВ — мінімальний внесок.
 * Не враховує штрафи, перехід на загальну, спец режими ЗЕД тощо.
 */
export function estimateAnnualTaxLoad(group, answers, params = {}) {
  const D = Math.max(0, Number(answers.projectedAnnualIncomeUah) || 0);

  const incPct = answers.expectsVatRegistration ? params.g3VatRate ?? 3 : params.g3NoVatRate ?? 5;
  const milPct = 1;

  switch (group) {
    case 1: {
      const { single, military } = MONTHLY_FIXED_UAH_2026.g1;
      return annualFixed12(single, military) + annualEsvMonths(12, false);
    }
    case 2: {
      const { single, military } = MONTHLY_FIXED_UAH_2026.g2;
      return annualFixed12(single, military) + annualEsvMonths(12, false);
    }
    case 3: {
      const epMil = D * ((incPct + milPct) / 100);
      const esv = annualEsvMonths(12, !!answers.esvCoveredElsewhere);
      return epMil + esv;
    }
    case 4: {
      const ha = Math.max(0, Number(answers.landAreaHa) || 0);
      const norm = Math.max(0, Number(answers.normativeLandValuePerHa) || 0);
      const lt = answers.g4LandType;
      const fromMap =
        lt && GROUP4_NORMATIVE_RATE_PCT[lt] != null ? GROUP4_NORMATIVE_RATE_PCT[lt] : GROUP4_NORMATIVE_RATE_PCT.arable_pasture;
      const ratePct = params.g4RatePct ?? fromMap;
      const landTaxAnnual = ha * norm * (ratePct / 100);
      const militaryAnnual = GROUP4_MILITARY_FIXED_MONTHLY_UAH * 12;
      return landTaxAnnual + militaryAnnual + annualEsvMonths(12, false);
    }
    default:
      return Infinity;
  }
}

function eligibleGroup1(a) {
  if (a.employeesBand !== '0')
    return {
      ok: false,
      reason: '1 група: законодавство не допускає використання найманої праці (лише індивідуальна діяльність).',
    };
  if (!a.g1ActivityAllowed)
    return {
      ok: false,
      reason: '1 група: не кожен вид діяльності підходить (типово — роздріб із торговельних місць на ринках, побутові послуги населенню тощо).',
    };
  if (a.projectedAnnualIncomeUah > LIMITS_ANNUAL_UAH_2026.g1)
    return {
      ok: false,
      reason: `Дохід перевищує ліміт 1 групи (${GROUP1_INCOME_LIMIT_MIN_WAGE_UNITS_2026} МЗП, ${LIMITS_ANNUAL_UAH_2026.g1.toLocaleString('uk-UA')} грн).`,
    };
  if (a.activity === 'agriculture')
    return {
      ok: false,
      reason: '1 група: для класичного сільгосп з землею зазвичай розглядають 4 групу або 3 — уточніть за КВЕД.',
    };
  return { ok: true, reason: null };
}

function eligibleGroup2(a) {
  if (a.employeesBand === '11+')
    return {
      ok: false,
      reason: '2 група: одночасно не більше 10 найманих працівників (ширші можливості порівняно з 1 групою, де найм заборонений).',
    };
  if (a.projectedAnnualIncomeUah > LIMITS_ANNUAL_UAH_2026.g2)
    return {
      ok: false,
      reason: `Дохід перевищує ліміт 2 групи (${GROUP2_INCOME_LIMIT_MIN_WAGE_UNITS_2026} МЗП, ${LIMITS_ANNUAL_UAH_2026.g2.toLocaleString('uk-UA')} грн).`,
    };
  return { ok: true, reason: null };
}

function eligibleGroup3(a) {
  if (a.projectedAnnualIncomeUah > LIMITS_ANNUAL_UAH_2026.g3)
    return {
      ok: false,
      reason: `Дохід перевищує ліміт 3 групи (${GROUP3_INCOME_LIMIT_MIN_WAGE_UNITS_2026} МЗП, ${LIMITS_ANNUAL_UAH_2026.g3.toLocaleString('uk-UA')} грн) — можливий перехід на загальну систему.`,
    };
  return { ok: true, reason: null };
}

function eligibleGroup4(a) {
  if (a.activity !== 'agriculture')
    return { ok: false, reason: '4 група: лише для сільськогосподарської діяльності з відповідними земельними ділянками.' };
  if (a.employeesBand !== '0')
    return {
      ok: false,
      reason: '4 група: у типовій моделі спрощеної 4 групи наймані працівники не передбачені (узгодьте з ПКУ та бухгалтером).',
    };
  const ha = Number(a.landAreaHa) || 0;
  const norm = Number(a.normativeLandValuePerHa) || 0;
  if (ha <= 0 || norm <= 0)
    return {
      ok: false,
      reason: '4 група: потрібні площа угідь (га) та нормативна грошова оцінка землі (грн/га) — база нарахування ЄП.',
    };
  return { ok: true, reason: null };
}

/**
 * Повертає порівняння груп і рекомендацію з мінімальним оціночним навантаженням серед допустимих.
 */
export function evaluateFopGroupQuiz(answers) {
  const groups = [1, 2, 3, 4].map((g) => {
    let elig = { ok: false, reason: '' };
    if (g === 1) elig = eligibleGroup1(answers);
    else if (g === 2) elig = eligibleGroup2(answers);
    else if (g === 3) elig = eligibleGroup3(answers);
    else elig = eligibleGroup4(answers);

    const tax = elig.ok ? estimateAnnualTaxLoad(g, answers) : null;
    return {
      group: g,
      eligible: elig.ok,
      disqualifyReason: elig.ok ? null : elig.reason,
      estimatedAnnualTaxUah: tax,
    };
  });

  const feasible = groups.filter((x) => x.eligible && x.estimatedAnnualTaxUah !== null);
  let recommended = null;
  if (feasible.length) {
    recommended = feasible.reduce((best, cur) =>
      cur.estimatedAnnualTaxUah < best.estimatedAnnualTaxUah ? cur : best
    );
  }

  const fxNote =
    answers.fxIncomeSharePercent > 0
      ? 'Валютний дохід для ліміту зазвичай перераховується в гривні за курсом НБУ; для ПДВ окремо відстежують оборот постачання (поріг 1 млн грн).'
      : null;

  return {
    groups,
    recommendedGroup: recommended?.group ?? null,
    recommendedTaxUah: recommended?.estimatedAnnualTaxUah ?? null,
    fxNote,
    zedNote: answers.zedExport
      ? 'ЗЕД може впливати на ПДВ, валютний контроль і звітність — уточнюйте окремо від спрощених ставок.'
      : null,
  };
}
