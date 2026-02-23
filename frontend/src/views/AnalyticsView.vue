<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useTransactionStore } from '@/stores/transactionStore';
import { Doughnut } from 'vue-chartjs';
import { Chart as ChartJS, Title, Tooltip, Legend, ArcElement, CategoryScale } from 'chart.js';
import { PieChart, ArrowUpRight, ArrowDownLeft } from 'lucide-vue-next';
import SkeletonLoader from '@/components/common/SkeletonLoader.vue';

ChartJS.register(Title, Tooltip, Legend, ArcElement, CategoryScale);

const store = useTransactionStore();
const router = useRouter();

onMounted(async () => {
  // Clear category filter when visiting analytics so it doesn't affect the chart
  store.filters.categoryId = '';
  
  // Always fetch transactions on mount to ensure filters are applied correctly
  await store.fetchTransactions();
});

watch(() => store.filters, () => {
  store.fetchTransactions();
}, { deep: true });

// Helper to accumulate amounts by category
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

  const labels = Object.keys(categoryTotals);
  const data = Object.values(categoryTotals).map(c => c.amount);
  const catIds = Object.values(categoryTotals).map(c => c.id);

  // Generate some nice colors
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
    catIds
  };
};

const expenseData = computed(() => getChartData('expense'));
const incomeData = computed(() => getChartData('income'));

// Chart click handler
const handleChartClick = (type, elements) => {
  if (!elements.length) return;
  const index = elements[0].index;
  const chartData = type === 'expense' ? expenseData.value : incomeData.value;
  const categoryId = chartData.catIds[index];
  
  // Set filter in store
  store.filters.type = type;
  store.filters.categoryId = categoryId;
  
  // Navigate to transactions 
  router.push('/transactions');
};

const commonOptions = (type) => ({
  responsive: true,
  maintainAspectRatio: false,
  cutout: '70%',
  plugins: {
    legend: {
      position: 'bottom',
      labels: {
        usePointStyle: true,
        padding: 24,
        font: {
          family: 'Inter, sans-serif',
          size: 13,
          weight: '600'
        },
        color: '#4b5563'
      }
    },
    tooltip: {
      callbacks: {
        label: (context) => {
          let label = context.label || '';
          if (label) {
            label += ': ';
          }
           if (context.parsed !== null) {
              label += new Intl.NumberFormat('uk-UA', { style: 'currency', currency: 'UAH' }).format(context.parsed);
           }
           return label;
        }
      },
      padding: 16,
      cornerRadius: 16,
      backgroundColor: 'rgba(17, 24, 39, 0.9)',
      titleFont: { size: 14, family: 'Inter, sans-serif', weight: 'bold' },
      bodyFont: { size: 14, font: 'Inter, sans-serif', weight: 'bold' }
    }
  },
  onClick: (event, elements) => handleChartClick(type, elements),
  onHover: (event, elements) => {
    event.native.target.style.cursor = elements.length ? 'pointer' : 'default';
  }
});
</script>

<template>
  <div class="max-w-6xl mx-auto p-4 sm:p-8 animate-fade-in font-sans">
    <header class="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-8 sm:mb-12">
      <div>
        <h1 class="text-3xl sm:text-4xl font-black text-gray-900 tracking-tight flex items-center gap-3">
          <div class="w-12 h-12 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center shadow-lg shadow-blue-100/50">
             <PieChart :size="24" stroke-width="3" />
          </div>
          Аналітика
        </h1>
        <p class="text-gray-500 font-medium mt-2 text-lg">Огляд витрат та доходів за категоріями</p>
      </div>
    </header>

    <div v-if="store.isLoading" class="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <div class="bg-white p-8 rounded-[2.5rem] shadow-2xl shadow-gray-200/50 border border-gray-50 aspect-square flex flex-col items-center">
        <SkeletonLoader width="200px" height="32px" class="mb-12 self-start" />
        <SkeletonLoader width="350px" height="350px" borderRadius="50%" />
      </div>
      <div class="bg-white p-8 rounded-[2.5rem] shadow-2xl shadow-gray-200/50 border border-gray-50 aspect-square flex flex-col items-center">
         <SkeletonLoader width="200px" height="32px" class="mb-12 self-start" />
         <SkeletonLoader width="350px" height="350px" borderRadius="50%" />
      </div>
    </div>

    <div v-else class="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <!-- Витрати -->
      <div class="bg-white p-6 sm:p-10 rounded-[2.5rem] shadow-xl shadow-gray-200/40 border border-gray-100 flex flex-col relative group">
        <div class="flex items-center gap-4 mb-8">
          <div class="w-14 h-14 bg-red-50 text-red-600 rounded-2xl flex items-center justify-center shadow-lg shadow-red-100/50 transform group-hover:-translate-y-1 transition-transform">
            <ArrowDownLeft :size="28" stroke-width="3" />
          </div>
          <div>
            <h2 class="text-2xl font-black text-gray-800 tracking-tight">Загальні витрати</h2>
            <p class="text-sm font-bold text-gray-400 mt-1 uppercase tracking-wider">Структура за категоріями</p>
          </div>
        </div>
        
        <div class="flex-grow relative min-h-[450px]">
          <Doughnut 
            v-if="expenseData.datasets[0].data.length > 0"
            :data="expenseData" 
            :options="commonOptions('expense')" 
          />
          <div v-else class="absolute inset-0 flex flex-col items-center justify-center text-gray-300 gap-4">
             <PieChart :size="48" stroke-width="1.5" class="opacity-50" />
            <span class="font-black tracking-widest uppercase text-sm">Немає транзакцій</span>
          </div>
        </div>
      </div>

      <!-- Доходи -->
      <div class="bg-white p-6 sm:p-10 rounded-[2.5rem] shadow-xl shadow-gray-200/40 border border-gray-100 flex flex-col relative group">
        <div class="flex items-center gap-4 mb-8">
          <div class="w-14 h-14 bg-green-50 text-green-600 rounded-2xl flex items-center justify-center shadow-lg shadow-green-100/50 transform group-hover:-translate-y-1 transition-transform">
            <ArrowUpRight :size="28" stroke-width="3" />
          </div>
           <div>
            <h2 class="text-2xl font-black text-gray-800 tracking-tight">Загальні доходи</h2>
            <p class="text-sm font-bold text-gray-400 mt-1 uppercase tracking-wider">Структура за джерелами</p>
          </div>
        </div>
        
        <div class="flex-grow relative min-h-[450px]">
          <Doughnut 
            v-if="incomeData.datasets[0].data.length > 0"
            :data="incomeData" 
            :options="commonOptions('income')" 
          />
          <div v-else class="absolute inset-0 flex flex-col items-center justify-center text-gray-300 gap-4">
             <PieChart :size="48" stroke-width="1.5" class="opacity-50" />
            <span class="font-black tracking-widest uppercase text-sm">Немає транзакцій</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.animate-fade-in { animation: fadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
</style>
