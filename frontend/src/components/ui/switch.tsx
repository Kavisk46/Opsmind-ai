import type { InputHTMLAttributes, Ref } from "react";

import { cn } from "@/lib/utils";

interface SwitchProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "size"> {
  label?: string;
  ref?: Ref<HTMLInputElement>;
}

// A native checkbox styled as a toggle — real input semantics (role
// "switch" from the type, keyboard/focus behavior all native), just
// visually restyled via peer selectors. No forwardRef needed: React 19
// accepts `ref` as a plain prop on function components.
export function Switch({ className, label, id, ref, ...props }: SwitchProps) {
  return (
    <label className="inline-flex items-center gap-2">
      <span className="relative inline-flex h-5 w-9 shrink-0 items-center">
        <input
          type="checkbox"
          role="switch"
          id={id}
          ref={ref}
          className="peer sr-only"
          {...props}
        />
        <span
          aria-hidden="true"
          className={cn(
            "absolute inset-0 rounded-full bg-muted transition-colors peer-checked:bg-primary peer-focus-visible:ring-2 peer-focus-visible:ring-ring peer-focus-visible:ring-offset-2 peer-focus-visible:ring-offset-background peer-disabled:opacity-50",
            className
          )}
        />
        <span
          aria-hidden="true"
          className="pointer-events-none absolute left-0.5 h-4 w-4 rounded-full bg-background shadow-sm transition-transform motion-reduce:transition-none peer-checked:translate-x-4"
        />
      </span>
      {label && <span className="text-sm text-foreground">{label}</span>}
    </label>
  );
}
