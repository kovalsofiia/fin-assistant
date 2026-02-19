<script setup>
  
import { ref, onMounted, watch, computed } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/services/api'; 
import { supabase } from '@/services/supabase';
import BaseModal from '../components/common/BaseModal.vue'; 
import { KVED_SECTIONS } from '../constants/kveds';
import { APP_CONSTANTS } from '../constants/appConstants';
import { 
  User, 
  Briefcase, 
  Plus, 
  X, 
  Search, 
  ChevronDown, 
  ChevronRight, 
  Check,
  Save,
  Loader2
} from 'lucide-vue-next';
import { useTaxRulesStore } from '../stores/taxRulesStore';

const taxRulesStore = useTaxRulesStore();
const router = useRouter();
const isLoading = ref(false);
const isSaving = ref(false);
const message = ref({ text: '', type: '' }); // type: 'success' | 'error'
const userId = ref(null);

// Стан модального вікна КВЕДів
const isKvedModalOpen = ref(false);
const kvedSearch = ref('');
const openSections = ref({});

// Стан профілю
const profile = ref({
  full_name: '',
  is_fop: true
});

// Стан налаштувань ФОП
const fopSettings = ref({
  fop_group: 3,
  is_zed: false,
  income_tax_percent: 5,
  esv_value: 1760,
  military_tax_percent: 1,
  tax_system: 'simplified',
  activity_type: 'services',
  has_employees: false,
  employees_count: 0,
  is_vat_payer: false,
  land_area_ha: 0,
  normative_land_value: 0,
  single_tax_value: 0,
  military_tax_value: 0
});

// Локальний стан для КВЕДів
const userKveds = ref([]);

// --- API Methods ---

const loadData = async () => {
  isLoading.value = true;
  try {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) {
      router.push('/');
      return;
    }
    userId.value = user.id;

    // 1. Отримуємо профіль
    try {
      const profileRes = await api.getProfile(userId.value);
      profile.value = profileRes.data;
    } catch (e) {
      console.warn("Profile not found or error", e);
    }

    // 2. Отримуємо налаштування ФОП (тільки якщо користувач є ФОП)
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
            military_tax_percent: settingsRes.data.military_tax_percent,
            tax_system: settingsRes.data.tax_system || 'simplified',
            activity_type: settingsRes.data.activity_type || 'services',
            has_employees: settingsRes.data.has_employees || false,
            employees_count: settingsRes.data.employees_count || 0,
            is_vat_payer: settingsRes.data.is_vat_payer || false,
            land_area_ha: settingsRes.data.land_area_ha || 0,
            normative_land_value: settingsRes.data.normative_land_value || 0
          };
          
          // Ініціалізуємо суми на основі групи та ПРАВИЛ з бази
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

    // 3. Завантажуємо локальні КВЕДи
    const storedKveds = localStorage.getItem(`kveds_${userId.value}`);
    if (storedKveds) {
      userKveds.value = JSON.parse(storedKveds);
    }

  } catch (error) {
    console.error("Critical load error:", error);
    showMessage("Не вдалося завантажити дані", 'error');
  } finally {
    isLoading.value = false;
  }
};

const saveChanges = async () => {
  if (!userId.value) return;
  
  // Валідація найманих працівників
  const group = parseInt(fopSettings.value.fop_group);
  if ((group === 1 || group === 4) && fopSettings.value.has_employees) {
    showMessage("Для 1-ї та 4-ї груп наймана праця заборонена", 'error');
    return;
  }
  if (group === 2 && fopSettings.value.employees_count > 10) {
    showMessage("Для 2-ї групи ліміт — 10 працівників", 'error');
    return;
  }
  if (fopSettings.value.employees_count < 0) {
    showMessage("Кількість працівників не може бути від'ємною", 'error');
    return;
  }

  isSaving.value = true;
  message.value.text = '';

  try {
    // 1. Оновлюємо профіль
    await api.updateProfile(userId.value, {
      full_name: profile.value.full_name,
      is_fop: profile.value.is_fop
    });

    // 2. Оновлюємо налаштування ФОП (якщо увімкнено)
    if (profile.value.is_fop) {
      await api.updateFopSettings(userId.value, {
        fop_group: fopSettings.value.fop_group,
        is_zed: fopSettings.value.is_zed,
        income_tax_percent: fopSettings.value.income_tax_percent,
        esv_value: fopSettings.value.esv_value,
        military_tax_percent: fopSettings.value.military_tax_percent,
        tax_system: fopSettings.value.tax_system,
        activity_type: fopSettings.value.activity_type,
        has_employees: fopSettings.value.has_employees,
        employees_count: fopSettings.value.employees_count,
        is_vat_payer: fopSettings.value.is_vat_payer,
        land_area_ha: fopSettings.value.land_area_ha,
        normative_land_value: fopSettings.value.normative_land_value
      });
    }

    // 3. Зберігаємо КВЕДи локально
    localStorage.setItem(`kveds_${userId.value}`, JSON.stringify(userKveds.value));

    showMessage("Налаштування успішно збережено", 'success');
  } catch (error) {
    console.error(error);
    const errorMsg = error.response?.data?.detail || "Помилка при збереженні";
    showMessage(errorMsg, 'error');
  } finally {
    isSaving.value = false;
  }
};

// --- Helpers ---

const showMessage = (text, type) => {
  message.value = { text, type };
  setTimeout(() => message.value.text = '', 3000);
};

watch(() => profile.value.is_fop, async (newVal) => {
  if (newVal && userId.value) {
    try {
        const res = await api.get(`/settings/${userId.value}`);
        if(res.data) Object.assign(fopSettings.value, res.data);
    } catch (e) {
        // ігноруємо
    }
  }
});

// Реактивне скидання працівників при зміні групи
watch(() => fopSettings.value.fop_group, (newGroup) => {
  const group = parseInt(newGroup);
  if (group === 1 || group === 4) {
    fopSettings.value.has_employees = false;
    fopSettings.value.employees_count = 0;
  }
  
  // Автоматичне підставлення ставок при зміні групи (з динамічних правил)
  const rules = taxRulesStore.currentRules || {};
  
  if (group === 1) {
    fopSettings.value.single_tax_value = rules.single_tax_g1;
    fopSettings.value.military_tax_value = rules.fixed_military_tax;
    fopSettings.value.income_tax_percent = 0;
    fopSettings.value.military_tax_percent = 0;
  } else if (group === 2) {
    fopSettings.value.single_tax_value = rules.single_tax_g2;
    fopSettings.value.military_tax_value = rules.fixed_military_tax;
    fopSettings.value.income_tax_percent = 0;
    fopSettings.value.military_tax_percent = 0;
  } else if (group === 3) {
    fopSettings.value.income_tax_percent = fopSettings.value.is_vat_payer ? 3 : 5;
    fopSettings.value.military_tax_percent = 1;
    fopSettings.value.single_tax_value = 0;
    fopSettings.value.military_tax_value = 0;
  } else if (group === 4) {
    fopSettings.value.military_tax_value = rules.fixed_military_tax;
    fopSettings.value.single_tax_value = 0;
    fopSettings.value.income_tax_percent = 0;
    fopSettings.value.military_tax_percent = 0;
  }
});

// Проактивне обмеження кількості працівників та ставок
watch(() => fopSettings.value.employees_count, (newVal) => {
  if (newVal < 0) fopSettings.value.employees_count = 0;
  
  const group = parseInt(fopSettings.value.fop_group);
  if (group === 2 && newVal > 10) {
    fopSettings.value.employees_count = 10;
  }
});

watch(() => fopSettings.value.income_tax_percent, (newVal) => {
  const group = parseInt(fopSettings.value.fop_group);
  if (group === 4) {
    if (newVal < 0.09) fopSettings.value.income_tax_percent = 0.09;
    if (newVal > 1.8) fopSettings.value.income_tax_percent = 1.8;
  }
});

// Автоматичне перемикання податку при зміні ПДВ (для 3 групи)
watch(() => fopSettings.value.is_vat_payer, (isVat) => {
  if (parseInt(fopSettings.value.fop_group) === 3) {
    fopSettings.value.income_tax_percent = isVat ? 3 : 5;
  }
});

const filteredKveds = computed(() => {
  if (!kvedSearch.value) return KVED_SECTIONS;
  const search = kvedSearch.value.toLowerCase();
  return KVED_SECTIONS.map(section => ({
    ...section,
    groups: section.groups.map(g => ({
      ...g,
      items: g.items.filter(i => i.code.includes(search) || i.name.toLowerCase().includes(search))
    })).filter(g => g.items.length > 0)
  })).filter(s => s.groups.length > 0);
});

// Функція для підсвічування частин тексту, що збігаються з пошуком
const highlightMatch = (text, query) => {
  if (!query) return text;
  const parts = text.split(new RegExp(`(${query})`, 'gi'));
  return parts.map(part => 
    part.toLowerCase() === query.toLowerCase() 
      ? `<span class="bg-yellow-100 text-yellow-800 rounded px-0.5 font-bold">${part}</span>` 
      : part
  ).join('');
};

const toggleSection = (id) => { openSections.value[id] = !openSections.value[id]; };
const isKvedSelected = (code) => userKveds.value.some(k => k.code === code);

const toggleKved = (item) => {
  const idx = userKveds.value.findIndex(k => k.code === item.code);
  if (idx >= 0) userKveds.value.splice(idx, 1);
  else userKveds.value.push(item);
};

const removeKved = (code) => {
  userKveds.value = userKveds.value.filter(k => k.code !== code);
};

onMounted(() => {
  loadData();
});
</script>

<template>
  <div class="max-w-4xl mx-auto p-4 sm:p-8 animate-fade-in font-sans">
    <header class="mb-8 sm:mb-10 flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
      <div>
        <h1 class="text-3xl sm:text-4xl font-black text-gray-900 tracking-tight mb-2">Налаштування</h1>
        <p class="text-gray-500 font-medium font-bold">Керування профілем та податковими параметрами</p>
      </div>
      <div v-if="message.text" :class="message.type === 'success' ? 'bg-green-50 text-green-700 border-green-100' : 'bg-red-50 text-red-700 border-red-100'" class="px-4 py-2 rounded-2xl border text-sm font-bold animate-slide-up shadow-sm">
        {{ message.text }}
      </div>
    </header>

    <div v-if="isLoading" class="py-24 text-center">
      <Loader2 class="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
      <p class="text-gray-500 font-bold uppercase tracking-widest text-xs">Завантаження...</p>
    </div>

    <form v-else @submit.prevent="saveChanges" class="space-y-8">
      
      <!-- Card: Profile -->
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

      <!-- Card: Tax Settings (Only if FOP) -->
      <transition enter-active-class="transition duration-300 ease-out" enter-from-class="opacity-0 translate-y-4" enter-to-class="opacity-100 translate-y-0">
        <section v-if="profile.is_fop" class="bg-white rounded-[2rem] sm:rounded-3xl shadow-xl shadow-gray-200/50 border border-gray-100 p-6 sm:p-8 transform">
          <div class="flex items-center gap-4 mb-8">
            <div class="bg-indigo-600 p-3 rounded-2xl text-white shadow-lg shadow-indigo-200">
              <Briefcase :size="24" stroke-width="2.5" />
            </div>
            <h2 class="text-2xl font-black text-gray-900">Податки</h2>
          </div>

          <div class="space-y-8">
            <!-- Group Selection -->
            <div class="flex flex-col gap-4">
              <label class="text-sm font-black text-gray-400 uppercase tracking-widest">Група оподаткування</label>
              <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                <label 
                  v-for="g in [1, 2, 3, 4]" 
                  :key="g"
                  class="flex items-center justify-center p-4 border-2 rounded-2xl cursor-pointer transition-all text-center relative overflow-hidden group"
                  :class="fopSettings.fop_group === g ? 'border-indigo-600 bg-indigo-50 text-indigo-700 font-black shadow-lg shadow-indigo-100' : 'border-gray-50 bg-gray-50 hover:border-indigo-200 hover:bg-white text-gray-500'"
                >
                  <input type="radio" v-model="fopSettings.fop_group" :value="g" class="hidden">
                  <span class="z-10 text-lg">{{ g }} Гр</span>
                </label>
              </div>
            </div>

            <!-- Additional Details -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div class="flex flex-col gap-2 md:col-span-2">
              <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest px-2">Тип діяльності</label>
              <select v-model="fopSettings.activity_type" class="px-4 py-3 bg-gray-50 border-2 border-transparent focus:border-indigo-500 rounded-xl outline-none transition-all font-bold text-gray-800">
                <option value="services">Послуги</option>
                <option value="trade">Торгівля</option>
                <option value="production">Виробництво</option>
                <option value="agriculture">Сільське господарство</option>
                <option value="other">Інше</option>
              </select>
            </div>
          </div>

                <label 
                  class="flex items-center justify-between p-5 bg-gray-50 rounded-2xl border border-gray-100 transition-all group"
                  :class="[fopSettings.fop_group === 1 || fopSettings.fop_group === 4 ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:bg-white']"
                >
                  <div>
                    <p class="font-black text-gray-900 group-hover:text-blue-600 transition-colors">Наймані працівники</p>
                    <p class="text-[10px] text-gray-500 uppercase tracking-widest font-black" v-if="fopSettings.has_employees">
                      {{ fopSettings.fop_group === 2 ? 'Макс. 10 осіб' : 'Без обмежень' }}
                    </p>
                    <p class="text-[10px] text-red-500 uppercase tracking-widest font-black" v-if="fopSettings.fop_group === 1 || fopSettings.fop_group === 4">Заборонено законодавством</p>
                  </div>
                  <div class="relative w-7 h-7">
                    <input 
                      type="checkbox" 
                      v-model="fopSettings.has_employees" 
                      :disabled="fopSettings.fop_group === 1 || fopSettings.fop_group === 4"
                      class="peer appearance-none w-7 h-7 border-2 border-gray-200 checked:bg-blue-600 checked:border-blue-600 rounded-xl transition-all disabled:bg-gray-200"
                    >
                    <div class="absolute inset-0 flex items-center justify-center text-white opacity-0 peer-checked:opacity-100 pointer-events-none">
                      <Check :size="16" stroke-width="4" />
                    </div>
                  </div>
                </label>
               
                <div v-if="fopSettings.has_employees" class="animate-fade-in flex flex-col gap-2">
                  <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest px-2">Кількість працівників</label>
                  <input 
                    type="number" 
                    v-model.number="fopSettings.employees_count" 
                    min="0"
                    :max="fopSettings.fop_group === 2 ? 10 : undefined"
                    class="px-4 py-3 bg-gray-50 border-2 border-transparent focus:border-indigo-500 rounded-xl outline-none transition-all font-bold text-gray-800"
                  >
                </div>

            <!-- Group 4 Details -->
            <transition enter-active-class="transition duration-300 ease-out" enter-from-class="opacity-0 translate-x-4" enter-to-class="opacity-100 translate-x-0">
              <div v-if="fopSettings.fop_group === 4" class="grid grid-cols-1 md:grid-cols-2 gap-6 p-6 bg-green-50/30 rounded-3xl border border-green-100 shadow-inner">
                <div class="flex flex-col gap-2">
                  <label class="text-[10px] font-black text-green-700 uppercase tracking-widest px-2">Площа земель (га)</label>
                  <input type="number" step="0.01" min="0" v-model="fopSettings.land_area_ha" class="px-4 py-3 bg-white border-2 border-transparent focus:border-green-500 rounded-xl outline-none transition-all font-bold text-gray-800">
                </div>
                <div class="flex flex-col gap-2">
                  <label class="text-[10px] font-black text-green-700 uppercase tracking-widest px-2">Нормативна оцінка (грн/га)</label>
                  <input type="number" min="0" v-model="fopSettings.normative_land_value" class="px-4 py-3 bg-white border-2 border-transparent focus:border-green-500 rounded-xl outline-none transition-all font-bold text-gray-800">
                </div>
              </div>
            </transition>

            <label v-if="fopSettings.fop_group === 3" class="flex items-center justify-between p-5 bg-indigo-50/50 rounded-2xl border border-indigo-100 animate-fade-in hover:bg-indigo-50 transition-all cursor-pointer group">
              <div>
                <p class="font-black text-indigo-900 group-hover:text-blue-600 transition-colors">Платник ПДВ</p>
                <p class="text-[10px] text-indigo-600 font-bold uppercase tracking-widest">Ставка податку 3% замість 5%</p>
              </div>
              <div class="relative w-7 h-7">
                <input type="checkbox" v-model="fopSettings.is_vat_payer" class="peer appearance-none w-7 h-7 border-2 border-indigo-200 checked:bg-indigo-600 checked:border-indigo-600 rounded-xl transition-all">
                <div class="absolute inset-0 flex items-center justify-center text-white opacity-0 peer-checked:opacity-100 pointer-events-none">
                  <Check :size="16" stroke-width="4" />
                </div>
              </div>
            </label>

            <!-- Tax Rates Inputs -->
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 p-6 bg-gray-50/50 rounded-3xl border border-gray-100 shadow-inner">
              <!-- Єдиний податок -->
              <div class="flex flex-col gap-2">
                <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest px-2">
                  {{ fopSettings.fop_group === 3 ? 'Єдиний податок (%)' : (fopSettings.fop_group === 4 ? 'Ставка податку (%)' : 'Єдиний податок (грн/міс)') }}
                </label>
                  
                  <!-- Для 3 групи - відсотки -->
                  <input 
                    v-if="fopSettings.fop_group === 3"
                    type="number" 
                    step="0.1" 
                    min="0"
                    v-model.number="fopSettings.income_tax_percent" 
                    class="px-4 py-3 bg-white border-2 border-transparent focus:border-indigo-500 rounded-xl outline-none transition-all font-bold text-gray-800"
                    title="Ставка для 3-ї групи: 5% (або 3% з ПДВ)"
                  >
                  <!-- Для 1 та 2 груп - фіксована сума (НЕ РЕДАГУЄТЬСЯ) -->
                  <input 
                    v-else-if="fopSettings.fop_group === 1 || fopSettings.fop_group === 2"
                    type="number" 
                    v-model.number="fopSettings.single_tax_value" 
                    disabled
                    class="px-4 py-3 bg-gray-100 border-2 border-transparent rounded-xl outline-none transition-all font-bold text-gray-400 cursor-not-allowed"
                    title="Для 1-ї та 2-ї груп ставка фіксована"
                  >
                  <!-- Для 4 групи - редагуємо відсоток 0.09% - 1.8% -->
                  <div v-else class="flex flex-col gap-1">
                    <input 
                      type="number" 
                      step="0.01"
                      min="0.09"
                      max="1.8"
                      v-model.number="fopSettings.income_tax_percent" 
                      class="px-4 py-3 bg-white border-2 border-transparent focus:border-indigo-500 rounded-xl outline-none transition-all font-bold text-gray-800"
                    >
                    <span class="text-[8px] text-gray-400 font-bold px-1 uppercase tracking-tighter">Діапазон: 0.09% - 1.8%</span>
                  </div>
              </div>

              <!-- Військовий збір -->
              <div class="flex flex-col gap-2">
                <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest px-2">
                  {{ fopSettings.fop_group === 3 ? 'Військовий збір (%)' : 'Військовий збір (грн/міс)' }}
                </label>
                  
                  <!-- Для 3 групи - 1% -->
                  <input 
                    v-if="fopSettings.fop_group === 3"
                    type="number" 
                    step="0.1" 
                    min="0"
                    v-model.number="fopSettings.military_tax_percent" 
                    class="px-4 py-3 bg-white border-2 border-transparent focus:border-indigo-500 rounded-xl outline-none transition-all font-bold text-gray-800"
                  >
                  <!-- Для інших - фіксований 800 грн (НЕ РЕДАГУЄТЬСЯ) -->
                  <input 
                    v-else
                    type="number" 
                    v-model.number="fopSettings.military_tax_value" 
                    disabled
                    class="px-4 py-3 bg-gray-100 border-2 border-transparent rounded-xl outline-none transition-all font-bold text-gray-400 cursor-not-allowed"
                  >
              </div>

              <!-- ЄСВ -->
              <div class="flex flex-col gap-2">
                <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest px-2">ЄСВ (грн/міс)</label>
                  <input 
                    type="number" 
                    min="0"
                    step="0.01"
                    v-model.number="fopSettings.esv_value" 
                    :class="[fopSettings.fop_group === 1 || fopSettings.fop_group === 2 ? 'bg-indigo-50/30' : 'bg-white text-gray-800']"
                    class="px-4 py-3 border-2 border-transparent focus:border-indigo-500 rounded-xl outline-none transition-all font-bold text-gray-800 w-full"
                  >
                  <span v-if="fopSettings.fop_group === 1 || fopSettings.fop_group === 2" class="text-[8px] text-gray-400 font-bold px-1 uppercase tracking-tighter">Зазвичай 1760.00 грн (22% від мін. з/п)</span>
              </div>
            </div>

            <!-- KVEDs Section -->
            <div class="space-y-4">
              <div class="flex justify-between items-center">
                <label class="text-sm font-black text-gray-400 uppercase tracking-widest">Види діяльності (КВЕД)</label>
                <button 
                  type="button" 
                  @click="isKvedModalOpen = true" 
                  class="text-xs font-black bg-indigo-600 text-white px-4 py-2 rounded-xl hover:bg-indigo-700 transition-all flex items-center gap-2 shadow-lg shadow-indigo-200 active:scale-95"
                >
                  <Plus :size="16" stroke-width="3" /> Додати новий
                </button>
              </div>
              
              <transition-group tag="div" name="list" class="flex flex-wrap gap-3">
                <div 
                  v-for="k in userKveds" 
                  :key="k.code" 
                  class="inline-flex items-center gap-3 px-4 py-2 bg-white border-2 border-gray-100 rounded-2xl text-sm font-bold text-gray-700 shadow-sm group hover:border-indigo-200 transition-all"
                >
                  <span class="font-black font-mono text-indigo-600">{{ k.code }}</span>
                  <span class="max-w-[200px] truncate text-gray-600">{{ k.name }}</span>
                  <button 
                    type="button" 
                    @click="removeKved(k.code)" 
                    class="text-gray-300 hover:text-red-500 transition-colors p-1"
                  >
                    <X :size="16" />
                  </button>
                </div>
              </transition-group>
              
              <div v-if="userKveds.length === 0" class="flex flex-col items-center justify-center py-10 border-2 border-dashed border-gray-100 rounded-3xl bg-gray-50/30">
                <Plus :size="32" class="text-gray-200 mb-2" />
                <p class="text-sm text-gray-400 font-bold uppercase tracking-widest">КВЕДи не обрано</p>
              </div>
            </div>

            <!-- ZED Checkbox -->
            <!-- ZED Checkbox (Commented out as per request)
            <label 
              class="flex items-center gap-6 p-6 border-2 border-gray-50 rounded-3xl transition-all bg-gray-50/30 group"
              :class="[fopSettings.fop_group === 1 || fopSettings.fop_group === 4 ? 'opacity-50 cursor-not-allowed grayscale' : 'cursor-pointer hover:border-indigo-100']"
            >
              <div class="relative w-10 h-10 shrink-0">
                <input 
                  type="checkbox" 
                  v-model="fopSettings.is_zed" 
                  :disabled="fopSettings.fop_group === 1 || fopSettings.fop_group === 4"
                  class="peer appearance-none w-10 h-10 border-2 border-gray-200 checked:bg-indigo-600 checked:border-indigo-600 rounded-2xl transition-all shadow-inner disabled:bg-gray-200 disabled:border-gray-300"
                >
                <div class="absolute inset-0 flex items-center justify-center text-white opacity-0 peer-checked:opacity-100 pointer-events-none transition-all scale-50 peer-checked:scale-100">
                  <Check :size="24" stroke-width="4" />
                </div>
              </div>
              <div class="flex-grow">
                <div class="flex items-center gap-2">
                  <span class="block font-black text-gray-900 text-lg group-hover:text-indigo-600 transition-colors">ЗЕД (ВЕД)</span>
                  <span v-if="fopSettings.fop_group === 1 || fopSettings.fop_group === 4" class="text-[10px] bg-red-100 text-red-600 px-2 py-0.5 rounded-full font-bold uppercase tracking-wider">Заборонено</span>
                </div>
                <span class="text-sm text-gray-500 font-medium">Робота з валютою та іноземними контрагентами</span>
              </div>
              <div class="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" v-if="fopSettings.is_zed"></div>
            </label>
            -->
          </div>
        </section>
      </transition>

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
    <BaseModal 
      :isOpen="isKvedModalOpen" 
      title="Оберіть КВЕД" 
      @close="isKvedModalOpen = false"
    >
      <div class="flex flex-col h-[70vh] p-2">
        <div class="mb-6 relative group">
          <Search class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-blue-500 transition-colors" :size="20" />
          <input 
            type="text" 
            v-model="kvedSearch" 
            placeholder="Пошук за кодом або назвою..." 
            class="w-full pl-12 pr-12 py-4 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-2xl outline-none font-bold placeholder:text-gray-300 transition-all shadow-sm"
          >
          <button 
            v-if="kvedSearch" 
            @click="kvedSearch = ''"
            class="absolute right-4 top-1/2 -translate-y-1/2 p-2 hover:bg-gray-100 rounded-full text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X :size="18" />
          </button>
        </div>
        
        <div class="flex-1 overflow-y-auto custom-scrollbar border-2 border-gray-100 rounded-3xl bg-gray-50/50">
          <div v-for="section in filteredKveds" :key="section.id" class="border-b border-gray-100 last:border-0 overflow-hidden bg-white">
            <button 
              type="button"
              @click="toggleSection(section.id)" 
              class="w-full flex items-center justify-between p-5 hover:bg-gray-50 text-left transition-colors sticky top-0 z-10 bg-white"
            >
              <span class="font-black text-sm text-gray-800 tracking-tight">{{ section.title }}</span>
              <div class="bg-gray-100 p-1 rounded-lg">
                <ChevronDown v-if="openSections[section.id]" :size="16" class="text-gray-500" />
                <ChevronRight v-else :size="16" class="text-gray-400" />
              </div>
            </button>
            
            <transition enter-active-class="transition duration-200 ease-out" enter-from-class="opacity-0 -translate-y-2" enter-to-class="opacity-100 translate-y-0">
              <div v-if="openSections[section.id] || kvedSearch" class="bg-white border-t border-gray-50">
                <div v-for="group in section.groups" :key="group.id" class="border-b border-gray-50 last:border-0">
                  <div class="px-6 py-2 bg-gray-50/50 text-[9px] font-black text-gray-400 uppercase tracking-widest">
                    {{ group.title }}
                  </div>
                  <div class="divide-y divide-gray-50">
                    <button 
                      v-for="item in group.items" 
                      :key="item.code" 
                      type="button"
                      @click="toggleKved(item)" 
                      class="w-full text-left px-6 py-4 flex items-center gap-5 hover:bg-blue-50 transition-all group"
                    >
                      <div 
                        class="w-6 h-6 rounded-lg border-2 flex items-center justify-center shrink-0 transition-all bg-white"
                        :class="isKvedSelected(item.code) ? 'bg-blue-600 border-blue-600 shadow-lg shadow-blue-100' : 'border-gray-200 group-hover:border-blue-300'"
                      >
                        <Check v-if="isKvedSelected(item.code)" :size="14" class="text-white" stroke-width="3" />
                      </div>
                      <div class="flex-grow">
                        <div class="flex items-center gap-3 mb-1">
                          <span class="font-black font-mono text-sm text-gray-900 group-hover:text-blue-600" v-html="highlightMatch(item.code, kvedSearch)"></span>
                          <div class="flex gap-1">
                            <span v-for="g in item.allowedGroups" :key="g" class="text-[9px] font-black bg-gray-100 text-gray-400 px-1.5 py-0.5 rounded border border-gray-100">
                              {{ g }} ГР
                            </span>
                          </div>
                        </div>
                        <div class="text-sm text-gray-600 font-medium leading-relaxed" v-html="highlightMatch(item.name, kvedSearch)"></div>
                      </div>
                    </button>
                  </div>
                </div>
              </div>
            </transition>
          </div>
          <div v-if="kvedSearch && filteredKveds.length === 0" class="p-12 text-center">
            <div class="text-4xl mb-4 text-gray-300">🔍</div>
            <p class="font-black text-gray-500 uppercase tracking-widest text-sm">Нічого не знайдено</p>
            <p class="text-xs text-gray-400 mt-2 italic font-medium">Спробуйте змінити запит або код</p>
          </div>
        </div>

        <div class="pt-6 mt-auto flex justify-end">
          <button 
            type="button" 
            @click="isKvedModalOpen = false" 
            class="px-10 py-4 bg-gray-900 text-white rounded-2xl font-black hover:bg-black transition-all shadow-xl active:scale-95"
          >
            Готово
          </button>
        </div>
      </div>
    </BaseModal>
  </div>
</template>

<style scoped>
.animate-fade-in { animation: fadeIn 0.6s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

.animate-slide-up { animation: slideUp 0.4s ease-out; }
@keyframes slideUp { from { transform: translateY(10px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }

/* Scrollbar customization */
.custom-scrollbar::-webkit-scrollbar { width: 5px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background-color: #e2e8f0; border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background-color: #cbd5e1; }

.list-enter-active, .list-leave-active { transition: all 0.3s ease; }
.list-enter-from, .list-leave-to { opacity: 0; transform: translateX(-10px); }
</style>