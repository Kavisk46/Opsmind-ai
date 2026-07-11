import { isDev } from "@/lib/env";

export type LogLevel = "debug" | "info" | "warn" | "error";

export interface LogContext {
  [key: string]: unknown;
}

export interface Logger {
  debug(message: string, context?: LogContext): void;
  info(message: string, context?: LogContext): void;
  warn(message: string, context?: LogContext): void;
  error(message: string, error?: unknown, context?: LogContext): void;
}

const LEVEL_ORDER: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

const MIN_LEVEL: LogLevel = isDev ? "debug" : "info";

// Console-only for now, by design (no external service integration yet).
// A future Sentry/Datadog/etc. logger just implements this same `Logger`
// interface and gets swapped in below — no call sites change.
class ConsoleLogger implements Logger {
  private shouldLog(level: LogLevel): boolean {
    return LEVEL_ORDER[level] >= LEVEL_ORDER[MIN_LEVEL];
  }

  debug(message: string, context?: LogContext): void {
    if (!this.shouldLog("debug")) return;
    // eslint-disable-next-line no-console -- this class is the sanctioned console boundary
    console.debug(`[debug] ${message}`, context ?? "");
  }

  info(message: string, context?: LogContext): void {
    if (!this.shouldLog("info")) return;
    // eslint-disable-next-line no-console -- this class is the sanctioned console boundary
    console.info(`[info] ${message}`, context ?? "");
  }

  warn(message: string, context?: LogContext): void {
    if (!this.shouldLog("warn")) return;
    console.warn(`[warn] ${message}`, context ?? "");
  }

  error(message: string, error?: unknown, context?: LogContext): void {
    if (!this.shouldLog("error")) return;
    console.error(`[error] ${message}`, error ?? "", context ?? "");
  }
}

export const logger: Logger = new ConsoleLogger();
