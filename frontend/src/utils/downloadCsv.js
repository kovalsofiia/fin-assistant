/**
 * Завантажує CSV з відповіді axios (responseType: 'blob').
 */
export function downloadCsvResponse(response, fallbackName = 'export.csv') {
  const disposition = response.headers?.['content-disposition'] || '';
  const match = disposition.match(/filename="?([^";\n]+)"?/i);
  const filename = match?.[1] || fallbackName;

  const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8;' });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
