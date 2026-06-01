/** Локальний кеш КВЕД (дублює user_kveds у Supabase). */

export function getStoredKveds(userId) {
  if (!userId) return [];
  try {
    const raw = localStorage.getItem(`kveds_${userId}`);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function setStoredKveds(userId, kveds) {
  if (!userId) return;
  localStorage.setItem(`kveds_${userId}`, JSON.stringify(kveds || []));
}

export function toKvedSyncPayload(kveds) {
  return (kveds || [])
    .filter((k) => k?.code)
    .map((k) => ({ code: String(k.code).trim(), name: k.name || null }));
}
