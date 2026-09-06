const STORAGE_KEY = "niveshguide.client_key.v1";
const LEGACY_STORAGE_KEY = "stockinsight.client_key.v1";

function randomKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `ck_${Math.random().toString(36).slice(2)}${Date.now().toString(36)}`;
}

export function getClientKey(): string {
  if (typeof window === "undefined") return "";
  try {
    const existing = window.localStorage.getItem(STORAGE_KEY);
    if (existing && existing.length >= 8) return existing;

    const legacy = window.localStorage.getItem(LEGACY_STORAGE_KEY);
    if (legacy && legacy.length >= 8) {
      window.localStorage.setItem(STORAGE_KEY, legacy);
      return legacy;
    }

    const created = randomKey();
    window.localStorage.setItem(STORAGE_KEY, created);
    return created;
  } catch {
    return randomKey();
  }
}
