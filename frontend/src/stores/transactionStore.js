import { defineStore } from 'pinia';
import api from '@/api';
import { supabase } from '@/supabase';

export const useTransactionStore = defineStore('transactions', {
  state: () => ({
    transactions: [],
    categories: [], // { income: [], expense: [], all: [] }
    filters: {
      startDate: '',
      endDate: '',
      type: '' // 'income', 'expense' або ''
    },
    summary: {
      totalIncome: 0,
      totalExpense: 0,
      netProfit: 0
    },
    isLoading: false,
    error: null
  }),

  actions: {
    // Отримання даних з урахуванням фільтрів
    async fetchTransactions() {
      this.isLoading = true;
      try {
        const { data: { user } } = await supabase.auth.getUser();
        if (!user) return;

        const params = { limit: 100 }; // Базовий ліміт
        if (this.filters.startDate) params.start_date = this.filters.startDate;
        if (this.filters.endDate) params.end_date = this.filters.endDate;
        if (this.filters.type) params.type = this.filters.type;

        const txRes = await api.getTransactions(user.id, params);
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

    async fetchCategories() {
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) return;
      const catRes = await api.getCategories(user.id);
      this.categories = catRes.data;
    },

    async fetchInitialData() {
      await Promise.all([this.fetchTransactions(), this.fetchCategories()]);
    },

    calculateSummary() {
      let inc = 0;
      let exp = 0;
      this.transactions.forEach(t => {
        const amount = parseFloat(t.transaction_amount);
        if (t.transaction_type === 'income') inc += amount;
        else exp += amount;
      });
      this.summary.totalIncome = inc;
      this.summary.totalExpense = exp;
      this.summary.netProfit = inc - exp;
    },

    async addTransaction(txData) {
      await api.createTransaction(txData);
      await this.fetchTransactions(); 
    },

    async editTransaction(txId, userId, patchData) {
      await api.patchTransaction(txId, userId, patchData);
      await this.fetchTransactions();
    },

    async deleteTransaction(txId, userId) {
      await api.deleteTransaction(txId, userId);
      // Видаляємо локально, щоб не робити зайвий запит
      this.transactions = this.transactions.filter(t => t.transaction_id !== txId);
      this.calculateSummary();
    },

    async createNewCategory(categoryData) {
      // categoryData: { name, type, user_id }
      await api.createCategory(categoryData);
      await this.fetchCategories(); // Оновлюємо список категорій
    },
    
    async removeCategory(catId, userId) {
      await api.deleteCategory(catId, userId);
      await this.fetchCategories();
    }
  }
});