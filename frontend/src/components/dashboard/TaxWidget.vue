<script setup>
defineProps({
  calculations: {
    type: Object,
    required: true // { total, ep, vz, esv }
  },
  settings: {
    type: Object,
    default: () => ({ income_tax_percent: 5, military_tax_percent: 1.5 })
  }
});
</script>

<template>
  <div class="tax-widget">
    <h2>Податкове зобов'язання</h2>
    <div class="tax-total">
      <span class="label">Всього до сплати:</span>
      <span class="value">{{ calculations.total.toFixed(2) }} ₴</span>
    </div>

    <div class="tax-breakdown">
      <div class="tax-row">
        <span>Єдиний податок ({{ settings?.income_tax_percent }}%)</span>
        <span>{{ calculations.ep.toFixed(2) }} ₴</span>
      </div>
      <div class="tax-row">
        <span>Військовий збір ({{ settings?.military_tax_percent }}%)</span>
        <span>{{ calculations.vz.toFixed(2) }} ₴</span>
      </div>
      <div class="tax-row">
        <span>ЄСВ (фіксований)</span>
        <span>{{ calculations.esv.toFixed(2) }} ₴</span>
      </div>
    </div>
    
    <div class="info-note">
      * Розрахунок є орієнтовним та базується на поточному доході та налаштуваннях.
    </div>
  </div>
</template>

<style scoped>
.tax-widget h2 { margin-top: 0; font-size: 1.2em; color: #1E3A8A; }
.tax-total { background: #EFF6FF; padding: 15px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.tax-total .label { color: #1E40AF; font-weight: 500; }
.tax-total .value { color: #1E40AF; font-weight: bold; font-size: 1.2em; }

.tax-breakdown { display: flex; flex-direction: column; gap: 10px; }
.tax-row { display: flex; justify-content: space-between; font-size: 0.95em; color: #475569; border-bottom: 1px dashed #E2E8F0; padding-bottom: 5px; }
.info-note { margin-top: 20px; font-size: 0.8em; color: #94A3B8; font-style: italic; }
</style>