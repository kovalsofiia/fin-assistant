<script setup>
defineProps({
  width: {
    type: String,
    default: '100%'
  },
  height: {
    type: String,
    default: '1rem'
  },
  borderRadius: {
    type: String,
    default: '0.5rem'
  },
  className: {
    type: String,
    default: ''
  }
});
</script>

<template>
  <div 
    class="skeleton-loader overflow-hidden bg-gray-200 relative"
    :class="className"
    :style="{ 
      width: width, 
      height: height, 
      borderRadius: borderRadius 
    }"
  >
    <div class="shimmer-wrapper absolute inset-0">
      <div class="shimmer w-full h-full bg-gradient-to-r from-transparent via-white/40 to-transparent"></div>
    </div>
  </div>
</template>

<style scoped>
.shimmer {
  animation: shimmer 1.5s infinite;
  transform: translateX(-100%);
}

@keyframes shimmer {
  100% {
    transform: translateX(100%);
  }
}
</style>
