const isBrowser = typeof window !== "undefined";

export function getLocalStorageItem<T>(key: string, fallback: T): T {
  if (!isBrowser) {
    return fallback;
  }

  try {
    const raw = window.localStorage.getItem(key);
    return raw === null ? fallback : (JSON.parse(raw) as T);
  } catch {
    return fallback;
  }
}

export function setLocalStorageItem<T>(key: string, value: T): void {
  if (!isBrowser) {
    return;
  }

  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Storage unavailable (quota exceeded, private mode, etc.) — ignore.
  }
}

export function removeLocalStorageItem(key: string): void {
  if (!isBrowser) {
    return;
  }

  try {
    window.localStorage.removeItem(key);
  } catch {
    // Storage unavailable — ignore.
  }
}

export function clearLocalStorage(): void {
  if (!isBrowser) {
    return;
  }

  try {
    window.localStorage.clear();
  } catch {
    // Storage unavailable — ignore.
  }
}
