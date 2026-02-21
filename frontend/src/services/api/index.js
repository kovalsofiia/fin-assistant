import api from './axios';
import transactions from './transactions';
import categories from './categories';
import profiles from './profiles';

export default {
    ...transactions,
    ...categories,
    ...profiles,
    // Direct axios methods for flexibility
    get: (url, config) => api.get(url, config),
    post: (url, data, config) => api.post(url, data, config),
    patch: (url, data, config) => api.patch(url, data, config),
    delete: (url, config) => api.delete(url, config),
};
