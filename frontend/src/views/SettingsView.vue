<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/services/api'; 
import { supabase } from '@/services/supabase';
import { Save, Loader2, ClipboardList } from 'lucide-vue-next';
import { useTaxRulesStore } from '@/stores/taxRulesStore';
import { APP_CONSTANTS } from '@/constants/appConstants';
import { useTransactionStore } from '@/stores/transactionStore';
import { useNotificationStore } from '@/stores/notificationStore';

// Components
import CategoryManager from '@/components/settings/CategoryManager.vue';
import AccountManager from '@/components/settings/AccountManager.vue';
import ProfileForm from '@/components/settings/ProfileForm.vue';
import FopSettingsForm from '@/components/settings/FopSettingsForm.vue';
import KvedSelector from '@/components/settings/KvedSelector.vue';
import {
  getStoredKveds,
  setStoredKveds,
  toKvedSyncPayload,
} from '@/utils/kvedStorage';

const txStore = useTransactionStore();
const taxRulesStore = useTaxRulesStore();
const router = useRouter();

function goTaxRulesAdmin() {
  router.push({ name: 'admin-tax-rules' });
}
const notificationStore = useNotificationStore();

const isLoading = ref(false);
const isSaving = ref(false);
const userId = ref(null);

const isKvedModalOpen = ref(false);

const profile = ref({
  full_name: '',
  is_fop: true
});

const fopSettings = ref({
  fop_group: 3,
  is_zed: false,
  income_tax_percent: APP_CONSTANTS.TAX_DEFAULTS.INCOME_TAX_G3,
  esv_value: APP_CONSTANTS.TAX_DEFAULTS.ESV_VALUE,
  esv_covered_by_primary_employment: false,
  military_tax_percent: APP_CONSTANTS.TAX_DEFAULTS.MILITARY_TAX_PERCENT,
  tax_system: 'simplified',
  activity_type: 'services',
  has_employees: false,
  employees_count: 0,
  is_vat_payer: false,
  land_area_ha: 0,
  normative_land_value: 0,
  single_tax_value: 0,
  military_tax_value: 0,
  registration_date: ''
});

const userKveds = ref([]);

const loadData = async () => {
  isLoading.value = true;
  try {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) {
      router.push('/');
      return;
    }
    userId.value = user.id;

    try {
      const profileRes = await api.getProfile(userId.value);
      profile.value = profileRes.data;
    } catch (e) {
      console.warn("Profile not found or error", e);
    }

    await taxRulesStore.checkAdmin();

    if (profile.value.is_fop) {
      try {
        const [settingsRes, rules] = await Promise.all([
          api.getFopSettings(userId.value),
          taxRulesStore.fetchRules(new Date().getFullYear(), new Date().getMonth() + 1)
        ]);

        if (settingsRes.data) {
          fopSettings.value = {
            fop_group: settingsRes.data.fop_group,
            is_zed: settingsRes.data.is_zed,
            income_tax_percent: settingsRes.data.income_tax_percent,
            esv_value: settingsRes.data.esv_value,
            esv_covered_by_primary_employment: !!(settingsRes.data.esv_covered_by_primary_employment),
            military_tax_percent: settingsRes.data.military_tax_percent,
            tax_system: settingsRes.data.tax_system || 'simplified',
            activity_type: settingsRes.data.activity_type || 'services',
            has_employees: settingsRes.data.has_employees || false,
            employees_count: settingsRes.data.employees_count || 0,
            is_vat_payer: settingsRes.data.is_vat_payer || false,
            land_area_ha: settingsRes.data.land_area_ha || 0,
            normative_land_value: settingsRes.data.normative_land_value || 0,
            registration_date: settingsRes.data.registration_date || ''
          };
          
          const group = parseInt(fopSettings.value.fop_group);
          if (group === 1) {
            fopSettings.value.single_tax_value = rules.single_tax_g1;
            fopSettings.value.military_tax_value = rules.fixed_military_tax;
          } else if (group === 2) {
            fopSettings.value.single_tax_value = rules.single_tax_g2;
            fopSettings.value.military_tax_value = rules.fixed_military_tax;
          } else if (group === 4) {
            fopSettings.value.military_tax_value = rules.fixed_military_tax;
          }
        }
      } catch (e) {
        console.warn("Settings or rules not found, using defaults", e);
      }
    }

    const stored = getStoredKveds(userId.value);
    try {
      const kvedRes = await api.getMyKveds();
      const fromApi = kvedRes.data?.kveds || [];
      if (fromApi.length) {
        userKveds.value = fromApi.map((k) => {
          const local = stored.find((s) => s.code === k.code);
          return { code: k.code, name: k.name || local?.name || '' };
        });
        setStoredKveds(userId.value, userKveds.value);
      } else if (stored.length) {
        userKveds.value = stored;
        try {
          await api.syncMyKveds(toKvedSyncPayload(stored));
        } catch (syncErr) {
          console.warn('KVED backfill to DB failed', syncErr);
        }
      }
    } catch (e) {
      if (stored.length) {
        userKveds.value = stored;
      }
      console.warn('KVED from API not loaded', e);
    }

    await txStore.fetchCategories();

  } catch (error) {
    console.error("Critical load error:", error);
    notificationStore.showError("Не вдалося завантажити дані");
  } finally {
    isLoading.value = false;
  }
};

const saveChanges = async () => {
  if (!userId.value) return;
  
  const group = parseInt(fopSettings.value.fop_group);
  if ((group === 1 || group === 4) && fopSettings.value.has_employees) {
    notificationStore.showError("Для 1-ї та 4-ї груп наймана праця заборонена");
    return;
  }
  if (group === 2 && fopSettings.value.employees_count > 10) {
    notificationStore.showError("Для 2-ї групи ліміт — 10 працівників");
    return;
  }
  if (fopSettings.value.employees_count < 0) {
    notificationStore.showError("Кількість працівників не може бути від'ємною");
    return;
  }

  isSaving.value = true;

  try {
    await api.updateProfile(userId.value, {
      full_name: profile.value.full_name,
      is_fop: profile.value.is_fop
    });

    if (profile.value.is_fop) {
      await api.updateFopSettings(userId.value, {
        fop_group: fopSettings.value.fop_group,
        is_zed: fopSettings.value.is_zed,
        income_tax_percent: fopSettings.value.income_tax_percent,
        esv_value: fopSettings.value.esv_value,
        esv_covered_by_primary_employment:
          parseInt(fopSettings.value.fop_group) === 3
            ? !!fopSettings.value.esv_covered_by_primary_employment
            : false,
        military_tax_percent: fopSettings.value.military_tax_percent,
        tax_system: fopSettings.value.tax_system,
        activity_type: fopSettings.value.activity_type,
        has_employees: fopSettings.value.has_employees,
        employees_count: fopSettings.value.employees_count,
        is_vat_payer: fopSettings.value.is_vat_payer,
        land_area_ha: fopSettings.value.land_area_ha,
        normative_land_value: fopSettings.value.normative_land_value,
        registration_date: fopSettings.value.registration_date || null
      });
    }

    setStoredKveds(userId.value, userKveds.value);

    if (userKveds.value?.length) {
      try {
        await api.syncMyKveds(toKvedSyncPayload(userKveds.value));
      } catch (kvedErr) {
        const kvedMsg =
          kvedErr.response?.data?.detail ||
          'КВЕД збережено локально, але не синхронізовано з сервером';
        notificationStore.showError(
          typeof kvedMsg === 'string' ? kvedMsg : 'Помилка синхронізації КВЕД'
        );
        return;
      }
    } else {
      try {
        await api.syncMyKveds([]);
      } catch {
        /* порожній список — ігноруємо */
      }
    }

    notificationStore.showSuccess("Налаштування успішно збережено");
  } catch (error) {
    console.error(error);
    const errorMsg = error.response?.data?.detail || "Помилка при збереженні";
    notificationStore.showError(errorMsg);
  } finally {
    isSaving.value = false;
  }
};

onMounted(() => {
  loadData();
});
</script>

<template>
  <div class="max-w-4xl mx-auto p-4 sm:p-8 animate-fade-in font-sans">
    <header class="mb-8 sm:mb-10 flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
      <div class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between w-full">
        <div>
          <h1 class="text-3xl sm:text-4xl font-black text-gray-900 tracking-tight mb-2">Налаштування</h1>
          <p class="text-gray-500 font-medium font-bold">Керування профілем та податковими параметрами</p>
        </div>
        <div class="flex flex-wrap gap-2 shrink-0">
          <button
            v-if="profile.is_fop"
            type="button"
            class="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-2xl bg-indigo-600 text-white font-black text-sm hover:bg-indigo-700 shadow-lg shadow-indigo-200 transition-all"
            @click="router.push({ path: '/analytics', query: { tab: 'fop_group' } })"
          >
            <ClipboardList :size="18" stroke-width="2.5" />
            Рекомендація групи ФОП
          </button>
          <button
            v-if="taxRulesStore.isAdmin"
            type="button"
            class="inline-flex items-center justify-center gap-2 px-5 py-3 rounded-2xl bg-slate-800 text-white font-black text-sm hover:bg-slate-900 transition-all"
            @click="goTaxRulesAdmin"
          >
            Податкові правила (адмін)
          </button>
        </div>
      </div>
    </header>

    <div v-if="isLoading" class="py-24 text-center">
      <Loader2 class="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
      <p class="text-gray-500 font-bold uppercase tracking-widest text-xs">Завантаження...</p>
    </div>

    <form v-else @submit.prevent="saveChanges" class="space-y-8">
      
      <!-- Card: Profile -->
      <ProfileForm v-model="profile" />

      <AccountManager v-if="userId" />

      <!-- Card: Category Management -->
      <CategoryManager 
        v-if="userId" 
        :userId="userId" 
      />
      
      <!-- Card: Tax Settings (Only if FOP) -->
      <FopSettingsForm 
        v-if="profile.is_fop" 
        v-model="fopSettings" 
        v-model:userKveds="userKveds"
        @openKvedModal="isKvedModalOpen = true"
      />

      <!-- Action Buttons -->
      <footer class="sticky bottom-4 sm:bottom-8 z-40 flex flex-col sm:flex-row items-center justify-between gap-4 p-4 sm:p-6 bg-white/80 backdrop-blur-xl border-2 border-gray-100 rounded-[2rem] sm:rounded-3xl shadow-2xl shadow-gray-300">
        <div class="text-gray-400 font-black text-[10px] uppercase tracking-[0.2em] order-2 sm:order-1">
          {{ isSaving ? 'Узгодження даних...' : 'Готовий до збереження' }}
        </div>
        <button 
          type="submit" 
          :disabled="isSaving" 
          class="w-full sm:w-auto px-10 py-4 sm:py-5 bg-blue-600 text-white rounded-2xl font-black text-lg hover:bg-blue-700 disabled:opacity-70 shadow-2xl shadow-blue-200 transition-all active:scale-95 flex items-center justify-center gap-4 order-1 sm:order-2"
        >
          <Loader2 v-if="isSaving" class="animate-spin" :size="24" />
          <Save v-else :size="24" />
          {{ isSaving ? 'Збереження...' : 'Зберегти зміни' }}
        </button>
      </footer>
    </form>

    <!-- KVED Selection Modal -->
    <KvedSelector 
      :isOpen="isKvedModalOpen" 
      v-model:userKveds="userKveds"
      @close="isKvedModalOpen = false"
    />
  </div>
</template>

<style scoped>
.animate-fade-in { animation: fadeIn 0.6s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
</style>