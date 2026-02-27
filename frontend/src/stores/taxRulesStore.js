import { defineStore } from 'pinia';
import api from '@/services/api';
import { APP_CONSTANTS } from '@/constants/appConstants';

export const useTaxRulesStore = defineStore('taxRules', {
    state: () => ({
        rules: {}, // keyed by "year-month"
        currentRules: null,
        isLoading: false
    }),

    actions: {
        async fetchRules(year, month) {
            const key = `${year}-${month}`;
            if (this.rules[key]) {
                this.currentRules = this.rules[key];
                return this.rules[key];
            }

            this.isLoading = true;
            try {
                const res = await api.getTaxRules(year, month);
                if (res.data) {
                    this.rules[key] = res.data;
                    this.currentRules = res.data;
                    return res.data;
                }
            } catch (e) {
                console.error("Error fetching tax rules:", e);
                // Fallback to defaults from constants if API fails
                const emergencyFallback = {
                    esv_value: APP_CONSTANTS.TAX_DEFAULTS.ESV_VALUE,
                    single_tax_g1: APP_CONSTANTS.TAX_DEFAULTS.SINGLE_TAX_G1,
                    single_tax_g2: APP_CONSTANTS.TAX_DEFAULTS.SINGLE_TAX_G2,
                    fixed_military_tax: APP_CONSTANTS.TAX_DEFAULTS.FIXED_MILITARY_TAX,
                    limit_g1: APP_CONSTANTS.TAX_DEFAULTS.LIMIT_G1,
                    limit_g2: APP_CONSTANTS.TAX_DEFAULTS.LIMIT_G2,
                    limit_g3: APP_CONSTANTS.TAX_DEFAULTS.LIMIT_G3,
                    military_tax_percent: APP_CONSTANTS.TAX_DEFAULTS.MILITARY_TAX_PERCENT,
                    income_tax_percent: APP_CONSTANTS.TAX_DEFAULTS.INCOME_TAX_G3
                };
                this.currentRules = emergencyFallback;
                return emergencyFallback;
            } finally {
                this.isLoading = false;
            }
        }
    }
});
