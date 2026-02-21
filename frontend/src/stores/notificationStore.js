import { defineStore } from 'pinia';
import { ref } from 'vue';

export const useNotificationStore = defineStore('notification', () => {
    const notifications = ref([]);

    /**
     * Add a notification to the stack
     * @param {Object} notification
     * @param {string} notification.message - The message text
     * @param {'success' | 'error' | 'info' | 'warning'} [notification.type='info'] - Notification type
     * @param {number} [notification.duration=4000] - Duration in ms
     */
    const addNotification = ({ message, type = 'info', duration = 4000 }) => {
        const id = Date.now() + Math.random();
        const newNotification = { id, message, type };
        notifications.value.push(newNotification);

        if (duration > 0) {
            setTimeout(() => {
                removeNotification(id);
            }, duration);
        }
    };

    const removeNotification = (id) => {
        notifications.value = notifications.value.filter(n => n.id !== id);
    };

    const showSuccess = (message) => addNotification({ message, type: 'success' });
    const showError = (message) => addNotification({ message, type: 'error' });
    const showInfo = (message) => addNotification({ message, type: 'info' });
    const showWarning = (message) => addNotification({ message, type: 'warning' });

    return {
        notifications,
        addNotification,
        removeNotification,
        showSuccess,
        showError,
        showInfo,
        showWarning
    };
});
