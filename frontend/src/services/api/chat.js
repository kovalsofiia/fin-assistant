import api from './axios';

export default {
    getChatModels() {
        return api.get('/chat/models');
    },
    sendChatMessage(messages, model) {
        return api.post('/chat/', { messages, model: model || null });
    },
};
