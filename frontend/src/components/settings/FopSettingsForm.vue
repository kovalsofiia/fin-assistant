<script setup>
import { computed, watch } from 'vue';
import { Briefcase, Check, Plus, X } from 'lucide-vue-next';
import { useTaxRulesStore } from '@/stores/taxRulesStore';

const props = defineProps({
  modelValue: {
    type: Object,
    required: true
  },
  userKveds: {
    type: Array,
    required: true
  }
});

const emit = defineEmits(['update:modelValue', 'update:userKveds', 'openKvedModal']);

const taxRulesStore = useTaxRulesStore();
const fopSettings = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
});

// Watchers for internal FOP business logic previously in SettingsView.vue:
watch(() => fopSettings.value.fop_group, (newGroup) => {
  const group = parseInt(newGroup);
  if (group === 1 || group === 4) {
    fopSettings.value.has_employees = false;
    fopSettings.value.employees_count = 0;
  }
  
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

watch(() => fopSettings.value.is_vat_payer, (isVat) => {
  if (parseInt(fopSettings.value.fop_group) === 3) {
    fopSettings.value.income_tax_percent = isVat ? 3 : 5;
  }
});

const removeKved = (code) => {
  const updated = props.userKveds.filter(k => k.code !== code);
  emit('update:userKveds', updated);
};
</script>

<template>
  <transition enter-active-class="transition duration-300 ease-out" enter-from-class="opacity-0 translate-y-4" enter-to-class="opacity-100 translate-y-0">
    <section class="bg-white rounded-[2rem] sm:rounded-3xl shadow-xl shadow-gray-200/50 border border-gray-100 p-6 sm:p-8 transform">
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
              @click="$emit('openKvedModal')" 
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
      </div>
    </section>
  </transition>
</template>

<style scoped>
.animate-fade-in { animation: fadeIn 0.6s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

.list-enter-active, .list-leave-active { transition: all 0.3s ease; }
.list-enter-from, .list-leave-to { opacity: 0; transform: translateX(-10px); }
</style>
