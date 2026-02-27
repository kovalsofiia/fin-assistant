<script setup>
import SkeletonLoader from '@/components/common/SkeletonLoader.vue';

defineProps({
  title: {
    type: String,
    required: true
  },
  amount: {
    type: [Number, String],
    required: true
  },
  subtext: {
    type: String,
    default: ''
  },
  // Варіанти: 'primary' (синій градієнт), 'white' (білий фон)
  variant: {
    type: String,
    default: 'white'
  },
  // Колір тексту суми для білих карток: 'blue', 'red', 'default'
  amountColor: {
    type: String,
    default: 'default'
  },
  loading: {
    type: Boolean,
    default: false
  },
  fopAmount: {
    type: [Number, String],
    default: null
  },
  showFopLoading: {
    type: Boolean,
    default: false
  }
});
</script>

<template>
  <div 
    class="rounded-[1.5rem] sm:rounded-2xl shadow-sm p-5 sm:p-6 transition-transform hover:-translate-y-0.5 duration-200 flex flex-col justify-center h-full"
    :class="[
      variant === 'primary' 
        ? 'bg-gradient-to-br from-blue-600 to-blue-700 text-white border-none' 
        : 'bg-white border border-gray-100 text-gray-800'
    ]"
  >
    <!-- Заголовок -->
    <h3 
      class="text-sm font-medium uppercase tracking-wide mb-1"
      :class="variant === 'primary' ? 'text-blue-100' : 'text-gray-500'"
    >
      {{ title }}
    </h3>

    <!-- Сума -->
    <div v-if="loading" class="mt-2 mb-1">
      <SkeletonLoader 
        width="140px" 
        height="36px" 
        :borderRadius="variant === 'primary' ? '12px' : '10px'"
        :className="variant === 'primary' ? 'bg-white/20' : 'bg-gray-100'"
      />
    </div>
    <p 
      v-else
      class="text-3xl font-bold mt-1"
      :class="{
        'text-blue-600': variant === 'white' && amountColor === 'blue',
        'text-red-500': variant === 'white' && amountColor === 'red',
        'text-gray-900': variant === 'white' && amountColor === 'default',
        'text-white': variant === 'primary'
      }"
    >
      {{ amount }}
    </p>

    <!-- Підтекст -->
    <span 
      v-if="subtext" 
      class="text-sm mt-2 block"
      :class="variant === 'primary' ? 'text-blue-200' : 'text-gray-400'"
    >
      {{ subtext }}
    </span>

    <!-- Спеціальне поле для ФОП доходу -->
    <div 
      v-if="fopAmount !== null || (loading && showFopLoading)" 
      class="mt-3 pt-3 border-t border-gray-50 animate-fade-in"
    >
      <p class="text-[11px] font-bold text-blue-500 uppercase tracking-tighter opacity-80 leading-tight">
        Надійшло на ФОП
      </p>
      <div v-if="loading" class="mt-1">
        <SkeletonLoader width="80px" height="16px" borderRadius="6px" />
      </div>
      <p v-else class="text-sm font-black text-gray-700 mt-0.5">
        {{ fopAmount }}
      </p>
    </div>
  </div>
</template>