import api from './axios';

export default {
    sendChatMessage(messages) {
        return api.post('/chat/', { messages });
    },
};
