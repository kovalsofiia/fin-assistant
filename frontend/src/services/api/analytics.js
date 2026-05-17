import api from './axios';

export default {
    getAnalyticsReports: (period = "monthly", startDate = null, endDate = null) =>
        api.get('/analytics/reports', {
            params: {
                period,
                start_date: startDate,
                end_date: endDate
            }
        }),
    getTaxHistory: () => api.get('/analytics/history/taxes'),
    getBehaviorInsights: (startDate, endDate) =>
        api.get('/analytics/insights', {
            params: {
                start_date: startDate,
                end_date: endDate
            }
        }),
    syncTaxMonth: (year, month) => api.post('/analytics/history/taxes/sync', null, { params: { year, month } }),
    syncAllTaxes: () => api.post('/analytics/history/taxes/sync_all'),
    exportCsv: (exportType, params = {}) =>
        api.get('/analytics/export/csv', {
            params: { export_type: exportType, ...params },
            responseType: 'blob',
        }),
};
