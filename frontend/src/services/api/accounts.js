import api from './axios';

export default {
    getAccounts(params = {}) {
        return api.get('/accounts', { params });
    },
    createAccount(data) {
        return api.post('/accounts', data);
    },
    updateAccount(accountId, data) {
        return api.patch(`/accounts/${accountId}`, data);
    },
    deleteAccount(accountId) {
        return api.delete(`/accounts/${accountId}`);
    },
};
