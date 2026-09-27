<script setup>
import { computed } from 'vue';
import { Bar, Doughnut, Line } from 'vue-chartjs';
import {
    ArcElement,
    BarElement,
    CategoryScale,
    Chart as ChartJS,
    Legend,
    LinearScale,
    LineElement,
    PointElement,
    Title,
    Tooltip,
} from 'chart.js';

ChartJS.register(ArcElement, BarElement, CategoryScale, Legend, LinearScale, LineElement, PointElement, Title, Tooltip);

const props = defineProps({
    // {chart, title, labels, datasets: [{label, data}], unit} — з backend/agent/charts.py
    chart: { type: Object, required: true },
});

const PALETTE = ['#2563eb', '#16a34a', '#dc2626', '#d97706', '#7c3aed', '#0891b2', '#db2777', '#65a30d', '#ea580c', '#4f46e5', '#0d9488', '#9ca3af'];
const COMPONENTS = { bar: Bar, line: Line, doughnut: Doughnut };

const isDoughnut = computed(() => props.chart.chart === 'doughnut');
const chartComponent = computed(() => COMPONENTS[props.chart.chart] || Bar);

const data = computed(() => ({
    labels: props.chart.labels,
    datasets: props.chart.datasets.map((dataset, index) => {
        const color = PALETTE[index % PALETTE.length];
        return {
            label: dataset.label,
            data: dataset.data,
            backgroundColor: isDoughnut.value ? props.chart.labels.map((_, i) => PALETTE[i % PALETTE.length]) : color,
            borderColor: isDoughnut.value ? '#ffffff' : color,
            borderWidth: 2,
            tension: 0.3,
            pointRadius: props.chart.labels.length > 40 ? 0 : 2,
        };
    }),
}));

function formatValue(value) {
    return `${Number(value).toLocaleString('uk-UA', { maximumFractionDigits: 2 })} ${props.chart.unit}`;
}

const options = computed(() => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        title: { display: Boolean(props.chart.title), text: props.chart.title, font: { size: 13 } },
        legend: {
            display: isDoughnut.value || props.chart.datasets.length > 1,
            position: 'bottom',
            labels: { boxWidth: 10, font: { size: 11 } },
        },
        tooltip: {
            callbacks: {
                label: (ctx) =>
                    isDoughnut.value
                        ? `${ctx.label}: ${formatValue(ctx.parsed)}`
                        : `${ctx.dataset.label}: ${formatValue(ctx.parsed.y)}`,
            },
        },
    },
    scales: isDoughnut.value
        ? {}
        : {
              x: { ticks: { font: { size: 10 }, maxRotation: 45 } },
              y: { beginAtZero: true, ticks: { font: { size: 10 } } },
          },
}));
</script>

<template>
  <div class="h-56 w-full rounded-xl bg-white p-2 ring-1 ring-gray-100">
    <component :is="chartComponent" :data="data" :options="options" />
  </div>
</template>
