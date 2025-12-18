<script setup>
defineProps({
  title: {
    type: String,
    required: true
  },
  amount: {
    type: [Number, String],
    required: true
  },
  subtext: {
    type: String,
    default: ''
  },
  // Варіанти: 'primary' (синій фон), 'white' (білий фон)
  variant: {
    type: String,
    default: 'white'
  },
  // Колір тексту суми для білих карток: 'blue', 'red', 'default'
  amountColor: {
    type: String,
    default: 'default'
  }
});
</script>

<template>
  <div class="stat-card" :class="variant">
    <h3>{{ title }}</h3>
    <p 
      class="amount"
      :class="{
        'text-blue': variant === 'white' && amountColor === 'blue',
        'text-red': variant === 'white' && amountColor === 'red'
      }"
    >
      {{ amount }}
    </p>
    <span v-if="subtext" class="subtext">{{ subtext }}</span>
  </div>
</template>

<style scoped>
.stat-card {
  padding: 25px;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.stat-card:hover {
  transform: translateY(-2px);
}

.stat-card h3 {
  margin: 0 0 10px 0;
  font-size: 0.9em;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
}

.amount {
  font-size: 1.8em;
  font-weight: bold;
  margin: 0;
}

.subtext {
  font-size: 0.8em;
  margin-top: 5px;
  opacity: 0.8;
}

/* Варіант Primary (Синій) */
.primary {
  background: linear-gradient(135deg, #2563EB 0%, #1E40AF 100%);
  color: white;
}
.primary h3 { opacity: 0.9; }
.primary .subtext { color: #DBEAFE; }

/* Варіант White (Білий) */
.white {
  background: white;
  border: 1px solid #E2E8F0;
  color: #1E293B;
}
.white h3 { color: #64748B; }

/* Кольори тексту для білих карток */
.text-blue { color: #2563EB; }
.text-red { color: #EF4444; }
</style>