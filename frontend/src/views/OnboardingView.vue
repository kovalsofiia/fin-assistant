<script setup>
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import api from '@/api'; 
import { supabase } from '@/supabase';
import { KVED_SECTIONS } from '@/constants/kveds';
import { 
  ArrowLeft, 
  Check, 
  Clock, 
  Info, 
  Search, 
  ChevronDown, 
  ChevronRight, 
  X 
} from 'lucide-vue-next';

const router = useRouter();
const isLoading = ref(false);
const step = ref(1);
const totalSteps = 3;

// Дані форми
const formData = ref({
  isFop: null,
  hasForeignClients: null,
  yearlyIncome: '',
  selectedKveds: []
});

// Пошук КВЕДів
const kvedSearch = ref('');
const openSections = ref({});

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

// Методи вибору
const toggleKved = (item) => {
  const idx = formData.value.selectedKveds.findIndex(k => k.code === item.code);
  if (idx >= 0) formData.value.selectedKveds.splice(idx, 1);
  else formData.value.selectedKveds.push(item);
};

const isKvedSelected = (code) => formData.value.selectedKveds.some(k => k.code === code);
const toggleSection = (id) => { openSections.value[id] = !openSections.value[id]; };

// Логіка завершення
const finishOnboarding = async () => {
  isLoading.value = true;
  try {
    const { data: { user } } = await supabase.auth.getUser();
    if (!user) throw new Error("Користувач не знайдений");

    // 1. Оновлюємо профіль (обов'язково для всіх)
    await api.patch(`/profile/${user.id}`, {
      is_fop: formData.value.isFop,
      full_name: user.user_metadata?.full_name || ""
    });

    // 2. Якщо користувач ФОП, зберігаємо податкові налаштування та КВЕДи
    if (formData.value.isFop) {
      // Визначаємо групу
      let group = 3;
      if (!formData.value.hasForeignClients && parseFloat(formData.value.yearlyIncome || 0) < 5000000) {
        group = 2;
      }

      const settingsData = {
        fop_group: group,
        is_zed: formData.value.hasForeignClients,
        income_tax_percent: group === 3 ? 5.0 : 0,
        esv_value: 1760.0,
        military_tax_percent: 1.5
      };
      await api.patch(`/settings/${user.id}`, settingsData);

      // Зберігаємо КВЕДи локально
      localStorage.setItem(`kveds_${user.id}`, JSON.stringify(formData.value.selectedKveds));
    }

    // 3. Перехід на дашборд
    router.push('/dashboard'); 
    
  } catch (e) {
    console.error(e);
    alert("Помилка збереження даних: " + e.message);
  } finally {
    isLoading.value = false;
  }
};
</script>

<template>
  <div class="min-h-screen bg-gray-50 flex items-center justify-center p-4">
    <div class="max-w-2xl w-full bg-white rounded-3xl shadow-2xl p-8 animate-slide-up border border-gray-100">
      
      <!-- Header & Progress -->
      <div class="mb-10">
        <div class="flex items-center justify-between mb-6">
          <div class="flex items-center gap-4">
            <button 
              v-if="step > 1" 
              @click="step--" 
              class="p-2.5 hover:bg-gray-100 rounded-xl text-gray-500 transition-all active:scale-95"
            >
              <ArrowLeft :size="20" />
            </button>
            <h2 class="text-3xl font-black text-gray-900 tracking-tight">Налаштування</h2>
          </div>
          <span class="text-xs font-black uppercase tracking-widest text-blue-600 bg-blue-50 px-4 py-1.5 rounded-full border border-blue-100">
            Крок {{ step }} з {{ totalSteps }}
          </span>
        </div>
        
        <!-- Progress Bar -->
        <div class="h-2.5 bg-gray-100 rounded-full overflow-hidden shadow-inner">
          <div 
            class="h-full bg-gradient-to-r from-blue-500 to-indigo-600 transition-all duration-700 ease-out shadow-lg" 
            :style="{ width: (step / totalSteps) * 100 + '%' }"
          ></div>
        </div>
      </div>

      <!-- Step 1: Status -->
      <div v-if="step === 1" class="space-y-8 animate-fade-in">
        <div class="text-center">
          <h3 class="text-2xl font-extrabold text-gray-800 mb-2">Ваш статус</h3>
          <p class="text-gray-500 font-medium">Ви вже зареєстровані як ФОП?</p>
        </div>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <button 
            @click="formData.isFop = true; step++" 
            class="p-8 border-2 border-transparent hover:border-blue-500 bg-blue-50/50 hover:bg-white rounded-3xl transition-all group text-left shadow-sm hover:shadow-xl hover:shadow-blue-100 relative overflow-hidden"
          >
            <div class="bg-blue-600 w-12 h-12 rounded-2xl flex items-center justify-center mb-6 text-white group-hover:scale-110 group-hover:rotate-3 transition-transform shadow-lg shadow-blue-200">
              <Check :size="24" stroke-width="3" />
            </div>
            <div class="font-black text-xl text-gray-900 mb-1">Так, я ФОП</div>
            <div class="text-sm text-gray-600 font-medium leading-relaxed">Я вже веду підприємницьку діяльність офіційно</div>
            <div class="absolute -right-4 -bottom-4 opacity-5 group-hover:scale-110 transition-transform">
              <Check :size="100" />
            </div>
          </button>

          <button 
            @click="formData.isFop = false; finishOnboarding()" 
            class="p-8 border-2 border-transparent hover:border-blue-400 bg-gray-50 hover:bg-white rounded-3xl transition-all group text-left shadow-sm hover:shadow-xl hover:shadow-gray-100 relative overflow-hidden"
          >
            <div class="bg-white w-12 h-12 rounded-2xl flex items-center justify-center mb-6 text-gray-400 group-hover:scale-110 group-hover:-rotate-3 transition-transform shadow-md border border-gray-100">
              <Clock :size="24" />
            </div>
            <div class="font-black text-xl text-gray-900 mb-1" v-if="!isLoading">Ні, не ФОП</div>
            <div class="font-black text-xl text-gray-900 mb-1 flex items-center gap-3" v-else>
              <div class="w-5 h-5 border-2 border-blue-600/30 border-t-blue-600 rounded-full animate-spin"></div>
              Завантаження...
            </div>
            <div class="text-sm text-gray-600 font-medium leading-relaxed">Просто хочу керувати своїми фінансами</div>
            <div class="absolute -right-4 -bottom-4 opacity-5 group-hover:scale-110 transition-transform">
              <Clock :size="100" />
            </div>
          </button>
        </div>
      </div>

      <!-- Step 2: Details -->
      <div v-if="step === 2" class="space-y-8 animate-fade-in">
        <div class="text-center">
          <h3 class="text-2xl font-extrabold text-gray-800 mb-2">Деталі діяльності</h3>
          <p class="text-gray-500 font-medium">Це допоможе визначити групу оподаткування</p>
        </div>

        <div class="space-y-6">
          <p class="font-bold text-gray-700 text-lg">Чи працюєте ви з іноземними замовниками (ЗЕД)?</p>
          <div class="grid grid-cols-1 gap-4">
            <button 
              @click="formData.hasForeignClients = true; step++"
              class="w-full py-5 px-6 rounded-2xl border-2 border-gray-100 hover:border-blue-500 hover:bg-blue-50 text-left group transition-all"
            >
              <div class="flex items-center justify-between">
                <div>
                  <div class="font-black text-gray-900 group-hover:text-blue-700">Так, отримую дохід у валюті</div>
                  <div class="text-sm text-gray-500 font-medium mt-1">Для експорту послуг або товарів за кордон</div>
                </div>
                <div class="w-2 h-2 rounded-full bg-gray-200 group-hover:bg-blue-500 group-hover:scale-150 transition-all"></div>
              </div>
            </button>
            <button 
              @click="formData.hasForeignClients = false; step++"
              class="w-full py-5 px-6 rounded-2xl border-2 border-gray-100 hover:border-blue-500 hover:bg-blue-50 text-left group transition-all"
            >
              <div class="flex items-center justify-between">
                <div>
                  <div class="font-black text-gray-900 group-hover:text-blue-700">Ні, працюю тільки по Україні</div>
                  <div class="text-sm text-gray-500 font-medium mt-1">Весь мій дохід у гривні від резидентів UA</div>
                </div>
                <div class="w-2 h-2 rounded-full bg-gray-200 group-hover:bg-blue-500 group-hover:scale-150 transition-all"></div>
              </div>
            </button>
          </div>
        </div>
      </div>

      <!-- Step 3: KVEDs -->
      <div v-if="step === 3" class="space-y-6 animate-fade-in">
        <div class="bg-blue-50/50 p-5 rounded-3xl text-sm text-blue-800 flex gap-4 border border-blue-100 shadow-sm shadow-blue-50">
          <div class="bg-blue-100 p-2 rounded-xl h-fit">
            <Info :size="20" class="text-blue-600" />
          </div>
          <p class="font-medium leading-relaxed">Оберіть ваші види діяльності (КВЕДи). Це критично впливає на те, які групи ФОП вам дозволені законом.</p>
        </div>

        <!-- Search -->
        <div class="relative group">
          <Search class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-blue-500 transition-colors" :size="20" />
          <input 
            type="text" 
            v-model="kvedSearch" 
            placeholder="Пошук за назвою або кодом КВЕД..." 
            class="w-full pl-12 pr-4 py-4 bg-gray-50 border-2 border-transparent focus:border-blue-500 focus:bg-white rounded-2xl outline-none transition-all font-medium placeholder:text-gray-400"
          >
        </div>

        <!-- List -->
        <div class="h-72 overflow-y-auto custom-scrollbar border-2 border-gray-100 rounded-3xl bg-gray-50/30">
          <div v-for="section in filteredKveds" :key="section.id" class="bg-white border-b border-gray-100 last:border-0 overflow-hidden">
            <button 
              @click="toggleSection(section.id)" 
              class="w-full flex items-center justify-between p-5 hover:bg-gray-50 text-left transition-colors"
            >
              <span class="font-extrabold text-sm text-gray-800 tracking-tight">{{ section.title }}</span>
              <div class="bg-gray-100 p-1 rounded-lg">
                <ChevronDown v-if="openSections[section.id]" :size="16" class="text-gray-500" />
                <ChevronRight v-else :size="16" class="text-gray-400" />
              </div>
            </button>
            
            <div v-if="openSections[section.id]" class="border-t border-gray-50 bg-white">
              <div v-for="group in section.groups" :key="group.id" class="border-b border-gray-50 last:border-0">
                <div class="px-5 py-2.5 bg-gray-50/50 text-[10px] font-black text-gray-400 uppercase tracking-[0.2em]">
                  {{ group.title }}
                </div>
                <div class="divide-y divide-gray-50">
                  <button 
                    v-for="item in group.items" 
                    :key="item.code" 
                    @click="toggleKved(item)" 
                    class="w-full text-left px-5 py-4 flex items-center gap-4 hover:bg-blue-50/50 transition-all group"
                  >
                    <div 
                      class="w-6 h-6 rounded-lg border-2 flex items-center justify-center shrink-0 transition-all duration-300"
                      :class="isKvedSelected(item.code) ? 'bg-blue-600 border-blue-600 shadow-lg shadow-blue-100 rotate-0' : 'border-gray-200 group-hover:border-blue-300 group-hover:rotate-6'"
                    >
                      <Check v-if="isKvedSelected(item.code)" :size="14" class="text-white" stroke-width="3" />
                    </div>
                    <div class="flex-grow">
                      <div class="flex items-center gap-2 mb-0.5">
                        <span class="font-black font-mono text-sm text-gray-900 group-hover:text-blue-700">{{ item.code }}</span>
                        <div class="flex gap-1">
                          <span v-for="g in item.allowedGroups" :key="g" class="text-[9px] font-black bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded border border-gray-200">
                            {{ g }} ГР
                          </span>
                        </div>
                      </div>
                      <div class="text-sm text-gray-600 font-medium leading-snug">{{ item.name }}</div>
                    </div>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Selected Tags -->
        <transition-group 
          tag="div" 
          name="list"
          v-if="formData.selectedKveds.length > 0" 
          class="flex flex-wrap gap-2 pt-2"
        >
          <span 
            v-for="k in formData.selectedKveds" 
            :key="k.code" 
            class="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-xl text-xs font-bold shadow-md shadow-blue-100"
          >
            {{ k.code }}
            <button @click="toggleKved(k)" class="hover:scale-125 transition-transform"><X :size="14" /></button>
          </span>
        </transition-group>

        <button 
          @click="finishOnboarding" 
          :disabled="formData.selectedKveds.length === 0 || isLoading" 
          class="w-full mt-8 py-5 rounded-2xl font-black bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed shadow-xl shadow-blue-200 transition-all active:scale-[0.98] flex justify-center items-center gap-3"
        >
          <div v-if="isLoading" class="loader w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
          {{ isLoading ? 'Збереження...' : 'Завершити налаштування' }}
        </button>
      </div>

    </div>
  </div>
</template>

<style scoped>
.animate-slide-up { animation: slideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes slideUp { from { transform: translateY(30px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }

.animate-fade-in { animation: fadeIn 0.4s ease-out; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

.custom-scrollbar::-webkit-scrollbar { width: 5px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background-color: #e2e8f0; border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background-color: #cbd5e1; }

.list-enter-active, .list-leave-active { transition: all 0.3s ease; }
.list-enter-from, .list-leave-to { opacity: 0; transform: scale(0.9); }

.loader {
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
}
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>

<style scoped>
.animate-slide-up { animation: slideUp 0.5s ease-out; }
@keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }

.animate-fade-in { animation: fadeIn 0.3s ease-out; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

.custom-scrollbar::-webkit-scrollbar { width: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background-color: #cbd5e1; border-radius: 3px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background-color: #94a3b8; }

.loader {
    border: 2px solid rgba(255,255,255,0.3);
    border-radius: 50%;
    border-top: 2px solid white;
    width: 20px;
    height: 20px;
    animation: spin 1s linear infinite;
}
@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
</style>