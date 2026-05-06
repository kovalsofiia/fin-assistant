import api from './axios';

export default {
    getCategories() {
        return api.get('/categories');
    },
    createCategory(data) {
        return api.post('/categories', data);
    },
    deleteCategory(categoryId) {
        return api.delete(`/categories/${categoryId}`);
    },
    updateCategory(categoryId, data) {
        return api.patch(`/categories/${categoryId}`, data);
    }
};
