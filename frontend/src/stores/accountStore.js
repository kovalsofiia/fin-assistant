import { defineStore } from 'pinia';
import api from '@/services/api';

export const useAccountStore = defineStore('accounts', {
  state: () => ({
    accounts: [],
    isLoading: false,
    error: null,
  }),

  getters: {
    businessAccounts: (state) => state.accounts.filter((a) => a.is_business),
    personalAccounts: (state) => state.accounts.filter((a) => !a.is_business),
    accountById: (state) => (id) => state.accounts.find((a) => a.id === id),
  },

  actions: {
    async fetchAccounts(includeInactive = false) {
      this.isLoading = true;
      this.error = null;
      try {
        const res = await api.getAccounts({
          include_inactive: includeInactive,
        });
        this.accounts = res.data || [];
      } catch (e) {
        console.error('Error fetching accounts:', e);
        this.error =
          e.response?.data?.detail || 'Не вдалося завантажити рахунки';
        this.accounts = [];
      } finally {
        this.isLoading = false;
      }
    },

    async createAccount(data) {
      await api.createAccount(data);
      await this.fetchAccounts();
    },

    async updateAccount(accountId, data) {
      await api.updateAccount(accountId, data);
      await this.fetchAccounts();
    },

    async removeAccount(accountId) {
      await api.deleteAccount(accountId);
      await this.fetchAccounts();
    },
  },
});
