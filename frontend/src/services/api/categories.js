import api from './axios';

export default {
    getCategories(userId) {
        return api.get('/categories', { params: { user_id: userId } });
    },
    createCategory(data) {
        return api.post('/categories', data);
    },
    deleteCategory(categoryId, userId) {
        return api.delete(`/categories/${categoryId}`, {
            params: { user_id: userId }
        });
    },
    updateCategory(categoryId, userId, data) {
        return api.patch(`/categories/${categoryId}`, data, {
            params: { user_id: userId }
        });
    }
};
