<script setup>
import { ref } from 'vue';
import { ChevronDown } from 'lucide-vue-next';

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  defaultOpen: {
    type: Boolean,
    default: false
  }
});

const isOpen = ref(props.defaultOpen);

const toggle = () => {
  isOpen.value = !isOpen.value;
};
</script>

<template>
  <section class="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
    <button
      type="button"
      class="w-full flex items-center justify-between gap-3 p-4 text-left hover:bg-gray-50/80 transition-colors"
      :aria-expanded="isOpen"
      @click="toggle"
    >
      <div class="min-w-0 flex-1">
        <p class="text-[10px] font-black uppercase tracking-widest text-gray-400 leading-none">
          {{ title }}
        </p>
        <div class="mt-1.5">
          <slot name="summary" />
        </div>
      </div>
      <ChevronDown
        class="w-5 h-5 text-gray-400 shrink-0 transition-transform duration-200"
        :class="{ 'rotate-180': isOpen }"
        aria-hidden="true"
      />
    </button>

    <div
      v-show="isOpen"
      class="border-t border-gray-100 px-4 pb-4 pt-3"
    >
      <slot />
    </div>
  </section>
</template>
