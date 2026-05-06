import { defineStore } from 'pinia';
import api from '@/services/api';

export const useBudgetStore = defineStore('budgets', {
    state: () => ({
        budgets: [],
        budgetProgress: [],
        reports: null,
        taxHistory: [],
        isLoading: false,
        error: null
    }),

    actions: {
        async fetchBudgets() {
            this.isLoading = true;
            try {
                const res = await api.getBudgets();
                this.budgets = res.data;
            } catch (e) {
                console.error("Error fetching budgets:", e);
                this.error = "Не вдалося завантажити бюджети";
            } finally {
                this.isLoading = false;
            }
        },

        async fetchBudgetProgress() {
            this.isLoading = true;
            try {
                const res = await api.getBudgetsProgress();
                this.budgetProgress = res.data;
            } catch (e) {
                console.error("Error fetching budget progress:", e);
                this.error = "Не вдалося завантажити прогрес бюджетів";
            } finally {
                this.isLoading = false;
            }
        },

        async createBudget(budgetData) {
            await api.createBudget(budgetData);
            await this.fetchBudgetProgress();
        },

        async updateBudget(budgetId, _userId, patchData) {
            await api.patchBudget(budgetId, patchData);
            await this.fetchBudgetProgress();
        },

        async deleteBudget(budgetId, _userId) {
            await api.deleteBudget(budgetId);
            await this.fetchBudgetProgress();
        },

        async fetchAnalyticsReports(period = 'monthly', startDate = null, endDate = null) {
            this.isLoading = true;
            try {
                const res = await api.getAnalyticsReports(period, startDate, endDate);
                this.reports = res.data;
            } catch (e) {
                console.error("Error fetching reports:", e);
                this.error = "Не вдалося завантажити звіти";
            } finally {
                this.isLoading = false;
            }
        },

        async fetchTaxHistory() {
            this.isLoading = true;
            try {
                const res = await api.getTaxHistory();
                this.taxHistory = res.data;
            } catch (e) {
                console.error("Error fetching tax history:", e);
                this.error = "Не вдалося завантажити історію податків";
            } finally {
                this.isLoading = false;
            }
        },

        async syncTaxMonth(year, month) {
            try {
                await api.syncTaxMonth(year, month);
                await this.fetchTaxHistory();
            } catch (e) {
                console.error("Error syncing tax month:", e);
                throw e;
            }
        },

        async syncAllTaxes() {
            try {
                await api.syncAllTaxes();
                await this.fetchTaxHistory();
            } catch (e) {
                console.error("Error syncing all taxes:", e);
                throw e;
            }
        }
    }
});
