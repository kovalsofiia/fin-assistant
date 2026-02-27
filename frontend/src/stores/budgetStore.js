import { defineStore } from 'pinia';
import api from '@/services/api';
import { supabase } from '@/services/supabase';

export const useBudgetStore = defineStore('budgets', {
    state: () => ({
        budgets: [],
        budgetProgress: [],
        reports: null,
        isLoading: false,
        error: null
    }),

    actions: {
        async fetchBudgets() {
            this.isLoading = true;
            try {
                const { data: { user } } = await supabase.auth.getUser();
                if (!user) return;
                const res = await api.getBudgets(user.id);
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
                const { data: { user } } = await supabase.auth.getUser();
                if (!user) return;
                const res = await api.getBudgetsProgress(user.id);
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

        async updateBudget(budgetId, userId, patchData) {
            await api.patchBudget(budgetId, userId, patchData);
            await this.fetchBudgetProgress();
        },

        async deleteBudget(budgetId, userId) {
            await api.deleteBudget(budgetId, userId);
            await this.fetchBudgetProgress();
        },

        async fetchAnalyticsReports(period = 'monthly') {
            this.isLoading = true;
            try {
                const { data: { user } } = await supabase.auth.getUser();
                if (!user) return;
                const res = await api.getAnalyticsReports(user.id, period);
                this.reports = res.data;
            } catch (e) {
                console.error("Error fetching reports:", e);
                this.error = "Не вдалося завантажити звіти";
            } finally {
                this.isLoading = false;
            }
        }
    }
});
