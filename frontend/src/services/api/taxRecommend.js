import api from './axios';

export default {
    getFopGroupRecommend(params = {}) {
        return api.get('/tax/recommend', { params });
    },
};
