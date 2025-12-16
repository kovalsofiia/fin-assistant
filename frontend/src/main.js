import { createApp } from 'vue';
import { createPinia } from 'pinia'; // Імпорт Pinia
import App from './App.vue';
import router from './router'; // Імпорт нашого роутера

const app = createApp(App);

app.use(createPinia()); // Підключаємо Store
app.use(router);        // Підключаємо Router

app.mount('#app');