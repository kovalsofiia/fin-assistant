import { createApp } from 'vue'
import { createPinia } from 'pinia' // якщо використовуєте pinia
import App from './App.vue'
import router from './router'

// ДОДАЙТЕ ЦЕЙ РЯДОК (шлях має відповідати розташуванню файлу)
import './assets/main.css' 

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.mount('#app')