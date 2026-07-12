import { cn } from "@/lib/utils";

interface ProgressProps {
  value: number;
  label?: string;
  className?: string;
}

export function Progress({ value, label, className }: ProgressProps) {
  const clamped = Math.min(100, Math.max(0, value));
  const fillClass =
    clamped >= 90
      ? "bg-destructive"
      : clamped >= 75
        ? "bg-warning"
        : "bg-primary";

  return (
    <div
      role="progressbar"
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label}
      className={cn(
        "h-2 w-full overflow-hidden rounded-full bg-muted",
        className
      )}
    >
      <div
        className={cn(
          "h-full rounded-full transition-[width] duration-300 motion-reduce:transition-none",
          fillClass
        )}
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}
