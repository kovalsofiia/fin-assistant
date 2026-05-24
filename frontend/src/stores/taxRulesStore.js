import { defineStore } from 'pinia';
import api from '@/services/api';
import { APP_CONSTANTS } from '@/constants/appConstants';
import { mapApiTaxRulesToQuizContext } from '@/utils/taxRulesContext';

function emergencyFallback() {
  const d = APP_CONSTANTS.TAX_DEFAULTS;
  return {
    year: new Date().getFullYear(),
    month: new Date().getMonth() + 1,
    min_wage: d.MIN_WAGE,
    esv_value: d.ESV_VALUE,
    single_tax_g1: d.SINGLE_TAX_G1,
    single_tax_g2: d.SINGLE_TAX_G2,
    fixed_military_tax: d.FIXED_MILITARY_TAX,
    limit_g1: d.LIMIT_G1,
    limit_g2: d.LIMIT_G2,
    limit_g3: d.LIMIT_G3,
    limit_g1_mzp_units: d.LIMIT_G1_MZP_UNITS,
    limit_g2_mzp_units: d.LIMIT_G2_MZP_UNITS,
    limit_g3_mzp_units: d.LIMIT_G3_MZP_UNITS,
    income_tax_percent: d.INCOME_TAX_G3,
    income_tax_percent_vat: d.INCOME_TAX_G3_VAT,
    military_tax_percent: d.MILITARY_TAX_PERCENT,
    g4_rate_arable: d.G4_RATE_ARABLE,
    g4_rate_water: d.G4_RATE_WATER,
    g4_rate_closed_soil: d.G4_RATE_CLOSED_SOIL,
    vat_supply_threshold: d.VAT_SUPPLY_THRESHOLD,
  };
}

export const useTaxRulesStore = defineStore('taxRules', {
  state: () => ({
    rules: {},
    currentRules: null,
    quizContext: null,
    isLoading: false,
    isAdmin: false,
    adminChecked: false,
    adminList: [],
    adminLoading: false,
  }),

  getters: {
    quizCtx: (state) =>
      state.quizContext || mapApiTaxRulesToQuizContext(state.currentRules),
  },

  actions: {
    async fetchRules(year, month) {
      const key = `${year}-${month}`;
      if (this.rules[key]) {
        this.currentRules = this.rules[key];
        this.quizContext = mapApiTaxRulesToQuizContext(this.currentRules);
        return this.currentRules;
      }

      this.isLoading = true;
      try {
        const res = await api.getTaxRules(year, month);
        if (res.data) {
          this.rules[key] = res.data;
          this.currentRules = res.data;
          this.quizContext = mapApiTaxRulesToQuizContext(res.data);
          return res.data;
        }
      } catch (e) {
        console.error('Error fetching tax rules:', e);
        const fb = emergencyFallback();
        this.currentRules = fb;
        this.quizContext = mapApiTaxRulesToQuizContext(fb);
        return fb;
      } finally {
        this.isLoading = false;
      }
      return null;
    },

    async checkAdmin() {
      try {
        const res = await api.checkTaxRulesAdmin();
        this.isAdmin = !!res.data?.is_admin;
      } catch {
        this.isAdmin = false;
      } finally {
        this.adminChecked = true;
      }
    },

    async fetchAdminList() {
      this.adminLoading = true;
      try {
        const res = await api.getTaxRulesAdminList();
        this.adminList = res.data || [];
        return this.adminList;
      } finally {
        this.adminLoading = false;
      }
    },

    async updateRule(ruleId, payload) {
      const res = await api.updateTaxRule(ruleId, payload);
      if (res.data) {
        const idx = this.adminList.findIndex((r) => r.id === ruleId);
        if (idx >= 0) this.adminList[idx] = res.data;
        const key = `${res.data.year}-${res.data.month}`;
        this.rules[key] = res.data;
        if (
          this.currentRules &&
          this.currentRules.year === res.data.year &&
          this.currentRules.month === res.data.month
        ) {
          this.currentRules = res.data;
          this.quizContext = mapApiTaxRulesToQuizContext(res.data);
        }
      }
      return res.data;
    },

    async seedYear(year) {
      const res = await api.seedTaxRulesYear(year);
      await this.fetchAdminList();
      this.rules = {};
      return res.data;
    },
  },
});
