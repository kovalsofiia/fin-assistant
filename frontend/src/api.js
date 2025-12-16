import axios from 'axios';

const API_URL = 'http://127.0.0.1:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export default {
  getTransactions(userId, params = {}) {
    return api.get('/transactions', { params: { user_id: userId, ...params } });
  },
  createTransaction(data) {
    return api.post('/transactions', data);
  },
  getCategories(userId) {
    return api.get('/categories', { params: { user_id: userId } });
  },
  getProfile(userId) {
    return api.get(`/profile/${userId}`);
  },
  createProfile(data) {
    // data: { user_id: "...", is_fop: true, full_name: "..." }
    return api.post('/profile/', data);
},
  updateProfile(userId, data) {
    return api.patch(`/profile/${userId}`, data);
  },
  getFopSettings(userId) {
    return api.get(`/settings/${userId}`);
  },
  updateFopSettings(userId, data) {
    return api.patch(`/settings/${userId}`, data);
  }
};