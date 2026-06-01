import { ref } from 'vue';
import { useTransactionStore } from '@/stores/transactionStore';
import { useAccountStore } from '@/stores/accountStore';
import api from '@/services/api';

export function useTransactionActions(userId, onUpdateCallback = null) {
    const store = useTransactionStore();

    const isModalOpen = ref(false);
    const isCategoryModalOpen = ref(false);
    const isSubmitting = ref(false);
    const editingTxId = ref(null);
    const fopSettings = ref(null);
    const isDetailModalOpen = ref(false);
    const selectedTransaction = ref(null);

    const initialFormState = {
        type: 'expense',
        amount: '',
        date: new Date().toISOString().split('T')[0],
        category_id: '',
        description: '',
        currency: 'UAH',
        manual_rate: '',
        isZed: false,
        is_fop: true,
        account_id: '',
    };
    const form = ref({ ...initialFormState });

    const applyDefaultAccount = () => {
        const accountStore = useAccountStore();
        const preferred =
            form.value.type === 'income'
                ? accountStore.businessAccounts[0] || accountStore.accounts[0]
                : accountStore.accounts[0];
        if (preferred) {
            form.value.account_id = preferred.id;
            form.value.is_fop = preferred.is_business;
        }
    };

    const fetchFopSettings = async () => {
        if (!userId.value) return;
        try {
            const res = await api.getFopSettings(userId.value);
            fopSettings.value = res.data;
        } catch (e) {
            console.error("Error loading FOP settings:", e);
        }
    };

    const openCreateModal = async () => {
        editingTxId.value = null;
        form.value = { ...initialFormState };
        const accountStore = useAccountStore();
        if (!accountStore.accounts.length) {
            await accountStore.fetchAccounts();
        }
        applyDefaultAccount();
        isModalOpen.value = true;
    };

    const openTransactionDetails = (tx) => {
        selectedTransaction.value = tx;
        isDetailModalOpen.value = true;
    };

    const submitTransaction = async () => {
        if (form.value.amount <= 0) return;
        isSubmitting.value = true;

        try {
            const payload = {
                category_id: form.value.category_id,
                type: form.value.type,
                amount: parseFloat(form.value.amount),
                date: form.value.date,
                description: form.value.description,
                currency: form.value.isZed ? form.value.currency : 'UAH',
                manual_rate: (form.value.isZed && form.value.manual_rate) ? parseFloat(form.value.manual_rate) : null,
                is_fop: form.value.is_fop !== false,
                account_id: form.value.account_id || null,
            };

            if (editingTxId.value) {
                await store.editTransaction(editingTxId.value, userId.value, payload);
            } else {
                await store.addTransaction(payload);
            }
            isModalOpen.value = false;

            if (onUpdateCallback) {
                await onUpdateCallback();
            }
        } catch (e) {
            console.error("Transaction submission error:", e);
        } finally {
            isSubmitting.value = false;
        }
    };

    const handleTransactionUpdate = async () => {
        if (onUpdateCallback) {
            await onUpdateCallback();
        } else {
            await store.fetchTransactions();
        }
        isDetailModalOpen.value = false;
    };

    return {
        isModalOpen,
        isCategoryModalOpen,
        isSubmitting,
        editingTxId,
        fopSettings,
        isDetailModalOpen,
        selectedTransaction,
        form,
        fetchFopSettings,
        openCreateModal,
        openTransactionDetails,
        submitTransaction,
        handleTransactionUpdate
    };
}
