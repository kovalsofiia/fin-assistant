import api from './axios';

export default {
    getBudgets: (userId) => api.get('/budgets/', { params: { user_id: userId } }),
    getBudgetsProgress: (userId) => api.get('/budgets/progress', { params: { user_id: userId } }),
    createBudget: (data) => api.post('/budgets/', data),
    patchBudget: (budgetId, userId, data) => api.patch(`/budgets/${budgetId}`, data, { params: { user_id: userId } }),
    deleteBudget: (budgetId, userId) => api.delete(`/budgets/${budgetId}`, { params: { user_id: userId } }),
};
