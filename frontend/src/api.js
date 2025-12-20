import axios from 'axios';

const API_URL = 'http://127.0.0.1:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export default {
  // --- ТРАНЗАКЦІЇ ---
  getTransactions(userId, params = {}) {
    return api.get('/transactions', { params: { user_id: userId, ...params } });
  },
  getTransactionSummary(userId, params = {}) {
    return api.get('/transactions/summary', { params: { user_id: userId, ...params } });
  },
  createTransaction(data) {
    return api.post('/transactions', data);
  },
  deleteTransaction(transactionId, userId) {
    return api.delete(`/transactions/${transactionId}`, {
      params: { user_id: userId }
    });
  },
  patchTransaction(transactionId, userId, data) {
    return api.patch(`/transactions/${transactionId}`, data, {
      params: { user_id: userId }
    });
  },

  // --- КАТЕГОРІЇ ---
  getCategories(userId) {
    return api.get('/categories', { params: { user_id: userId } });
  },
  createCategory(data) {
    return api.post('/categories', data);
  },
  deleteCategory(categoryId, userId) {
    return api.delete(`/categories/${categoryId}`, {
      params: { user_id: userId }
    });
  },

  // --- ПРОФІЛЬ ---
  getProfile(userId) {
    return api.get(`/profile/${userId}`);
  },
  createProfile(data) {
    return api.post('/profile/', data);
  },
  updateProfile(userId, data) {
    return api.patch(`/profile/${userId}`, data);
  },
  deleteProfile(userId) {
    return api.delete(`/profile/${userId}`);
  },

  // --- НАЛАШТУВАННЯ ФОП ---
  getFopSettings(userId) {
    return api.get(`/settings/${userId}`);
  },
  updateFopSettings(userId, data) {
    return api.patch(`/settings/${userId}`, data);
  },

  // === ДОДАЙТЕ ЦІ РЯДКИ, ЩОБ ВИПРАВИТИ ПОМИЛКУ ===
  // Дозволяє викликати api.get, api.post, api.patch напряму з компонентів
  get: (url, config) => api.get(url, config),
  post: (url, data, config) => api.post(url, data, config),
  patch: (url, data, config) => api.patch(url, data, config), // <--- Це виправить помилку
  delete: (url, config) => api.delete(url, config),
};