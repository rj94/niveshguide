import AsyncStorage from "@react-native-async-storage/async-storage";

const STORAGE_KEY = "nse_trend_desk_api_base";

/** Default for emulators; physical phones must use LAN IP via Settings. */
export const DEFAULT_API_BASE =
  process.env.EXPO_PUBLIC_API_URL?.trim() || "http://10.0.2.2:8011/api/v1";

let memoryBase: string | null = null;

export async function getApiBase(): Promise<string> {
  if (memoryBase) return memoryBase.replace(/\/$/, "");
  try {
    const stored = await AsyncStorage.getItem(STORAGE_KEY);
    if (stored?.trim()) {
      const cleaned = stored.trim().replace(/\/$/, "");
      memoryBase = cleaned;
      return cleaned;
    }
  } catch {
    // ignore
  }
  const fallback = DEFAULT_API_BASE.replace(/\/$/, "");
  memoryBase = fallback;
  return fallback;
}

export async function setApiBase(url: string): Promise<void> {
  const cleaned = url.trim().replace(/\/$/, "");
  memoryBase = cleaned;
  await AsyncStorage.setItem(STORAGE_KEY, cleaned);
}

export function getAdMobBannerId(): string {
  return (
    process.env.EXPO_PUBLIC_ADMOB_BANNER_ID?.trim() ||
    "ca-app-pub-3940256099942544/6300978111"
  );
}

/** Native AdMob requires a custom/dev build — Expo Go shows a placeholder. */
export function useNativeAdMob(): boolean {
  return process.env.EXPO_PUBLIC_USE_NATIVE_ADMOB === "true";
}
