import api from './axios';

export default {
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
    getFopSettings(userId) {
        return api.get(`/settings/${userId}`);
    },
    updateFopSettings(userId, data) {
        return api.patch(`/settings/${userId}`, data);
    },
    getTaxRules(year, month) {
        return api.get('/tax/rules', { params: { year, month } });
    }
};
