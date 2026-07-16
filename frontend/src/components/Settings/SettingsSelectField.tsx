"use client";

import type { SelectHTMLAttributes } from "react";
import { useFormContext } from "react-hook-form";

import { cn, FOCUS_RING_CLASS } from "@/lib/utils";

interface SettingsSelectFieldProps
  extends Omit<SelectHTMLAttributes<HTMLSelectElement>, "name"> {
  name: string;
  label: string;
  options: { value: string; label: string }[];
  hint?: string;
  required?: boolean;
}

export function SettingsSelectField({
  name,
  label,
  options,
  hint,
  required,
  className,
  ...props
}: SettingsSelectFieldProps) {
  const { register, formState } = useFormContext();
  const error = formState.errors[name]?.message as string | undefined;
  const fieldId = `settings-${name}`;
  const describedBy = error
    ? `${fieldId}-error`
    : hint
      ? `${fieldId}-hint`
      : undefined;

  return (
    <div>
      <label
        htmlFor={fieldId}
        className="mb-1.5 block text-sm font-medium text-foreground"
      >
        {label}
        {required && (
          <span className="ml-0.5 text-destructive" aria-hidden="true">
            *
          </span>
        )}
      </label>
      <select
        id={fieldId}
        required={required}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        className={cn(
          "w-full rounded-md border bg-background px-3 py-2 text-sm text-foreground",
          FOCUS_RING_CLASS,
          error ? "border-destructive" : "border-border",
          className
        )}
        {...register(name)}
        {...props}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {hint && !error && (
        <p
          id={`${fieldId}-hint`}
          className="mt-1.5 text-xs text-muted-foreground"
        >
          {hint}
        </p>
      )}
      {error && (
        <p
          id={`${fieldId}-error`}
          role="alert"
          className="mt-1.5 text-xs text-destructive"
        >
          {error}
        </p>
      )}
    </div>
  );
}
