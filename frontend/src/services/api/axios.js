import axios from 'axios';
import { supabase } from '@/services/supabase';

const API_URL = 'http://127.0.0.1:8000';

const instance = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

instance.interceptors.request.use(async (config) => {
    const { data } = await supabase.auth.getSession();
    const token = data?.session?.access_token;

    if (token) {
        config.headers = config.headers || {};
        config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
});

instance.interceptors.response.use(
    (response) => response,
    async (error) => {
        // We use dynamic import to avoid circular dependencies with stores
        const { useNotificationStore } = await import('@/stores/notificationStore');
        const notificationStore = useNotificationStore();

        const status = error.response ? error.response.status : null;
        const detail = error.response?.data?.detail;

        if (status === 401) {
            notificationStore.showError("Сесія завершена. Будь ласка, увійдіть знову.");
        } else if (status === 403) {
            notificationStore.showError("Доступ заборонено.");
        } else if (status === 500) {
            notificationStore.showError("Помилка на сервері. Спробуйте пізніше.");
        } else if (detail) {
            notificationStore.showError(detail);
        } else if (error.message === 'Network Error') {
            notificationStore.showError("Помилка мережі. Перевірте з'єднання.");
        }

        return Promise.reject(error);
    }
);

export default instance;
