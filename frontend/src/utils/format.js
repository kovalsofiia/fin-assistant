/**
 * Форматування грошових значень у гривнях.
 * @param {number} val - Сума для форматування.
 * @returns {string} Відформатований рядок (напр. "1,234.56 ₴").
 */
export const formatMoney = (val) => {
    return (val || 0).toLocaleString('uk-UA', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }) + ' ₴';
};

/**
 * Отримання назви категорії за ідентифікатором.
 * @param {string} id - ID категорії.
 * @param {Array} categories - Список категорій.
 * @returns {string} Назва категорії або "Без категорії".
 */
export const getCategoryName = (id, categories) => {
    if (!categories || categories.length === 0) return '...';
    const found = categories.find(c => c.id === id);
    return found ? found.name : 'Без категорії';
};
