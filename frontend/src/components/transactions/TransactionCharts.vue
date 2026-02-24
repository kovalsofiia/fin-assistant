<script setup>
import { ref, computed, watch } from 'vue';
import { useTransactionStore } from '@/stores/transactionStore';
import { Doughnut, Line } from 'vue-chartjs';
import { 
  Chart as ChartJS, 
  Title, 
  Tooltip, 
  Legend, 
  ArcElement, 
  CategoryScale, 
  LinearScale, 
  PointElement, 
  LineElement, 
  BarElement,
  Filler
} from 'chart.js';
import { 
  ArrowUpRight, ArrowDownLeft, TrendingUp, Tag
} from 'lucide-vue-next';

ChartJS.register(
  Title, Tooltip, Legend, ArcElement, CategoryScale, 
  LinearScale, PointElement, LineElement, BarElement, Filler
);

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  }
});

const store = useTransactionStore();
const selectedTrendCategoryId = ref('');

// --- Charting Logic ---

const getChartData = (type) => {
  const filtered = store.transactions.filter(t => t.transaction_type === type);
  const categoryTotals = {};
  
  filtered.forEach(tx => {
    const catName = store.getCategoryName(tx.category_id);
    const amount = parseFloat(tx.transaction_amount);
    if (!categoryTotals[catName]) {
      categoryTotals[catName] = { amount: 0, id: tx.category_id };
    }
    categoryTotals[catName].amount += amount;
  });

  const sortedCategories = Object.entries(categoryTotals)
    .map(([name, data]) => ({ name, ...data }))
    .sort((a, b) => b.amount - a.amount);

  const top5 = sortedCategories.slice(0, 5);
  const labels = sortedCategories.map(c => c.name);
  const data = sortedCategories.map(c => c.amount);
  const catIds = sortedCategories.map(c => c.id);

  const baseColors = type === 'expense' 
    ? ['#ef4444', '#f97316', '#f59e0b', '#eab308', '#84cc16', '#22c55e', '#10b981', '#14b8a6', '#06b6d4', '#0ea5e9', '#3b82f6', '#6366f1']
    : ['#22c55e', '#10b981', '#14b8a6', '#06b6d4', '#0ea5e9', '#3b82f6', '#4f46e5', '#8b5cf6'];

  const backgroundColor = labels.map((_, i) => baseColors[i % baseColors.length]);

  return {
    labels,
    datasets: [{
      data,
      backgroundColor,
      borderWidth: 0,
      hoverOffset: 8
    }],
    catIds,
    top5,
    total: data.reduce((a, b) => a + b, 0)
  };
};

const expenseData = computed(() => getChartData('expense'));
const incomeData = computed(() => getChartData('income'));

const chartLabels = computed(() => {
  const dates = [...new Set(store.transactions.map(t => t.transaction_date))];
  return dates.sort((a, b) => new Date(a) - new Date(b));
});

const getGroupedByDate = (type, categoryId = null) => {
  const grouped = {};
  store.transactions.forEach(tx => {
    if (type && tx.transaction_type !== type) return;
    if (categoryId && tx.category_id !== categoryId) return;
    const date = tx.transaction_date;
    const amount = parseFloat(tx.transaction_amount);
    grouped[date] = (grouped[date] || 0) + amount;
  });
  return grouped;
};

const expenseTrendData = computed(() => {
  const grouped = getGroupedByDate('expense');
  return {
    labels: chartLabels.value,
    datasets: [{
      label: 'Витрати',
      data: chartLabels.value.map(date => grouped[date] || 0),
      borderColor: '#ef4444',
      backgroundColor: 'rgba(239, 68, 68, 0.1)',
      fill: true,
      tension: 0.4,
      pointRadius: 4,
      borderWidth: 3
    }]
  };
});

const categoryTrendData = computed(() => {
  if (!selectedTrendCategoryId.value) return null;
  const grouped = getGroupedByDate(null, selectedTrendCategoryId.value);
  return {
    labels: chartLabels.value,
    datasets: [{
      label: store.getCategoryName(selectedTrendCategoryId.value),
      data: chartLabels.value.map(d => grouped[d] || 0),
      borderColor: '#3b82f6',
      backgroundColor: 'rgba(59, 130, 246, 0.1)',
      fill: true,
      tension: 0.4,
      pointRadius: 4,
      borderWidth: 3
    }]
  };
});

watch(() => store.categories.all, (newCats) => {
  if (newCats && newCats.length > 0 && !selectedTrendCategoryId.value) {
    const salary = newCats.find(c => c.name.toLowerCase().includes('зарплат') || c.name.toLowerCase().includes('salary'));
    selectedTrendCategoryId.value = salary ? salary.id : newCats[0].id;
  }
}, { immediate: true });

const handleChartClick = (type, elements) => {
  if (!elements.length) return;
  const index = elements[0].index;
  const chartData = type === 'income' ? incomeData.value : expenseData.value;
  store.filters.type = type;
  store.filters.categoryId = chartData.catIds[index];
};

const handleTimePointClick = (elements, type) => {
  if (!elements.length) return;
  const date = chartLabels.value[elements[0].index];
  store.filters.startDate = date;
  store.filters.endDate = date;
  if (type === 'income' || type === 'expense') store.filters.type = type;
  if (type === 'category') store.filters.categoryId = selectedTrendCategoryId.value;
};

const doughnutOptions = (type) => ({
  responsive: true,
  maintainAspectRatio: false,
  cutout: '75%',
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx) => `${ctx.label}: ${new Intl.NumberFormat('uk-UA', { style: 'currency', currency: 'UAH' }).format(ctx.parsed)}`
      },
      padding: 16, cornerRadius: 16, backgroundColor: 'rgba(17, 24, 39, 0.9)'
    }
  },
  onClick: (e, elements) => handleChartClick(type, elements)
});

const areaOptions = (type) => ({
  responsive: true, maintainAspectRatio: false,
  onClick: (e, elements) => handleTimePointClick(elements, type),
  plugins: {
    legend: { display: false },
    tooltip: {
      mode: 'index', intersect: false,
      callbacks: {
        label: (ctx) => `${ctx.dataset.label}: ${new Intl.NumberFormat('uk-UA', { style: 'currency', currency: 'UAH' }).format(ctx.parsed.y)}`,
        footer: () => 'Натисніть для фільтрації за датою'
      }
    }
  },
  scales: { x: { grid: { display: false } }, y: { beginAtZero: true, grid: { color: '#f3f4f6' } } }
});
</script>

<template>
  <transition
    enter-active-class="transition duration-500 ease-out"
    enter-from-class="opacity-0 -translate-y-10 scale-95"
    enter-to-class="opacity-100 translate-y-0 scale-100"
    leave-active-class="transition duration-300 ease-in"
    leave-from-class="opacity-100 translate-y-0 scale-100"
    leave-to-class="opacity-0 -translate-y-10 scale-95"
  >
    <div v-if="show && !store.isLoading" class="mb-12 space-y-8">
      <!-- Top Row: Doughnuts -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <!-- Expenses Doughnut -->
        <div class="bg-white p-6 sm:p-8 rounded-[2.5rem] shadow-xl shadow-gray-200/40 border border-gray-100 relative group">
          <h3 class="text-xl font-black text-gray-800 mb-8 flex items-center gap-3">
            <ArrowDownLeft class="text-red-500" :size="20" /> Витрати
          </h3>
          <div class="flex flex-col md:flex-row items-center gap-8">
            <div class="relative w-48 h-48 sm:w-64 sm:h-64 shrink-0 mx-auto md:mx-0">
              <Doughnut :data="expenseData" :options="doughnutOptions('expense')" />
              <div class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span class="text-xs font-bold text-gray-400 uppercase">Всього</span>
                <span class="text-xl font-black text-red-600">{{ expenseData.total.toLocaleString() }} ₴</span>
              </div>
            </div>
            <div class="flex-grow w-full">
              <h4 class="text-xs font-black text-gray-400 uppercase tracking-widest mb-4">ТОП-5 Категорій</h4>
              <div class="space-y-3">
                <div v-for="(cat, idx) in expenseData.top5" :key="idx" 
                     @click="store.filters.type = 'expense'; store.filters.categoryId = cat.id"
                     class="flex justify-between items-center p-3 rounded-xl hover:bg-red-50 cursor-pointer transition-all">
                  <div class="flex items-center gap-3">
                    <div class="w-2 h-2 rounded-full" :style="{ backgroundColor: expenseData.datasets[0].backgroundColor[idx] }"></div>
                    <span class="font-bold text-gray-700 text-sm">{{ cat.name }}</span>
                  </div>
                  <span class="font-black text-gray-900 text-sm">{{ cat.amount.toLocaleString() }} ₴</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Income Doughnut -->
        <div class="bg-white p-6 sm:p-8 rounded-[2.5rem] shadow-xl shadow-gray-200/40 border border-gray-100 relative group">
          <h3 class="text-xl font-black text-gray-800 mb-8 flex items-center gap-3">
            <ArrowUpRight class="text-green-500" :size="20" /> Доходи
          </h3>
          <div class="flex flex-col md:flex-row items-center gap-8">
            <div class="relative w-48 h-48 sm:w-64 sm:h-64 shrink-0 mx-auto md:mx-0">
              <Doughnut :data="incomeData" :options="doughnutOptions('income')" />
              <div class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span class="text-xs font-bold text-gray-400 uppercase">Всього</span>
                <span class="text-xl font-black text-green-600">{{ incomeData.total.toLocaleString() }} ₴</span>
              </div>
            </div>
            <div class="flex-grow w-full">
              <h4 class="text-xs font-black text-gray-400 uppercase tracking-widest mb-4">ТОП-5 Категорій</h4>
              <div class="space-y-3">
                <div v-for="(cat, idx) in incomeData.top5" :key="idx" 
                     @click="store.filters.type = 'income'; store.filters.categoryId = cat.id"
                     class="flex justify-between items-center p-3 rounded-xl hover:bg-green-50 cursor-pointer transition-all">
                  <div class="flex items-center gap-3">
                    <div class="w-2 h-2 rounded-full" :style="{ backgroundColor: incomeData.datasets[0].backgroundColor[idx] }"></div>
                    <span class="font-bold text-gray-700 text-sm">{{ cat.name }}</span>
                  </div>
                  <span class="font-black text-gray-900 text-sm">{{ cat.amount.toLocaleString() }} ₴</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Bottom Row: Trends -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div class="bg-white p-6 sm:p-8 rounded-[2.5rem] shadow-xl shadow-gray-200/40 border border-gray-100">
          <h3 class="text-xl font-black text-gray-800 mb-6 flex items-center gap-3"><TrendingUp class="text-blue-500" /> Динаміка витрат</h3>
          <div class="h-48 sm:h-64"><Line :data="expenseTrendData" :options="areaOptions('expense')" /></div>
        </div>
        <div class="bg-white p-6 sm:p-8 rounded-[2.5rem] shadow-xl shadow-gray-200/40 border border-gray-100">
           <div class="flex justify-between items-center mb-6">
              <h3 class="text-xl font-black text-gray-800 flex items-center gap-3"><Tag class="text-fuchsia-500" /> Аналіз категорії</h3>
              <select v-model="selectedTrendCategoryId" class="text-xs font-bold bg-gray-50 border-none rounded-lg px-2 py-1 outline-none">
                 <option v-for="cat in store.categories.all" :key="cat.id" :value="cat.id">{{ cat.name }}</option>
              </select>
           </div>
          <div class="h-48 sm:h-64"><Line :data="categoryTrendData" :options="areaOptions('category')" /></div>
        </div>
      </div>
    </div>
  </transition>
</template>
