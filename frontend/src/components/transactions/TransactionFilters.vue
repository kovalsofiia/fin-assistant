<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue';
import { ChevronDown, RotateCcw, SlidersHorizontal, TrendingDown, TrendingUp, X } from 'lucide-vue-next';
import { useTransactionStore } from '@/stores/transactionStore';

const props = defineProps({
  filters: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['update:filters', 'reset']);

const store = useTransactionStore();

const localFilters = computed({
  get: () => props.filters,
  set: (val) => emit('update:filters', val)
});

const searchInput = ref(localFilters.value.searchText || '');
let searchDebounceTimer = null;

/** Категорія та діапазон дат — згорнуто за замовчуванням */
const advancedOpen = ref(false);

const PERIOD_LABELS = {
  '': 'Весь час',
  today: 'Сьогодні',
  yesterday: 'Вчора',
  last_week: 'Останні 7 днів',
  last_two_weeks: 'Останні 2 тижні',
  this_month: 'Цей місяць',
  last_month: 'Минулий місяць',
  last_3_months: 'Останні 3 місяці',
  custom: 'Довільний період'
};

const formatUaDate = (iso) => {
  if (!iso || typeof iso !== 'string') return '';
  const [y, m, d] = iso.split('-').map(Number);
  if (!y || !m || !d) return iso;
  return new Date(y, m - 1, d).toLocaleDateString('uk-UA', {
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  });
};

const quickDateFilter = computed({
  get: () => localFilters.value.period ?? '',
  set: (val) => {
    localFilters.value.period = val;
    if (val && val !== 'custom') {
      applyDateFilter(val);
    } else if (val === '') {
      if (store.lifetimeSummary?.firstDate && store.lifetimeSummary?.lastDate) {
        localFilters.value.startDate = store.lifetimeSummary.firstDate;
        localFilters.value.endDate = store.lifetimeSummary.lastDate;
      } else {
        localFilters.value.startDate = '';
        localFilters.value.endDate = '';
      }
    }
  }
});

const applyDateFilter = (range) => {
  const today = new Date();
  let start = new Date();
  let end = new Date();

  if (range === 'today') {
    start = today;
    end = today;
  } else if (range === 'yesterday') {
    start.setDate(today.getDate() - 1);
    end.setDate(today.getDate() - 1);
  } else if (range === 'last_week') {
    start.setDate(today.getDate() - 7);
    end = today;
  } else if (range === 'last_two_weeks') {
    start.setDate(today.getDate() - 14);
    end = today;
  } else if (range === 'this_month') {
    start = new Date(today.getFullYear(), today.getMonth(), 1);
    end = new Date(today.getFullYear(), today.getMonth() + 1, 0);
  } else if (range === 'last_month') {
    start = new Date(today.getFullYear(), today.getMonth() - 1, 1);
    end = new Date(today.getFullYear(), today.getMonth(), 0);
  } else if (range === 'last_3_months') {
    start = new Date(today.getFullYear(), today.getMonth() - 3, 1);
    end = new Date(today.getFullYear(), today.getMonth() + 1, 0);
  }

  if (range && range !== 'custom') {
    const toIsoDate = (d) => {
      const year = d.getFullYear();
      const month = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
    };
    localFilters.value.startDate = toIsoDate(start);
    localFilters.value.endDate = toIsoDate(end);
  }
};

const isDefaultMonthView = computed(() => {
  const { start, end } = store.getMonthRange();
  const f = localFilters.value;
  return (
    f.period === 'this_month' &&
    f.startDate === start &&
    f.endDate === end &&
    !f.type &&
    !f.categoryId &&
    !(f.searchText || '').trim()
  );
});

const activeSummaryChips = computed(() => {
  const chips = [];
  const f = localFilters.value;

  const search = (f.searchText || '').trim();
  if (search) {
    chips.push({
      key: 'search',
      label: `Пошук: ${search.length > 28 ? `${search.slice(0, 28)}…` : search}`
    });
  }

  if (f.type === 'income') chips.push({ key: 'type', label: 'Тільки доходи' });
  if (f.type === 'expense') chips.push({ key: 'type', label: 'Тільки витрати' });

  if (f.categoryId) {
    const cats = store.categories?.all || [];
    const cat = cats.find((c) => String(c.id) === String(f.categoryId));
    chips.push({
      key: 'category',
      label: cat ? `Категорія: ${cat.name}` : 'Категорія'
    });
  }

  if (!isDefaultMonthView.value) {
    if (f.period === 'custom') {
      chips.push({
        key: 'period',
        label: `${formatUaDate(f.startDate)} — ${formatUaDate(f.endDate)}`
      });
    } else {
      chips.push({
        key: 'period',
        label: PERIOD_LABELS[f.period] || 'Період'
      });
    }
  }

  return chips;
});

const setType = (t) => {
  localFilters.value.type = t;
};

const clearChip = (key) => {
  if (key === 'search') {
    searchInput.value = '';
    localFilters.value.searchText = '';
  } else if (key === 'type') {
    localFilters.value.type = '';
  } else if (key === 'category') {
    localFilters.value.categoryId = '';
  } else if (key === 'period') {
    const { start, end } = store.getMonthRange();
    localFilters.value.period = 'this_month';
    localFilters.value.startDate = start;
    localFilters.value.endDate = end;
  }
};

const resetFilters = () => {
  searchInput.value = '';
  quickDateFilter.value = '';
  emit('reset');
};

watch(searchInput, (value) => {
  if (searchDebounceTimer) {
    clearTimeout(searchDebounceTimer);
  }
  searchDebounceTimer = setTimeout(() => {
    localFilters.value.searchText = value.trim();
  }, 300);
});

watch(() => localFilters.value.searchText, (value) => {
  if ((value || '') !== searchInput.value) {
    searchInput.value = value || '';
  }
});

onMounted(() => {
  if (!localFilters.value.period && (localFilters.value.startDate || localFilters.value.endDate)) {
    localFilters.value.period = 'custom';
  }

  if (localFilters.value.period === '' && store.lifetimeSummary?.firstDate) {
    localFilters.value.startDate = store.lifetimeSummary.firstDate;
    localFilters.value.endDate = store.lifetimeSummary.lastDate;
  }
});

onBeforeUnmount(() => {
  if (searchDebounceTimer) {
    clearTimeout(searchDebounceTimer);
  }
});

watch(
  () => store.lifetimeSummary,
  (newVal) => {
    if (localFilters.value.period === '' && newVal?.firstDate) {
      localFilters.value.startDate = newVal.firstDate;
      localFilters.value.endDate = newVal.lastDate;
    }
  },
  { deep: true }
);
</script>

<template>
  <div
    class="bg-white p-3 sm:p-4 rounded-2xl border border-gray-100 mb-4 sm:mb-8 shadow-md shadow-gray-200/40 flex flex-col gap-2"
  >
    <!-- Один ряд: пошук · тип · період · ще -->
    <div class="flex flex-col gap-2 min-[480px]:flex-row min-[480px]:items-center min-[480px]:gap-2">
      <div class="min-w-0 flex-1">
        <input
          v-model="searchInput"
          type="search"
          enterkeyhint="search"
          autocomplete="off"
          aria-label="Пошук транзакцій"
          placeholder="Шукати по сумі, даті, коментарю…"
          class="w-full py-2 pl-3 pr-3 bg-gray-50 border border-transparent focus:border-blue-500 focus:bg-white rounded-lg outline-none text-sm font-semibold text-gray-800 placeholder:text-gray-400"
        />
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <div
          class="inline-flex rounded-lg bg-gray-100/90 p-0.5 gap-0.5 shrink-0"
          role="group"
          aria-label="Тип операції"
        >
          <button
            type="button"
            title="Усі операції"
            class="px-2 py-1.5 rounded-md text-xs font-bold transition-all min-w-[2rem]"
            :class="
              localFilters.type === ''
                ? 'bg-white text-blue-600 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            "
            @click="setType('')"
          >
            Усі
          </button>
          <button
            type="button"
            title="Тільки доходи"
            class="p-1.5 rounded-md transition-all"
            :class="
              localFilters.type === 'income'
                ? 'bg-white text-emerald-600 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            "
            @click="setType('income')"
          >
            <TrendingUp :size="16" stroke-width="2.5" class="mx-0.5" />
          </button>
          <button
            type="button"
            title="Тільки витрати"
            class="p-1.5 rounded-md transition-all"
            :class="
              localFilters.type === 'expense'
                ? 'bg-white text-red-600 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            "
            @click="setType('expense')"
          >
            <TrendingDown :size="16" stroke-width="2.5" class="mx-0.5" />
          </button>
        </div>

        <select
          v-model="quickDateFilter"
          aria-label="Період"
          class="min-w-[9.5rem] flex-1 min-[480px]:flex-initial sm:min-w-[11rem] py-2 pl-2 pr-1 bg-gray-50 border border-transparent focus:border-blue-500 focus:bg-white rounded-lg text-xs font-bold text-gray-800 cursor-pointer max-w-full"
        >
          <option value="">Весь час</option>
          <option value="today">Сьогодні</option>
          <option value="yesterday">Вчора</option>
          <option value="last_week">Тиждень</option>
          <option value="last_two_weeks">2 тижні</option>
          <option value="this_month">Цей місяць</option>
          <option value="last_month">Минулий</option>
          <option value="last_3_months">3 місяці</option>
          <option value="custom">Довільні дати…</option>
        </select>

        <button
          type="button"
          class="shrink-0 inline-flex items-center justify-center gap-1 rounded-lg border py-2 px-2.5 text-xs font-bold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400/50"
          :class="
            advancedOpen
              ? 'border-blue-300 bg-blue-50/60 text-blue-800'
              : 'border-gray-200 bg-white text-gray-600 hover:bg-gray-50'
          "
          :aria-expanded="advancedOpen"
          aria-controls="transaction-filters-advanced"
          title="Категорія та календар"
          @click="advancedOpen = !advancedOpen"
        >
          <SlidersHorizontal :size="16" stroke-width="2.5" class="shrink-0" />
          <span class="hidden sm:inline">Ще</span>
          <ChevronDown
            :size="14"
            stroke-width="2.5"
            class="text-current/60 transition-transform duration-200 shrink-0 hidden sm:inline"
            :class="{ '-rotate-180': advancedOpen }"
          />
        </button>
      </div>
    </div>

    <div v-if="activeSummaryChips.length" class="flex flex-wrap gap-1.5">
      <button
        v-for="chip in activeSummaryChips"
        :key="chip.key + chip.label"
        type="button"
        class="inline-flex items-center gap-1 pl-2 pr-1 py-0.5 rounded-md bg-blue-50 text-blue-900 text-[11px] font-bold border border-blue-100/80 hover:bg-blue-100/70 max-w-full"
        @click="clearChip(chip.key)"
      >
        <span class="truncate">{{ chip.label }}</span>
        <X :size="12" class="shrink-0 opacity-70" stroke-width="2.5" />
      </button>
    </div>

    <Transition
      enter-active-class="transition duration-150 ease-out"
      leave-active-class="transition duration-100 ease-in"
      enter-from-class="opacity-0 -translate-y-0.5"
      leave-to-class="opacity-0 -translate-y-0.5"
    >
      <div
        v-show="advancedOpen"
        id="transaction-filters-advanced"
        class="border-t border-gray-100 pt-2 flex flex-col gap-2"
      >
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <select
            v-model="localFilters.categoryId"
            aria-label="Категорія"
            class="w-full py-2 px-2 bg-gray-50 border border-transparent focus:border-blue-500 focus:bg-white rounded-lg text-xs font-bold text-gray-800 cursor-pointer"
          >
            <option value="">Усі категорії</option>
            <option v-for="cat in store.categories?.all || []" :key="cat.id" :value="cat.id">
              {{ cat.name }}
            </option>
          </select>
          <div class="flex items-center gap-1.5 min-w-0">
            <input
              type="date"
              v-model="localFilters.startDate"
              @change="quickDateFilter = 'custom'"
              class="min-w-0 flex-1 py-2 px-2 bg-gray-50 border border-transparent focus:border-blue-500 rounded-lg text-xs font-semibold text-gray-800"
            />
            <span class="text-gray-300 font-bold text-xs shrink-0">—</span>
            <input
              type="date"
              v-model="localFilters.endDate"
              @change="quickDateFilter = 'custom'"
              class="min-w-0 flex-1 py-2 px-2 bg-gray-50 border border-transparent focus:border-blue-500 rounded-lg text-xs font-semibold text-gray-800"
            />
          </div>
        </div>
        <div class="flex justify-end">
          <button
            type="button"
            @click="resetFilters"
            title="Скинути всі фільтри"
            class="inline-flex items-center gap-1.5 py-1.5 px-2.5 text-xs font-bold text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg"
          >
            <RotateCcw :size="14" />
            Скинути все
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>
