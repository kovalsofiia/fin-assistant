import api from './axios';

export default {
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
    deleteTransactionsBatch(userId, transactionIds) {
        return api.delete('/transactions/batch/delete', {
            data: { user_id: userId, transaction_ids: transactionIds }
        });
    }
};
