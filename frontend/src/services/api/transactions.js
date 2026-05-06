import api from './axios';

export default {
    getTransactions(params = {}) {
        return api.get('/transactions', { params });
    },
    getTransactionSummary(params = {}) {
        return api.get('/transactions/summary', { params });
    },
    createTransaction(data) {
        return api.post('/transactions', data);
    },
    deleteTransaction(transactionId) {
        return api.delete(`/transactions/${transactionId}`);
    },
    patchTransaction(transactionId, data) {
        return api.patch(`/transactions/${transactionId}`, data);
    }
};
