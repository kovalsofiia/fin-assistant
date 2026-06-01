import api from './axios';

export default {
    getKvedRestrictions() {
        return api.get('/kveds/restrictions');
    },
    getMyKveds() {
        return api.get('/kveds/me');
    },
    syncMyKveds(kveds) {
        return api.put('/kveds/me', { kveds });
    },
};
