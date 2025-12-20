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
  }
});
</script>

<template>
  <div 
    class="rounded-xl shadow-sm p-6 transition-transform hover:-translate-y-0.5 duration-200 flex flex-col justify-center h-full"
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
  </div>
</template>