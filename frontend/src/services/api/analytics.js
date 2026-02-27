import api from './axios';

export default {
    getAnalyticsReports: (userId, period = "monthly") => api.get('/analytics/reports', { params: { user_id: userId, period } })
};
