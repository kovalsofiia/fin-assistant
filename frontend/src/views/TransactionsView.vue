<script setup>
import { ref, computed, onMounted, reactive, watch } from 'vue';
import { useTransactionStore } from '@/stores/transactionStore';
import { supabase } from '@/supabase';
import BaseModal from '@/components/common/BaseModal.vue';

const store = useTransactionStore();
const userId = ref(null);

// --- UI Прапорці ---
const isModalOpen = ref(false);
const isCategoryModalOpen = ref(false); // Для модалки створення категорії
const isSubmitting = ref(false);
const editingTxId = ref(null); // Якщо ID є -> режим редагування, якщо null -> створення

// --- 1. Фільтри ---
// Слідкуємо за змінами фільтрів і перезавантажуємо список
watch(() => store.filters, () => {
  store.fetchTransactions();
}, { deep: true });

// --- 2. Форма Транзакції ---
const initialFormState = {
  type: 'expense',
  amount: '',
  date: new Date().toISOString().split('T')[0], // Сьогоднішня дата YYYY-MM-DD
  category_id: '',
  description: '',
  currency: 'UAH',
  manual_rate: '',
  isZed: false
};
// reactive об'єкт для форми
const form = reactive({ ...initialFormState });

// --- 3. Форма Категорії ---
const newCategoryName = ref('');

// --- Завантаження даних ---
onMounted(async () => {
  const { data: { user } } = await supabase.auth.getUser();
  if (user) {
    userId.value = user.id;
    // Завантажуємо транзакції та категорії при старті
    await store.fetchInitialData();
  }
});

// Обчислюємо доступні категорії залежно від типу (Дохід/Витрата)
const availableCategories = computed(() => {
  const type = form.type; // 'income' або 'expense'
  if (store.categories && store.categories[type]) {
     return store.categories[type];
  }
  return []; // Повертаємо пустий масив, якщо категорії ще не завантажились
});

// --- Дії (Actions) ---

const openCreateModal = () => {
  editingTxId.value = null; // Режим створення
  Object.assign(form, initialFormState); // Скидаємо форму до початкового стану
  
  // ЗАМІНА: Замість простого вибору, викликаємо нашу нову функцію авто-підбору
  setTimeout(() => autoSelectCategory(), 10);

  isModalOpen.value = true;
};

// Відправка форми (Створення або Редагування)
const submitTransaction = async () => {
  if (form.amount <= 0) { alert("Сума має бути більше 0"); return; }
  isSubmitting.value = true;

  try {
    const payload = {
      user_id: userId.value,
      category_id: form.category_id,
      type: form.type,
      amount: parseFloat(form.amount),
      date: form.date,
      description: form.description,
      currency: form.isZed ? form.currency : 'UAH',
      // Якщо ввели курс вручну - відправляємо число, інакше null (бекенд візьме НБУ)
      manual_rate: (form.isZed && form.manual_rate) ? parseFloat(form.manual_rate) : null
    };

    if (editingTxId.value) {
      // Викликаємо PATCH (Редагування)
      await store.editTransaction(editingTxId.value, userId.value, payload);
    } else {
      // Викликаємо POST (Створення)
      await store.addTransaction(payload);
    }
    isModalOpen.value = false;
  } catch (e) {
    console.error(e);
    alert("Помилка збереження. Перевірте введені дані.");
  } finally {
    isSubmitting.value = false;
  }
};

// Видалення транзакції
const deleteTx = async (id) => {
  if (confirm('Ви впевнені, що хочете видалити цей запис?')) {
    await store.deleteTransaction(id, userId.value);
  }
};

// --- Логіка Категорій ---

// Створення нової категорії
const submitNewCategory = async () => {
  if (!newCategoryName.value.trim()) return;
  try {
    await store.createNewCategory({
      name: newCategoryName.value,
      type: form.type, // Категорія прив'язується до поточного типу (Дохід/Витрата)
      user_id: userId.value
    });
    
    newCategoryName.value = '';
    isCategoryModalOpen.value = false;
    
    // Автоматично вибираємо новостворену категорію (вона остання в списку)
    const list = availableCategories.value;
    if (list.length > 0) {
       form.category_id = list[list.length - 1].id;
    }
  } catch (e) {
    alert("Помилка створення категорії");
  }
};

// Отримання назви категорії по ID (для таблиці)
const getCategoryName = (id) => {
  const all = store.categories.all || [];
  const found = all.find(c => c.id === id);
  return found ? found.name : '...';
};

// Додаємо змінну, щоб зберігати початковий тип при редагуванні
const originalEditingType = ref(null);

// --- Оновлена функція відкриття модалки РЕДАГУВАННЯ ---
const openEditModal = (tx) => {
  editingTxId.value = tx.transaction_id;
  
  // Запам'ятовуємо початковий тип для перевірки змін
  originalEditingType.value = tx.transaction_type; 

  form.type = tx.transaction_type;
  // Якщо є оригінальна сума, беремо її, інакше суму в гривні
  form.amount = tx.amount_original || tx.transaction_amount; 
  form.date = tx.transaction_date.split('T')[0]; 
  form.category_id = tx.category_id;
  form.description = tx.notes;
  
  // Логіка валют
  form.isZed = tx.is_foreign_currency;
  form.currency = tx.currency_code;
  // Якщо курс був збережений, показуємо його. Якщо 1.0 (UAH) — пусто
  form.manual_rate = tx.exchange_rate === 1.0 ? '' : tx.exchange_rate;

  isModalOpen.value = true;
};

// --- Нова функція для безпечної зміни ТИПУ ---
const handleTypeChange = (newType) => {
  // Якщо ми в режимі редагування і тип відрізняється від початкового
  if (editingTxId.value && newType !== originalEditingType.value) {
    const confirmed = confirm(
      `Ви змінюєте тип транзакції з "${originalEditingType.value === 'income' ? 'Дохід' : 'Витрата'}" на "${newType === 'income' ? 'Дохід' : 'Витрата'}".\nЦе може вплинути на статистику. Продовжити?`
    );
    
    if (!confirmed) {
      // Якщо відміна - повертаємо старе значення (радіо-кнопка візуально не перемкнеться)
      // Нам доведеться примусово оновити form.type назад, Vue це відпрацює
      // Невеликий хак з nextTick міг би бути потрібен, але тут реактивність спрацює
      form.type = originalEditingType.value; 
      return;
    }
  }

  // Якщо це не редагування або користувач підтвердив:
  form.type = newType;
  
  // ВАЖЛИВО: Скидаємо категорію, бо набір категорій змінився
  form.category_id = '';
  
  // Авто-вибір першої доступної категорії для зручності
  if (availableCategories.value.length > 0) {
    form.category_id = availableCategories.value[0].id;
  }
};

// Нова логіка авто-категорій
const autoSelectCategory = () => {
  const list = availableCategories.value;
  
  // Якщо категорії ще не завантажились — нічого не робимо
  if (!list || list.length === 0) return;

  // Логіка працює тільки для типу "income" (Дохід)
  if (form.type === 'income') {
    // 1. Визначаємо ключове слово на основі галочки "Валютний дохід"
    // Якщо form.isZed = true (галочка стоїть) -> шукаємо "ЗЕД"
    // Якщо form.isZed = false (галочка не стоїть) -> шукаємо "Гривня"
    const searchKey = form.isZed ? 'ЗЕД' : 'Гривня'; 
    
    // 2. Шукаємо категорію в списку, яка містить це слово (ігноруємо регістр літер)
    // Це знайде ваші категорії: "Дохід від ЗЕД (Валюта)" або "Дохід (Гривня)"
    const found = list.find(c => c.name.toLowerCase().includes(searchKey.toLowerCase()));

    if (found) {
      form.category_id = found.id;
    } else {
      // Якщо раптом категорію не знайшли, але нічого не вибрано — ставимо першу зі списку
      if (!form.category_id) form.category_id = list[0].id;
    }
  } else {
    // Для ВИТРАТ (expense):
    // Якщо категорія не обрана, вибираємо першу доступну зі списку витрат
    if (!form.category_id && list.length > 0) {
      form.category_id = list[0].id;
    }
  }
};

// Слідкуємо за галочкою "Валютний дохід". 
// Як тільки користувач її натискає — міняємо категорію.
watch(() => form.isZed, () => {
  autoSelectCategory();
});

// Слідкуємо за зміною типу транзакції (Дохід <-> Витрата).
watch(() => form.type, () => {
  // setTimeout потрібен, щоб Vue встиг оновити список availableCategories
  setTimeout(() => autoSelectCategory(), 10);
});
</script>

<template>
  <div class="transactions-view">
    <header class="view-header">
      <h1>Транзакції</h1>
      <button class="btn-primary" @click="openCreateModal">+ Додати</button>
    </header>

    <div class="filters-bar">
      <div class="filter-group">
        <label>З дати:</label>
        <input type="date" v-model="store.filters.startDate">
      </div>
      <div class="filter-group">
        <label>По дату:</label>
        <input type="date" v-model="store.filters.endDate">
      </div>
      <div class="filter-group">
        <label>Тип:</label>
        <select v-model="store.filters.type">
          <option value="">Всі</option>
          <option value="income">Доходи</option>
          <option value="expense">Витрати</option>
        </select>
      </div>
      <button class="btn-clear" @click="store.filters = { startDate:'', endDate:'', type:'' }">
        Скинути
      </button>
    </div>

    <div class="table-container">
      <table class="tx-table">
        <thead>
          <tr>
            <th>Дата</th>
            <th>Категорія</th>
            <th>Опис</th>
            <th class="text-right">Сума</th>
            <th class="text-right">Дії</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="tx in store.transactions" :key="tx.transaction_id">
            <td>{{ new Date(tx.transaction_date).toLocaleDateString('uk-UA') }}</td>
            <td>
              <span class="cat-badge" :class="tx.transaction_type">
                {{ getCategoryName(tx.category_id) }}
              </span>
            </td>
            <td class="desc-cell">{{ tx.notes || '-' }}</td>
            <td class="text-right amount-cell" :class="tx.transaction_type">
              {{ tx.transaction_type === 'income' ? '+' : '-' }}
              {{ tx.transaction_amount.toFixed(2) }} ₴
              <div v-if="tx.is_foreign_currency" class="fx-info">
                {{ tx.amount_original }} {{ tx.currency_code }} 
                <span class="rate">@ {{ tx.exchange_rate }}</span>
              </div>
            </td>
            <td class="text-right actions-cell">
              <button class="btn-icon edit" @click="openEditModal(tx)" title="Редагувати">✏️</button>
              <button class="btn-icon delete" @click="deleteTx(tx.transaction_id)" title="Видалити">🗑</button>
            </td>
          </tr>
          <tr v-if="store.transactions.length === 0">
            <td colspan="5" class="empty-state">
              {{ store.isLoading ? 'Завантаження...' : 'Записів не знайдено' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <BaseModal 
      :isOpen="isModalOpen" 
      :title="editingTxId ? 'Редагувати запис' : 'Нова транзакція'" 
      @close="isModalOpen = false"
    >
      <form @submit.prevent="submitTransaction" class="tx-form">
        
        <div class="form-group toggle-group">
        <label class="toggle-btn":class="{ active: form.type === 'expense' }" @click.prevent="handleTypeChange('expense')">Витрата</label>
        <label class="toggle-btn":class="{ active: form.type === 'income' }" @click.prevent="handleTypeChange('income')">Дохід</label>
        </div>

        <div class="row">
          <div class="form-group">
            <label>Сума</label>
            <input type="number" step="0.01" v-model="form.amount" required min="0.01" placeholder="0.00">
          </div>
          <div class="form-group">
            <label>Дата</label>
            <input type="date" v-model="form.date" required>
          </div>
        </div>

        <div v-if="form.type === 'income'" class="fx-section">
          <label class="checkbox-label">
            <input type="checkbox" v-model="form.isZed"> Валютний дохід
          </label>
          <div v-if="form.isZed" class="row fx-inputs">
            <select v-model="form.currency">
              <option value="USD">USD ($)</option>
              <option value="EUR">EUR (€)</option>
            </select>
            <input type="number" step="0.0001" v-model="form.manual_rate" placeholder="Курс (пусто = НБУ)">
          </div>
        </div>

        <div class="form-group">
          <div class="label-row">
            <label>Категорія</label>
            <span class="link-action" @click="isCategoryModalOpen = true">+ Створити нову</span>
          </div>
          <select v-model="form.category_id" required>
             <option v-for="cat in availableCategories" :key="cat.id" :value="cat.id">
               {{ cat.name }} {{ cat.user_id ? '(своя)' : '' }}
             </option>
          </select>
        </div>

        <div class="form-group">
          <label>Опис / Нотатки</label>
          <textarea v-model="form.description" rows="2"></textarea>
        </div>

        <div class="form-actions">
            <button type="button" class="btn-secondary" @click="isModalOpen = false">Скасувати</button>
            <button type="submit" class="btn-primary" :disabled="isSubmitting">
              {{ isSubmitting ? 'Збереження...' : 'Зберегти' }}
            </button>
        </div>
      </form>
    </BaseModal>

    <BaseModal 
      :isOpen="isCategoryModalOpen" 
      title="Нова категорія" 
      @close="isCategoryModalOpen = false"
    >
      <div class="tx-form">
        <p>Створюється для типу: <strong>{{ form.type === 'income' ? 'Дохід' : 'Витрата' }}</strong></p>
        <div class="form-group">
            <label>Назва категорії</label>
            <input type="text" v-model="newCategoryName" placeholder="Напр. Фріланс" autofocus>
        </div>
        <div class="form-actions">
            <button class="btn-secondary" @click="isCategoryModalOpen = false">Скасувати</button>
            <button class="btn-primary" @click="submitNewCategory">Створити</button>
        </div>
      </div>
    </BaseModal>

  </div>
</template>

<style scoped>
.transactions-view { max-width: 1000px; margin: 0 auto; padding: 20px; }
.view-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.view-header h1 { color: #1E3A8A; margin: 0; }

/* Фільтри */
.filters-bar { display: flex; gap: 10px; background: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; align-items: flex-end; box-shadow: 0 1px 3px rgba(0,0,0,0.05); flex-wrap: wrap;}
.filter-group { display: flex; flex-direction: column; gap: 4px; }
.filter-group label { font-size: 0.8em; color: #64748B; }
.filter-group input, .filter-group select { padding: 6px; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 0.9em; min-width: 120px; }
.btn-clear { background: none; border: none; color: #64748B; font-size: 0.9em; cursor: pointer; text-decoration: underline; margin-bottom: 8px; }

/* Таблиця */
.table-container { background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); overflow-x: auto; }
.tx-table { width: 100%; border-collapse: collapse; min-width: 600px; }
.tx-table th { background: #F8FAFC; text-align: left; padding: 15px; font-weight: 600; color: #64748B; border-bottom: 1px solid #E2E8F0; }
.tx-table td { padding: 15px; border-bottom: 1px solid #F1F5F9; color: #334155; }
.text-right { text-align: right; }

.amount-cell { font-weight: bold; font-family: monospace; }
.amount-cell.income { color: #10B981; }
.amount-cell.expense { color: #EF4444; }

.cat-badge { font-size: 0.85em; padding: 4px 8px; border-radius: 6px; background: #F1F5F9; color: #475569; }
.cat-badge.income { background: #ECFDF5; color: #047857; }
.cat-badge.expense { background: #FEF2F2; color: #B91C1C; }

.fx-info { font-size: 0.7em; color: #94A3B8; font-weight: normal; margin-top: 2px; }
.empty-state { text-align: center; padding: 40px; color: #94A3B8; }

.actions-cell { white-space: nowrap; }
.btn-icon { background: none; border: none; cursor: pointer; font-size: 1.1em; margin-left: 8px; opacity: 0.6; transition: opacity 0.2s; }
.btn-icon:hover { opacity: 1; }

/* Форма */
.tx-form { display: flex; flex-direction: column; gap: 15px; }
.form-group { display: flex; flex-direction: column; gap: 5px; }
.label-row { display: flex; justify-content: space-between; }
.link-action { color: #2563EB; font-size: 0.8em; cursor: pointer; font-weight: 600; }
input, select, textarea { padding: 10px; border: 1px solid #CBD5E1; border-radius: 6px; font-size: 1em; }
input:focus, select:focus, textarea:focus { border-color: #2563EB; outline: none; }
.row { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }

/* Toggle */
.toggle-group { flex-direction: row; background: #F1F5F9; padding: 4px; border-radius: 8px; gap: 0; }
.toggle-btn { flex: 1; text-align: center; padding: 8px; cursor: pointer; border-radius: 6px; font-weight: 600; color: #64748B; }
.toggle-btn.active { background: white; color: #1E293B; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }

/* FX Section */
.fx-section { background: #F0F9FF; padding: 10px; border-radius: 8px; border: 1px dashed #BAE6FD; }
.fx-inputs { margin-top: 5px; }
.checkbox-label { display: flex; align-items: center; gap: 8px; color: #0284C7; font-weight: 600; cursor: pointer; }

/* Buttons */
.form-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 10px; }
.btn-primary { background: #2563EB; color: white; border: none; padding: 10px 20px; border-radius: 6px; font-weight: 600; cursor: pointer; }
.btn-primary:disabled { background: #93C5FD; cursor: not-allowed; }
.btn-secondary { background: #E2E8F0; color: #475569; border: none; padding: 10px 20px; border-radius: 6px; font-weight: 600; cursor: pointer; }
</style>