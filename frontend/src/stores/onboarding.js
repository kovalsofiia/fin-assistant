import { defineStore } from 'pinia';
import api from '@/services/api';
import { supabase } from '@/services/supabase';
import { useTaxRulesStore } from '@/stores/taxRulesStore';

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
    async calculateRecommendation() {
      const { hasZed, annualIncome, employeesCount, selectedKveds } = this.userData;
      if (hasZed) { this.userData.recommendedGroup = 3; return; }

      const taxRulesStore = useTaxRulesStore();
      const rules = await taxRulesStore.fetchRules(new Date().getFullYear(), new Date().getMonth() + 1);

      const LIMIT_GROUP_2 = rules.limit_g2 || 5920000;
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
          const taxRulesStore = useTaxRulesStore();
          const rules = await taxRulesStore.fetchRules(new Date().getFullYear(), new Date().getMonth() + 1);

          await api.updateFopSettings(userId, {
            fop_group: this.userData.recommendedGroup,
            is_zed: this.userData.hasZed,
            income_tax_percent: this.userData.recommendedGroup === 3 ? (rules.income_tax_percent || APP_CONSTANTS.TAX_DEFAULTS.INCOME_TAX_G3) : 0,
            military_tax_percent: this.userData.recommendedGroup === 3 ? (rules.military_tax_percent || APP_CONSTANTS.TAX_DEFAULTS.MILITARY_TAX_PERCENT) : 0,
            esv_value: rules.esv_value || APP_CONSTANTS.TAX_DEFAULTS.ESV_VALUE
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