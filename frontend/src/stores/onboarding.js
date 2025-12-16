import { defineStore } from 'pinia';
import api from '@/api';
import { supabase } from '@/supabase';

export const useOnboardingStore = defineStore('onboarding', {
  state: () => ({
    currentStep: 1,
    totalSteps: 4,
    userData: {
      isFop: true,
      hasZed: false,
      annualIncome: null,
      employeesCount: 0,
      selectedKveds: [],
      recommendedGroup: 3
    },
    isLoading: false
  }),

  actions: {
    nextStep() { if (this.currentStep < this.totalSteps) this.currentStep++; },
    prevStep() { if (this.currentStep > 1) this.currentStep--; },
    
    // Логіка розрахунку (залишається та сама)
    calculateRecommendation() {
        const { hasZed, annualIncome, employeesCount, selectedKveds } = this.userData;
        if (hasZed) { this.userData.recommendedGroup = 3; return; }
        const LIMIT_GROUP_2 = 5921400;
        if (annualIncome > LIMIT_GROUP_2) { this.userData.recommendedGroup = 3; return; }
        if (employeesCount > 10) { this.userData.recommendedGroup = 3; return; }
        const needsGroup3 = selectedKveds.some(k => k.allowed_fop_groups.length === 1 && k.allowed_fop_groups.includes(3));
        if (needsGroup3) { this.userData.recommendedGroup = 3; return; }
        this.userData.recommendedGroup = 2;
    },

    // НОВА ФУНКЦІЯ: Тільки збереження даних (оновлення)
    async submitOnboarding() {
      this.isLoading = true;
      try {
        // Отримуємо поточного юзера
        const { data: { user } } = await supabase.auth.getUser();
        if (!user) throw new Error("Користувач не знайдений");

        const userId = user.id;

        // 1. Оновлюємо статус ФОП
        await api.updateProfile(userId, {
          is_fop: this.userData.isFop
        });

        // 2. Якщо ФОП -> зберігаємо налаштування
        if (this.userData.isFop) {
          await api.updateFopSettings(userId, {
            fop_group: this.userData.recommendedGroup,
            is_zed: this.userData.hasZed,
            income_tax_percent: this.userData.recommendedGroup === 3 ? 5.0 : 0,
            military_tax_percent: 1.5,
            esv_value: 1760.0
          });
        }
      } catch (error) {
        console.error("Onboarding Save Error:", error);
        throw error;
      } finally {
        this.isLoading = false;
      }
    }
  }
});