import { defineStore } from 'pinia';
import api from '@/api';
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
                // Fallback to local constants
                const fallback = year >= 2026 ? APP_CONSTANTS.TAX_2026 : APP_CONSTANTS.TAX_2025;
                const normalizedFallback = {
                    esv_value: fallback.ESV_MONTHLY,
                    single_tax_g1: fallback.SINGLE_TAX_G1,
                    single_tax_g2: fallback.SINGLE_TAX_G2,
                    fixed_military_tax: fallback.FIXED_MILITARY_TAX,
                    // Add limits if needed in frontend
                    limit_g1: 1336000,
                    limit_g2: 5920000,
                    limit_g3: 9336000
                };
                this.currentRules = normalizedFallback;
                return normalizedFallback;
            } finally {
                this.isLoading = false;
            }
        }
    }
});
