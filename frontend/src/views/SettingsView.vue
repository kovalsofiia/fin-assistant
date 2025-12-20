<script setup>
  
import { ref, onMounted, watch, computed } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/api'; 
import { supabase } from '@/supabase';
import BaseModal from '../components/common/BaseModal.vue'; 
import { KVED_SECTIONS } from '../constants/kveds';
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
  military_tax_percent: 1.5
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
        const settingsRes = await api.getFopSettings(userId.value);
        if (settingsRes.data) {
          fopSettings.value = {
            fop_group: settingsRes.data.fop_group,
            is_zed: settingsRes.data.is_zed,
            income_tax_percent: settingsRes.data.income_tax_percent,
            esv_value: settingsRes.data.esv_value,
            military_tax_percent: settingsRes.data.military_tax_percent
          };
        }
      } catch (e) {
        console.warn("Settings not found, using defaults");
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
        military_tax_percent: fopSettings.value.military_tax_percent
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
  <div class="max-w-4xl mx-auto p-4 md:p-8 animate-fade-in font-sans">
    <header class="mb-10 flex justify-between items-end">
      <div>
        <h1 class="text-4xl font-black text-gray-900 tracking-tight mb-2">Налаштування</h1>
        <p class="text-gray-500 font-medium">Керування профілем та податковими параметрами</p>
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
      <section class="bg-white rounded-3xl shadow-xl shadow-gray-200/50 border border-gray-100 p-8 transition-shadow hover:shadow-2xl hover:shadow-gray-200">
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
            <label class="flex items-center gap-4 cursor-pointer p-4 rounded-2xl bg-gray-50 hover:bg-blue-50 transition-all border-2 border-transparent hover:border-blue-100 group w-full">
              <div class="w-8 h-8 rounded-xl border-2 flex items-center justify-center transition-all bg-white" :class="profile.is_fop ? 'bg-blue-600 border-blue-600 shadow-lg shadow-blue-100' : 'border-gray-200'">
                <Check v-if="profile.is_fop" :size="20" class="text-white" stroke-width="3" />
              </div>
              <input type="checkbox" v-model="profile.is_fop" class="hidden">
              <div>
                <span class="block font-black text-gray-900">Я використовую ФОП</span>
                <span class="text-xs text-gray-500 font-medium">Активує податкові інструменти</span>
              </div>
            </label>
          </div>
        </div>
      </section>

      <!-- Card: Tax Settings (Only if FOP) -->
      <transition enter-active-class="transition duration-300 ease-out" enter-from-class="opacity-0 translate-y-4" enter-to-class="opacity-100 translate-y-0">
        <section v-if="profile.is_fop" class="bg-white rounded-3xl shadow-xl shadow-gray-200/50 border border-gray-100 p-8 transform">
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
              <div class="grid grid-cols-3 gap-4">
                <label 
                  v-for="g in [1, 2, 3]" 
                  :key="g"
                  class="flex items-center justify-center p-4 border-2 rounded-2xl cursor-pointer transition-all text-center relative overflow-hidden group"
                  :class="fopSettings.fop_group === g ? 'border-indigo-600 bg-indigo-50 text-indigo-700 font-black shadow-lg shadow-indigo-100' : 'border-gray-50 bg-gray-50 hover:border-indigo-200 hover:bg-white text-gray-500'"
                >
                  <input type="radio" v-model="fopSettings.fop_group" :value="g" class="hidden">
                  <span class="z-10 text-lg">{{ g }} Група</span>
                </label>
              </div>
            </div>

            <!-- Tax Rates Inputs -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 p-6 bg-gray-50/50 rounded-3xl border border-gray-100 shadow-inner">
              <div class="flex flex-col gap-2">
                <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest px-2">Єдиний податок (%)</label>
                <input 
                  type="number" 
                  step="0.1" 
                  v-model.number="fopSettings.income_tax_percent" 
                  :disabled="fopSettings.fop_group !== 3"
                  class="px-4 py-3 bg-white border-2 border-transparent focus:border-indigo-500 rounded-xl outline-none transition-all font-bold text-gray-800 disabled:opacity-50 disabled:grayscale"
                >
              </div>
              <div class="flex flex-col gap-2">
                <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest px-2">Військовий збір (%)</label>
                <input 
                  type="number" 
                  step="0.1" 
                  v-model.number="fopSettings.military_tax_percent" 
                  class="px-4 py-3 bg-white border-2 border-transparent focus:border-indigo-500 rounded-xl outline-none transition-all font-bold text-gray-800"
                >
              </div>
              <div class="flex flex-col gap-2">
                <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest px-2">ЄСВ (грн/квартал)</label>
                <input 
                  type="number" 
                  v-model.number="fopSettings.esv_value" 
                  class="px-4 py-3 bg-white border-2 border-transparent focus:border-indigo-500 rounded-xl outline-none transition-all font-bold text-gray-800"
                >
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
            <label class="flex items-center gap-6 p-6 border-2 border-gray-50 rounded-3xl cursor-pointer hover:border-indigo-100 transition-all bg-gray-50/30 group">
              <div class="w-10 h-10 rounded-2xl border-2 flex items-center justify-center transition-all bg-white" :class="fopSettings.is_zed ? 'bg-indigo-600 border-indigo-600 shadow-lg shadow-indigo-100' : 'border-gray-200 group-hover:border-indigo-300'">
                <Check v-if="fopSettings.is_zed" :size="20" class="text-white" stroke-width="3" />
              </div>
              <input type="checkbox" v-model="fopSettings.is_zed" class="hidden">
              <div class="flex-grow">
                <span class="block font-black text-gray-900 text-lg">ЗЕД (ВЕД)</span>
                <span class="text-sm text-gray-500 font-medium">Робота з валютою та іноземними контрагентами</span>
              </div>
              <div class="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" v-if="fopSettings.is_zed"></div>
            </label>
          </div>
        </section>
      </transition>

      <!-- Action Buttons -->
      <footer class="sticky bottom-8 z-40 flex items-center justify-between p-6 bg-white/80 backdrop-blur-xl border-2 border-gray-100 rounded-3xl shadow-2xl shadow-gray-300 pb-6 px-8">
        <div class="text-gray-400 font-bold text-xs uppercase tracking-[0.2em]">
          {{ isSaving ? 'Узгодження даних...' : 'Готовий до збереження' }}
        </div>
        <button 
          type="submit" 
          :disabled="isSaving" 
          class="px-10 py-5 bg-blue-600 text-white rounded-2xl font-black text-lg hover:bg-blue-700 disabled:opacity-70 shadow-2xl shadow-blue-200 transition-all active:scale-95 flex items-center gap-4"
        >
          <Loader2 v-if="isSaving" class="animte-spin" :size="24" />
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