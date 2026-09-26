<script setup>
import { computed } from 'vue';
import { renderMarkdown } from './renderMarkdown.js';

const props = defineProps({
  content: {
    type: String,
    required: true,
  },
});

const html = computed(() => renderMarkdown(props.content));
</script>

<template>
  <div
    class="chat-md text-sm text-gray-800 [&_h2]:mb-2 [&_h2]:mt-3 [&_h2]:text-base [&_h2]:font-bold [&_h3]:mb-1.5 [&_h3]:mt-2 [&_h3]:text-sm [&_h3]:font-semibold [&_p]:mb-2 [&_p:last-child]:mb-0 [&_ul]:mb-2 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:mb-2 [&_ol]:list-decimal [&_ol]:pl-5 [&_li]:my-0.5 [&_strong]:font-semibold [&_em]:italic [&_a]:text-blue-700 [&_a]:underline [&_code]:rounded [&_code]:bg-gray-200/80 [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-[0.8rem] [&_pre]:mb-2 [&_pre]:overflow-x-auto [&_pre]:rounded-lg [&_pre]:bg-gray-200/80 [&_pre]:p-2 [&_pre]:font-mono [&_pre]:text-[0.8rem] [&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_table]:mb-2 [&_table]:w-full [&_table]:border-collapse [&_table]:text-left [&_th]:border [&_th]:border-gray-300 [&_th]:bg-gray-200/60 [&_th]:px-2 [&_th]:py-1 [&_th]:font-semibold [&_td]:border [&_td]:border-gray-300 [&_td]:px-2 [&_td]:py-1"
    v-html="html"
  />
</template>
