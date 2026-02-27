import api from './axios';
import transactions from './transactions';
import categories from './categories';
import profiles from './profiles';
import budgets from './budgets';
import analytics from './analytics';

export default {
    ...transactions,
    ...categories,
    ...profiles,
    ...budgets,
    ...analytics,
    // Direct axios methods for flexibility
    get: (url, config) => api.get(url, config),
    post: (url, data, config) => api.post(url, data, config),
    patch: (url, data, config) => api.patch(url, data, config),
    delete: (url, config) => api.delete(url, config),
};
