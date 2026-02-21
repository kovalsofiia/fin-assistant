/**
 * Повертає межі місяця у форматі YYYY-MM-DD.
 * @param {number} year - Рік.
 * @param {number} month - Місяць (0-11).
 * @returns {Object} { start: string, end: string }
 */
export const getMonthRange = (year, month) => {
    const start = new Date(year, month, 1);
    const end = new Date(year, month + 1, 0);

    const formatDate = (date) => {
        const d = new Date(date);
        let month = '' + (d.getMonth() + 1);
        let day = '' + d.getDate();
        const year = d.getFullYear();

        if (month.length < 2) month = '0' + month;
        if (day.length < 2) day = '0' + day;

        return [year, month, day].join('-');
    };

    return {
        start: formatDate(start),
        end: formatDate(end)
    };
};
