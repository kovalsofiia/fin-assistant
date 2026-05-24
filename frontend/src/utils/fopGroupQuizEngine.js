/**
 * Підбір групи ФОП для квізу. Числові значення — з GET /tax/rules (через quizContext).
 * Текстові пояснення — локальні константи UI.
 */
import { emergencyQuizRulesFromConstants } from '@/utils/taxRulesContext';

export const GROUP3_CONTEXT_NOTE =
  '3 група — найбільш гнучка серед спрощених: значні обороти, можливість мати необмежену кількість найманих працівників (із загальними трудовими та звітними вимогами), безперешкодна співпраця з юридичними особами незалежно від їхньої системи оподаткування. Часто обирають IT, консалтинг, ЗЕД — узгоджуйте КВЕД і контракти з бухгалтером.';

export const GROUP3_FX_ZED_NOTE =
  'За поширеними підприємницькими та навчальними формулюваннями саме 3 групу розглядають як ключову для значних оборотів, валютних надходжень та ЗЕД (зокрема IT, консалтинг). Облік доходу в іноземній валюті та відповідність обраній групі завжди звіряйте з актуальним законодавством і роз\'ясненнями ДПС.';

export const GROUP3_ZERO_INCOME_NOTE =
  'За відсутності доходу у звітному періоді зазвичай не виникає нарахування єдиного податку та військового збору від бази «доходу»; залишаються зобов\'язання щодо ЄСВ ФОП відповідно до статусу платника — уточнюйте з бухгалтером.';

export const GROUP2_CONTEXT_NOTE =
  '2 група — наймасовіший рівень спрощеної системи: ширші можливості масштабування порівняно з 1 групою. Типово — послуги, ресторанний бізнес, мале виробництво, роздрібна торгівля (B2C; обмежена співпраця з іншими платниками єдиного податку). Надання послуг юридичним особам на загальній системі оподаткування обмежене за правилами ПКУ — уточнюйте перелік і контрагентів.';

export const GROUP2_EMPLOYER_PAYROLL_NOTE =
  'Якщо є наймані працівники, роботодавець утримує з їхньої зарплати ПДФО (18%) та військовий збір (5%) і нараховує на фонд оплати праці ЄСВ (22%) — це окремий блок зобов’язань від фіксованих платежів самого ФОП на спрощеній системі.';

export const GROUP4_CONTEXT_NOTE =
  'Четверта група відокремлена від інших і призначена виключно для діяльності в агросекторі. Умови доступу базуються на наявності відповідних земельних ділянок (угідь, водний фонд тощо), а не на лімітах доходу в тій самій логіці, що для 1–3 груп.';

export const GROUP4_EP_FROM_NORMATIVE_NOTE =
  'Стратегія нарахування єдиного податку прив’язана до нормативної грошової оцінки землі: для ріллі, сіножатей і пасовищ коефіцієнт 0,95%; для земель водного фонду — 2,43%; для угідь у закритому ґрунті (наприклад тепличні комплекси) — 6,33%.';

export const GROUP4_REPORTING_NOTE =
  'Звітність щодо єдиного податку за 4 групою зазвичай подається один раз на рік, не пізніше 20 лютого року, наступного за звітним, з розрахунком податку на поточний рік (форму та актуальні дедлайни перевіряйте в ДПС).';

export const QUIZ_LEGAL_NOTE =
  'Квіз використовує спрощені формули та актуальні правила з сервера (GET /tax/rules). Реальний вибір групи залежить від КВЕД, місця торгівлі, ЗЕД, ПДВ, перехідних правил і рішень податкової. Обов’язково узгодьте з бухгалтером.';

function resolveCtx(quizContext) {
  return quizContext || emergencyQuizRulesFromConstants();
}

function annualFixed12(monthlySingle, monthlyMil) {
  return (monthlySingle + monthlyMil) * 12;
}

function annualEsvMonths(ctx, months = 12, covered = false) {
  if (covered) return 0;
  return ctx.esvMonthly * months;
}

/**
 * Оціночний річний податковий навантаж (спрощено): ЄП + ВЗ + типовий ЄСВ ФОП.
 */
export function estimateAnnualTaxLoad(group, answers, quizContext) {
  const ctx = resolveCtx(quizContext);
  const D = Math.max(0, Number(answers.projectedAnnualIncomeUah) || 0);

  const incPct = answers.expectsVatRegistration ? ctx.g3.epVat : ctx.g3.epNonVat;
  const milPct = ctx.g3.militaryPct;

  switch (group) {
    case 1: {
      const { single, military } = ctx.monthlyFixed.g1;
      return annualFixed12(single, military) + annualEsvMonths(ctx, 12, false);
    }
    case 2: {
      const { single, military } = ctx.monthlyFixed.g2;
      return annualFixed12(single, military) + annualEsvMonths(ctx, 12, false);
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
      const fromMap =
        lt && ctx.g4Rates[lt] != null ? ctx.g4Rates[lt] : ctx.g4Rates.arable_pasture;
      const landTaxAnnual = ha * norm * (fromMap / 100);
      const militaryAnnual = ctx.militaryFixedMonthly * 12;
      return landTaxAnnual + militaryAnnual + annualEsvMonths(ctx, 12, false);
    }
    default:
      return Infinity;
  }
}

function eligibleGroup1(a, ctx) {
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
  if (a.projectedAnnualIncomeUah > ctx.limits.g1)
    return {
      ok: false,
      reason: `Дохід перевищує ліміт 1 групи (${ctx.limitMzpUnits.g1} МЗП, ${ctx.limits.g1.toLocaleString('uk-UA')} грн).`,
    };
  if (a.activity === 'agriculture')
    return {
      ok: false,
      reason: '1 група: для класичного сільгосп з землею зазвичай розглядають 4 групу або 3 — уточніть за КВЕД.',
    };
  return { ok: true, reason: null };
}

function eligibleGroup2(a, ctx) {
  if (a.employeesBand === '11+')
    return {
      ok: false,
      reason: '2 група: одночасно не більше 10 найманих працівників (ширші можливості порівняно з 1 групою, де найм заборонений).',
    };
  if (a.projectedAnnualIncomeUah > ctx.limits.g2)
    return {
      ok: false,
      reason: `Дохід перевищує ліміт 2 групи (${ctx.limitMzpUnits.g2} МЗП, ${ctx.limits.g2.toLocaleString('uk-UA')} грн).`,
    };
  return { ok: true, reason: null };
}

function eligibleGroup3(a, ctx) {
  if (a.projectedAnnualIncomeUah > ctx.limits.g3)
    return {
      ok: false,
      reason: `Дохід перевищує ліміт 3 групи (${ctx.limitMzpUnits.g3} МЗП, ${ctx.limits.g3.toLocaleString('uk-UA')} грн) — можливий перехід на загальну систему.`,
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
 * @param {import('./taxRulesContext').mapApiTaxRulesToQuizContext extends Function ? ReturnType<typeof import('./taxRulesContext').mapApiTaxRulesToQuizContext> : object} quizContext
 */
export function evaluateFopGroupQuiz(answers, quizContext) {
  const ctx = resolveCtx(quizContext);

  const groups = [1, 2, 3, 4].map((g) => {
    let elig = { ok: false, reason: '' };
    if (g === 1) elig = eligibleGroup1(answers, ctx);
    else if (g === 2) elig = eligibleGroup2(answers, ctx);
    else if (g === 3) elig = eligibleGroup3(answers, ctx);
    else elig = eligibleGroup4(answers);

    const tax = elig.ok ? estimateAnnualTaxLoad(g, answers, ctx) : null;
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
      ? `Валютний дохід для ліміту зазвичай перераховується в гривні за курсом НБУ; для ПДВ окремо відстежують оборот постачання (поріг ${ctx.vatThreshold.toLocaleString('uk-UA')} грн).`
      : null;

  return {
    groups,
    recommendedGroup: recommended?.group ?? null,
    recommendedTaxUah: recommended?.estimatedAnnualTaxUah ?? null,
    fxNote,
    zedNote: answers.zedExport
      ? 'ЗЕД може впливати на ПДВ, валютний контроль і звітність — уточнюйте окремо від спрощених ставок.'
      : null,
    quizContext: ctx,
  };
}
