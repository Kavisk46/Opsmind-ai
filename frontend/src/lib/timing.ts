type AnyFn = (...args: never[]) => void;

interface Cancelable {
  cancel: () => void;
}

export function debounce<T extends AnyFn>(
  fn: T,
  wait: number
): ((...args: Parameters<T>) => void) & Cancelable {
  let timeoutId: ReturnType<typeof setTimeout> | undefined;

  const debounced = (...args: Parameters<T>) => {
    if (timeoutId !== undefined) {
      clearTimeout(timeoutId);
    }
    timeoutId = setTimeout(() => {
      timeoutId = undefined;
      fn(...args);
    }, wait);
  };

  debounced.cancel = () => {
    if (timeoutId !== undefined) {
      clearTimeout(timeoutId);
      timeoutId = undefined;
    }
  };

  return debounced;
}

export function throttle<T extends AnyFn>(
  fn: T,
  wait: number
): ((...args: Parameters<T>) => void) & Cancelable {
  let lastCallTime = 0;
  let timeoutId: ReturnType<typeof setTimeout> | undefined;
  let pendingArgs: Parameters<T> | undefined;

  const invoke = (args: Parameters<T>) => {
    lastCallTime = Date.now();
    fn(...args);
  };

  const throttled = (...args: Parameters<T>) => {
    const remaining = wait - (Date.now() - lastCallTime);

    if (remaining <= 0) {
      if (timeoutId !== undefined) {
        clearTimeout(timeoutId);
        timeoutId = undefined;
      }
      invoke(args);
      return;
    }

    pendingArgs = args;
    if (timeoutId === undefined) {
      timeoutId = setTimeout(() => {
        timeoutId = undefined;
        if (pendingArgs) {
          invoke(pendingArgs);
          pendingArgs = undefined;
        }
      }, remaining);
    }
  };

  throttled.cancel = () => {
    if (timeoutId !== undefined) {
      clearTimeout(timeoutId);
      timeoutId = undefined;
    }
    pendingArgs = undefined;
  };

  return throttled;
}
