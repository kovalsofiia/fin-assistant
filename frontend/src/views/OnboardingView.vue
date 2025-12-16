<script setup>
import { useOnboardingStore } from '@/stores/onboarding';
import StepStatus from '@/components/onboarding/StepStatus.vue';
import StepDetails from '@/components/onboarding/StepDetails.vue';
import StepKved from '@/components/onboarding/StepKved.vue';
import StepResult from '@/components/onboarding/StepResult.vue';

const store = useOnboardingStore();
</script>

<template>
  <div class="onboarding-container">
    <div class="progress-bar">
      <div 
        class="progress-fill" 
        :style="{ width: (store.currentStep / store.totalSteps) * 100 + '%' }"
      ></div>
    </div>

    <div class="step-content">
      <StepStatus v-if="store.currentStep === 1" />
      <StepDetails v-else-if="store.currentStep === 2" />
      <StepKved v-else-if="store.currentStep === 3" />
      <StepResult v-else-if="store.currentStep === 4" />
    </div>

    </div>
</template>

<style scoped>
.onboarding-container { max-width: 600px; margin: 40px auto; padding: 20px; background: white; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.progress-bar { height: 6px; background: #eee; border-radius: 3px; margin-bottom: 30px; overflow: hidden; }
.progress-fill { height: 100%; background: #4CAF50; transition: width 0.3s ease; }
</style>