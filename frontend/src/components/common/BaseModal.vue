<script setup>
import { X } from 'lucide-vue-next';

defineProps({
  isOpen: {
    type: Boolean,
    required: true
  },
  title: {
    type: String,
    default: 'Вікно'
  }
});

const emit = defineEmits(['close']);

const close = () => {
  emit('close');
};
</script>

<template>
  <Teleport to="body">
    <transition
      enter-active-class="transition duration-300 ease-out"
      enter-from-class="opacity-0 scale-95"
      enter-to-class="opacity-100 scale-100"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="opacity-100 scale-100"
      leave-to-class="opacity-0 scale-95"
    >
      <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/40 backdrop-blur-sm" @click.self="close">
        <div class="bg-white rounded-[2.5rem] w-full max-w-lg shadow-2xl shadow-blue-900/10 overflow-hidden border border-gray-100 flex flex-col max-h-[90vh]">
          <header class="px-8 py-6 border-b border-gray-50 flex justify-between items-center bg-white/50 backdrop-blur-md sticky top-0 z-10">
            <h3 class="text-xl font-black text-gray-900 tracking-tight">{{ title }}</h3>
            <button 
              class="p-2 hover:bg-gray-100 rounded-2xl text-gray-400 hover:text-gray-900 transition-all active:scale-95" 
              @click="close"
            >
              <X :size="24" stroke-width="3" />
            </button>
          </header>
          
          <div class="p-8 overflow-y-auto">
            <slot></slot>
          </div>
          
          <footer class="px-8 py-6 border-t border-gray-50 flex justify-end gap-3 bg-gray-50/50" v-if="$slots.footer">
            <slot name="footer"></slot>
          </footer>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<style scoped>
/* No extra scoped CSS needed thanks to Tailwind and Transition */
</style>