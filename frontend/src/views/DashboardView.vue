<script setup>
import { onMounted, computed, ref } from 'vue';
import { useTransactionStore } from '@/stores/transactionStore';
import api from '@/api';
import { supabase } from '@/supabase';
import { APP_CONSTANTS } from '@/constants/appConstants';

// Імпорти компонентів
import StatCard from '@/components/dashboard/StatCard.vue';
import TaxWidget from '@/components/dashboard/TaxWidget.vue';

const txStore = useTransactionStore();
const settings = ref(null);
const userId = ref(null);

onMounted(async () => {
  const { data: { user } } = await supabase.auth.getUser();
  if (user) {
    userId.value = user.id;
    // Вантажимо транзакції
    await txStore.fetchInitialData();
    // Вантажимо податкові налаштування
    const res = await api.getFopSettings(user.id);
    settings.value = res.data || APP_CONSTANTS.DEFAULT_TAXES;
  }
});

// Обчислення податків на льоту
const taxCalculations = computed(() => {
  if (!settings.value) return { total: 0, ep: 0, esv: 0, vz: 0 };

  const income = txStore.summary.totalIncome;
  
  // 1. Єдиний податок (напр. 5%)
  const ep = income * (settings.value.income_tax_percent / 100);
  
  // 2. ВЗ
  const vz = income * (settings.value.military_tax_percent / 100);
  
  // 3. ЄСВ (фіксований)
  const esv = settings.value.esv_value; 

  return {
    ep: ep,
    vz: vz,
    esv: esv,
    total: ep + vz + esv
  };
});

// Чистий дохід після податків
const realProfit = computed(() => {
  return txStore.summary.netProfit - taxCalculations.value.total;
});

// Форматування валюти
const formatMoney = (val) => {
  return val.toFixed(2) + ' ₴';
};
</script>

<template>
  <div class="dashboard-container">
    <header class="page-header">
      <h1>Фінансовий огляд</h1>
      <p class="date">Сьогодні: {{ new Date().toLocaleDateString('uk-UA') }}</p>
    </header>

    <div class="stats-grid">
      <StatCard 
        title="Чистий прибуток"
        :amount="formatMoney(realProfit)"
        subtext="Після витрат і податків"
        variant="primary"
      />

      <StatCard 
        title="Загальний обіг"
        :amount="formatMoney(txStore.summary.totalIncome)"
        variant="white"
        amountColor="blue"
      />

      <StatCard 
        title="Витрати"
        :amount="formatMoney(txStore.summary.totalExpense)"
        variant="white"
        amountColor="red"
      />
    </div>

    <div class="content-row">
      <div class="widget-col">
        <TaxWidget 
          :calculations="taxCalculations" 
          :settings="settings" 
        />
      </div>

      <div class="widget-col list-col">
        <div class="widget-header">
          <h2>Останні операції</h2>
          <router-link to="/transactions" class="link">Всі транзакції →</router-link>
        </div>
        
        <div v-if="txStore.isLoading">Завантаження...</div>
        
        <ul v-else class="tx-list">
          <li v-for="tx in txStore.transactions.slice(0, 5)" :key="tx.transaction_id" class="tx-item">
            <div class="tx-info">
              <span class="tx-cat">
                {{ tx.category_id || '...' }}
              </span>
              <span class="tx-date">{{ new Date(tx.transaction_date).toLocaleDateString() }}</span>
            </div>
            <div class="tx-amount" :class="tx.transaction_type">
              {{ tx.transaction_type === 'income' ? '+' : '-' }}
              {{ tx.transaction_amount.toFixed(2) }} ₴
              <div v-if="tx.is_foreign_currency" class="fx-original">
                ({{ tx.amount_original }} {{ tx.currency_code }})
              </div>
            </div>
          </li>
          <li v-if="txStore.transactions.length === 0" class="empty">Транзакцій поки немає</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard-container { max-width: 1200px; margin: 0 auto; padding: 20px; }
.page-header { margin-bottom: 30px; display: flex; justify-content: space-between; align-items: end; }
.page-header h1 { color: #1E3A8A; margin: 0; }
.date { color: #64748B; margin: 0; }

.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }

.content-row { display: grid; grid-template-columns: 1fr 1.5fr; gap: 20px; }
@media (max-width: 768px) { .content-row { grid-template-columns: 1fr; } }

.widget-col { background: white; padding: 20px; border-radius: 12px; border: 1px solid #E2E8F0; }
.widget-header { display: flex; justify-content: space-between; margin-bottom: 15px; align-items: center; }
.link { color: #2563EB; font-size: 0.9em; }

.tx-list { list-style: none; padding: 0; margin: 0; }
.tx-item { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #F1F5F9; }
.tx-item:last-child { border-bottom: none; }
.tx-cat { display: block; font-weight: 500; color: #334155; }
.tx-date { font-size: 0.8em; color: #94A3B8; }
.tx-amount { font-weight: bold; text-align: right; }
.tx-amount.income { color: #10B981; }
.tx-amount.expense { color: #EF4444; }
.fx-original { font-size: 0.75em; color: #64748B; font-weight: normal; }
.empty { color: #94A3B8; text-align: center; padding: 20px; }
</style>