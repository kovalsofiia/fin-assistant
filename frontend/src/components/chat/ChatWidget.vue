<script setup>
import { nextTick, ref } from 'vue';
import { MessageCircle, X, Send, RotateCcw } from 'lucide-vue-next';
import api from '@/services/api';

// Мають збігатися з backend/routers/chat.py
const MAX_HISTORY = 20;
const MAX_MESSAGE_CHARS = 2000;
const MAX_ASSISTANT_CHARS = 8000; // має збігатися з backend/routers/chat.py
const GREETING = 'Вітаю! Я фінансовий асистент. Запитайте про ваші доходи, витрати, бюджети чи податки.';
const MODEL_STORAGE_KEY = 'chatModel';

const isOpen = ref(false);
const messages = ref([]);
const draft = ref('');
const isLoading = ref(false);
const error = ref('');
const listEl = ref(null);
const models = ref([]);
const selectedModel = ref('');
let modelsLoaded = false;

function readStoredModel() {
    try {
        return localStorage.getItem(MODEL_STORAGE_KEY);
    } catch {
        return null;
    }
}

function rememberModel() {
    try {
        localStorage.setItem(MODEL_STORAGE_KEY, selectedModel.value);
    } catch {
        // localStorage недоступний (приватний режим) — вибір просто не збережеться
    }
}

async function loadModels() {
    if (modelsLoaded) return;
    try {
        const { data } = await api.getChatModels();
        models.value = data.models;
        const stored = readStoredModel();
        selectedModel.value = data.models.includes(stored) ? stored : data.default || '';
        modelsLoaded = true;
    } catch {
        // Без списку моделей чат працює на моделі за замовчуванням
    }
}

function modelLabel(model) {
    return model.split('/').pop();
}

async function scrollToBottom() {
    await nextTick();
    if (listEl.value) listEl.value.scrollTop = listEl.value.scrollHeight;
}

function toggle() {
    isOpen.value = !isOpen.value;
    if (isOpen.value) {
        loadModels();
        scrollToBottom();
    }
}

function reset() {
    messages.value = [];
    error.value = '';
}

async function send() {
    const text = draft.value.trim();
    if (!text || isLoading.value) return;

    messages.value.push({ role: 'user', content: text });
    draft.value = '';
    error.value = '';
    isLoading.value = true;
    scrollToBottom();

    try {
        const payload = messages.value
        .slice(-MAX_HISTORY)
        .map((m) => (m.role === 'assistant' ? { ...m, content: m.content.slice(0, MAX_ASSISTANT_CHARS) } : m));
    const { data } = await api.sendChatMessage(payload, selectedModel.value);
        messages.value.push({ role: 'assistant', content: data.reply });
    } catch (e) {
        // Повертаємо текст у поле, щоб користувач міг повторити без дублювання в історії
        messages.value.pop();
        draft.value = text;
        const detail = e?.response?.data?.detail;
        error.value = typeof detail === 'string' ? detail : 'Не вдалося отримати відповідь. Спробуйте ще раз.';
    } finally {
        isLoading.value = false;
        scrollToBottom();
    }
}
</script>

<template>
  <div>
    <button
      v-if="!isOpen"
      type="button"
      class="fixed bottom-6 right-6 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-blue-600 text-white shadow-lg hover:bg-blue-700"
      aria-label="Відкрити фінансового асистента"
      @click="toggle"
    >
      <MessageCircle class="h-6 w-6" />
    </button>

    <section
      v-else
      class="fixed inset-0 z-50 flex flex-col bg-white sm:inset-auto sm:bottom-6 sm:right-6 sm:h-[32rem] sm:w-96 sm:rounded-2xl sm:border sm:border-gray-200 sm:shadow-2xl"
      aria-label="Фінансовий асистент"
    >
      <header class="flex items-center justify-between border-b border-gray-100 px-4 py-3">
        <div class="flex min-w-0 items-center gap-2">
          <h2 class="font-semibold text-gray-900">Асистент</h2>
          <select
            v-if="models.length > 1"
            v-model="selectedModel"
            class="min-w-0 max-w-[10rem] truncate rounded-lg border border-gray-200 bg-white px-2 py-1 text-xs text-gray-700"
            aria-label="Модель"
            :title="selectedModel"
            @change="rememberModel"
          >
            <option v-for="model in models" :key="model" :value="model">{{ modelLabel(model) }}</option>
          </select>
        </div>
        <div class="flex items-center gap-1">
          <button
            type="button"
            :disabled="isLoading"
            class="rounded p-1.5 text-gray-500 hover:bg-gray-100 disabled:opacity-40"
            aria-label="Почати нову розмову"
            @click="reset"
          >
            <RotateCcw class="h-4 w-4" />
          </button>
          <button type="button" class="rounded p-1.5 text-gray-500 hover:bg-gray-100" aria-label="Закрити" @click="toggle">
            <X class="h-5 w-5" />
          </button>
        </div>
      </header>

      <div ref="listEl" class="flex-1 space-y-3 overflow-y-auto px-4 py-3">
        <p class="rounded-2xl bg-gray-100 px-3 py-2 text-sm text-gray-800">{{ GREETING }}</p>
        <p
          v-for="(message, index) in messages"
          :key="index"
          class="max-w-[85%] whitespace-pre-line rounded-2xl px-3 py-2 text-sm"
          :class="message.role === 'user' ? 'ml-auto bg-blue-600 text-white' : 'bg-gray-100 text-gray-800'"
        >{{ message.content }}</p>
        <p v-if="isLoading" class="text-sm italic text-gray-500">Друкує…</p>
      </div>

      <p v-if="error" class="px-4 pb-2 text-sm text-red-600">{{ error }}</p>

      <form class="flex items-end gap-2 border-t border-gray-100 p-3" @submit.prevent="send">
        <textarea
          v-model="draft"
          rows="1"
          :maxlength="MAX_MESSAGE_CHARS"
          placeholder="Напишіть запитання…"
          class="max-h-32 flex-1 resize-none rounded-xl border border-gray-200 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          @keydown.enter.exact.prevent="send"
        />
        <button
          type="submit"
          :disabled="isLoading || !draft.trim()"
          class="flex h-9 w-9 items-center justify-center rounded-full bg-blue-600 text-white disabled:opacity-40"
          aria-label="Надіслати"
        >
          <Send class="h-4 w-4" />
        </button>
      </form>
    </section>
  </div>
</template>
