<script setup>
import { computed } from 'vue';
import BaseModal from '@/components/common/BaseModal.vue';
import TransactionForm from '@/components/common/TransactionForm.vue';

const props = defineProps({
  isOpen: {
    type: Boolean,
    required: true
  },
  editingTxId: {
    type: String,
    default: null
  },
  form: {
    type: Object,
    required: true
  },
  fopSettings: {
    type: Object,
    default: null
  },
  isSubmitting: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['close', 'submit', 'update:form', 'add-category']);

const localForm = computed({
  get: () => props.form,
  set: (val) => emit('update:form', val)
});

const handleSubmit = () => {
  emit('submit');
};
</script>

<template>
  <BaseModal 
    :isOpen="isOpen" 
    :title="editingTxId ? 'Редагувати запис' : 'Створити запис'" 
    @close="$emit('close')"
  >
    <form @submit.prevent="handleSubmit">
      <TransactionForm 
        v-model="localForm"
        :fopSettings="fopSettings"
        :isSubmitting="isSubmitting"
        @add-category="$emit('add-category')"
      />
    </form>
  </BaseModal>
</template>
