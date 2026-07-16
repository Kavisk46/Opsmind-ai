export type TimeRange = "7d" | "30d";

export interface QueryVolumePoint {
  date: string;
  queries: number;
}

export interface ApiRequestPoint {
  date: string;
  success: number;
  error: number;
}

export interface ResponseTimePoint {
  date: string;
  avgMs: number;
  p95Ms: number;
}

export interface ActiveUsersPoint {
  date: string;
  users: number;
}

export interface CategoryBreakdown {
  category: string;
  value: number;
}

export interface TopDocument {
  id: string;
  title: string;
  views: number;
}

export interface CpuUsagePoint {
  date: string;
  cpu: number;
}

export interface MemoryUsagePoint {
  date: string;
  memory: number;
}

export interface NetworkUsagePoint {
  date: string;
  inboundMbps: number;
  outboundMbps: number;
}

export interface StorageUsagePoint {
  date: string;
  storage: number;
}

export type QueryLogStatus = "success" | "error" | "timeout";

export interface QueryLogEntry {
  id: string;
  timestamp: string;
  user: string;
  category: string;
  status: QueryLogStatus;
  responseMs: number;
}

export type DatePreset = "today" | "7d" | "30d" | "90d" | "custom";

export interface DateRangeValue {
  preset: DatePreset;
  // Only meaningful when preset is "custom" — plain yyyy-mm-dd strings,
  // matching what a native <input type="date"> produces.
  start: string | null;
  end: string | null;
}
