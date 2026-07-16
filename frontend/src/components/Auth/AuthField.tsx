"use client";

import type { InputHTMLAttributes } from "react";
import { useFormContext } from "react-hook-form";

import { cn, FOCUS_RING_CLASS } from "@/lib/utils";

interface AuthFieldProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, "name"> {
  name: string;
  label: string;
  hint?: string;
  required?: boolean;
}

// Reused across every auth form for a labeled input + error message — reads
// from the enclosing <Form>'s react-hook-form context, so it must be
// rendered inside one. Mirrors Settings' SettingsField, kept feature-local
// per this codebase's convention of each module owning its own form fields.
export function AuthField({
  name,
  label,
  hint,
  required,
  className,
  ...props
}: AuthFieldProps) {
  const { register, formState } = useFormContext();
  const error = formState.errors[name]?.message as string | undefined;
  const fieldId = `auth-${name}`;
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
      <input
        id={fieldId}
        required={required}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        className={cn(
          "w-full rounded-md border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground",
          FOCUS_RING_CLASS,
          error ? "border-destructive" : "border-border",
          className
        )}
        {...register(name)}
        {...props}
      />
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
