<script setup>
import { computed } from 'vue';
import { User, Check } from 'lucide-vue-next';

const props = defineProps({
  modelValue: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['update:modelValue']);

// Using computed to create a writable proxy for v-model binding
const profile = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
});
</script>

<template>
  <section class="bg-white rounded-[2rem] sm:rounded-3xl shadow-xl shadow-gray-200/50 border border-gray-100 p-6 sm:p-8 transition-shadow hover:shadow-2xl hover:shadow-gray-200">
    <div class="flex items-center gap-4 mb-8">
      <div class="bg-blue-600 p-3 rounded-2xl text-white shadow-lg shadow-blue-200">
        <User :size="24" stroke-width="2.5" />
      </div>
      <h2 class="text-2xl font-black text-gray-900">Профіль</h2>
    </div>
    
    <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
      <div class="flex flex-col gap-2">
        <label class="text-sm font-black text-gray-400 uppercase tracking-widest">Повне ім'я</label>
        <input 
          type="text" 
          v-model="profile.full_name" 
          class="px-5 py-4 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-2xl outline-none transition-all font-bold text-gray-800 placeholder:text-gray-300 shadow-inner" 
          placeholder="Ваше Прізвище та Ім'я"
        >
      </div>
      
      <div class="flex items-center">
        <label class="flex items-center gap-6 p-6 bg-gray-50 hover:bg-white rounded-3xl border border-gray-100 cursor-pointer shadow-sm hover:shadow-md transition-all group w-full">
          <div class="relative w-8 h-8 shrink-0">
            <input type="checkbox" v-model="profile.is_fop" class="peer appearance-none w-8 h-8 border-2 border-gray-200 checked:bg-blue-600 checked:border-blue-600 rounded-xl transition-all shadow-inner">
            <div class="absolute inset-0 flex items-center justify-center text-white opacity-0 peer-checked:opacity-100 pointer-events-none transition-all scale-50 peer-checked:scale-100">
              <Check :size="20" stroke-width="4" />
            </div>
          </div>
          <div>
            <span class="block font-black text-gray-900 text-lg group-hover:text-blue-600 transition-colors">Я використовую ФОП</span>
            <span class="text-xs text-gray-500 font-medium">Активує податкові інструменти та податкові розрахунки</span>
          </div>
        </label>
      </div>
    </div>
  </section>
</template>
