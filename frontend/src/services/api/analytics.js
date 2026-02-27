import api from './axios';

export default {
    getAnalyticsReports: (userId, period = "monthly", startDate = null, endDate = null) =>
        api.get('/analytics/reports', {
            params: {
                user_id: userId,
                period,
                start_date: startDate,
                end_date: endDate
            }
        }),
    getTaxHistory: (userId) => api.get('/analytics/history/taxes', { params: { user_id: userId } }),
    syncTaxMonth: (userId, year, month) => api.post('/analytics/history/taxes/sync', null, { params: { user_id: userId, year, month } }),
    syncAllTaxes: (userId) => api.post('/analytics/history/taxes/sync_all', null, { params: { user_id: userId } })
};
