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

// Session-scoped mirror of the helpers above — for state that should
// reset when the tab/browser session ends (e.g. "has this dismissible
// banner already been dismissed this session"), unlike localStorage which
// persists indefinitely.
export function getSessionStorageItem<T>(key: string, fallback: T): T {
  if (!isBrowser) {
    return fallback;
  }

  try {
    const raw = window.sessionStorage.getItem(key);
    return raw === null ? fallback : (JSON.parse(raw) as T);
  } catch {
    return fallback;
  }
}

export function setSessionStorageItem<T>(key: string, value: T): void {
  if (!isBrowser) {
    return;
  }

  try {
    window.sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Storage unavailable (quota exceeded, private mode, etc.) — ignore.
  }
}
