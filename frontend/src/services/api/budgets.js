import api from './axios';

export default {
    getBudgets: () => api.get('/budgets/'),
    getBudgetsProgress: () => api.get('/budgets/progress'),
    createBudget: (data) => api.post('/budgets/', data),
    patchBudget: (budgetId, data) => api.patch(`/budgets/${budgetId}`, data),
    deleteBudget: (budgetId) => api.delete(`/budgets/${budgetId}`),
};
