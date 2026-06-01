import { defineStore } from 'pinia';
import api from '@/services/api';
import { supabase } from '@/services/supabase';
import { getMonthRange } from '@/utils/dateUtils';
import { getCategoryName } from '@/utils/format';
import { useAccountStore } from '@/stores/accountStore';

export const useTransactionStore = defineStore('transactions', {
  state: () => {
    // ... (rest of state remains the same)
    const { start, end } = getMonthRange();
    let savedFilters = {
      startDate: start,
      endDate: end,
      type: '',
      categoryId: '',
      period: 'this_month',
      searchText: ''
    };

    try {
      const stored = localStorage.getItem('transaction_filters');
      if (stored) {
        const parsed = JSON.parse(stored);
        // Ensure we don't restore invalid NaN dates
        if (parsed.startDate && parsed.startDate.includes('NaN')) delete parsed.startDate;
        if (parsed.endDate && parsed.endDate.includes('NaN')) delete parsed.endDate;

        savedFilters = { ...savedFilters, ...parsed };
      }
    } catch (e) {
      console.error("Error parsing saved filters:", e);
    }

    return {
      transactions: [],
      categories: { income: [], expense: [], all: [] },
      filters: savedFilters,
      summary: {
        totalIncome: 0,
        totalFopIncome: 0,
        totalExpense: 0,
        netProfit: 0
      },
      lifetimeSummary: {
        totalIncome: 0,
        totalExpense: 0,
        balance: 0,
        monthsCount: 0
      },
      isLoading: false,
      error: null
    };
  },

  actions: {
    // Utilities are now imported
    getMonthRange,

    getCategoryName(id) {
      return getCategoryName(id, this.categories.all);
    },

    // Отримання даних з урахуванням фільтрів
    async fetchTransactions(filterOverride = null) {
      this.isLoading = true;
      try {
        const { data: { user } } = await supabase.auth.getUser();
        if (!user) return;

        const effectiveFilters = filterOverride || this.filters;
        const params = { limit: 100 }; // Базовий ліміт

        if (effectiveFilters.startDate) params.start_date = effectiveFilters.startDate;
        if (effectiveFilters.endDate) params.end_date = effectiveFilters.endDate;
        if (effectiveFilters.type) params.type = effectiveFilters.type;
        if (effectiveFilters.categoryId) params.category_id = effectiveFilters.categoryId;
        if (effectiveFilters.searchText) params.search = effectiveFilters.searchText;

        // Save filters to localStorage only if they are the main filters
        if (!filterOverride) {
          localStorage.setItem('transaction_filters', JSON.stringify(this.filters));
        }

        const txRes = await api.getTransactions(params);
        this.transactions = txRes.data;

        // Перераховуємо суми (тільки для відображених транзакцій)
        this.calculateSummary();
      } catch (e) {
        console.error("Error fetching transactions:", e);
        this.error = "Не вдалося завантажити транзакції";
      } finally {
        this.isLoading = false;
      }
    },

    async fetchLifetimeSummary(endDateOverride = null) {
      try {
        const { data: { user } } = await supabase.auth.getUser();
        if (!user) return;

        const params = {};
        const effectiveEndDate = endDateOverride || this.filters.endDate;
        if (effectiveEndDate) params.end_date = effectiveEndDate;

        const summaryRes = await api.getTransactionSummary(params);
        this.lifetimeSummary = summaryRes.data;
      } catch (e) {
        console.error("Error fetching lifetime summary:", e);
      }
    },

    async fetchCategories() {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return;
      const catRes = await api.getCategories();
      this.categories = catRes.data;
    },

    async fetchInitialData(filterOverride = null) {
      const accountStore = useAccountStore();
      await Promise.all([
        this.fetchTransactions(filterOverride),
        this.fetchCategories(),
        this.fetchLifetimeSummary(filterOverride?.endDate),
        accountStore.fetchAccounts(),
      ]);
    },

    calculateSummary() {
      let inc = 0;
      let fopInc = 0;
      let exp = 0;
      this.transactions.forEach(t => {
        const amount = parseFloat(t.transaction_amount);
        const isFop = t.is_fop !== false; // Default to true if missing

        if (t.transaction_type === 'income') {
          inc += amount;
          if (isFop) fopInc += amount;
        } else {
          exp += amount;
        }
      });
      this.summary.totalIncome = inc;
      this.summary.totalFopIncome = fopInc;
      this.summary.totalExpense = exp;
      this.summary.netProfit = inc - exp;
    },

    async addTransaction(txData) {
      await api.createTransaction(txData);
      await this.fetchTransactions();
    },

    async editTransaction(txId, _userId, patchData) {
      await api.patchTransaction(txId, patchData);
      await this.fetchTransactions();
    },

    async deleteTransaction(txId, _userId) {
      await api.deleteTransaction(txId);
      // Видаляємо локально, щоб не робити зайвий запит
      this.transactions = this.transactions.filter(t => t.transaction_id !== txId);
      this.calculateSummary();
    },

    async createNewCategory(categoryData) {
      // categoryData: { name, type, user_id, is_fop_only }
      await api.createCategory(categoryData);
      await this.fetchCategories(); // Оновлюємо список категорій
    },

    async modifyCategory(catId, userId, updateData) {
      await api.updateCategory(catId, updateData);
      await this.fetchCategories();
    },

    async removeCategory(catId, userId) {
      await api.deleteCategory(catId);
      await this.fetchCategories();
    }
  }
});