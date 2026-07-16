"use client";

import {
  useRef,
  type ChangeEvent,
  type ClipboardEvent,
  type KeyboardEvent,
} from "react";

interface OtpInputProps {
  id?: string;
  length?: number;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  invalid?: boolean;
  describedBy?: string;
}

// Segmented code entry: each box holds one digit, but the value handed to
// onChange is a single string so it drops straight into a controlled RHF
// field via Controller.
export function OtpInput({
  id,
  length = 6,
  value,
  onChange,
  disabled,
  invalid,
  describedBy,
}: OtpInputProps) {
  const inputRefs = useRef<Array<HTMLInputElement | null>>([]);
  const digits = Array.from({ length }, (_, index) => value[index] ?? "");

  const setDigit = (index: number, digit: string) => {
    const next = digits.slice();
    next[index] = digit;
    onChange(next.join(""));
  };

  const handleChange =
    (index: number) => (event: ChangeEvent<HTMLInputElement>) => {
      const raw = event.target.value.replace(/\D/g, "");
      if (!raw) {
        setDigit(index, "");
        return;
      }
      setDigit(index, raw.slice(-1));
      if (index < length - 1) {
        inputRefs.current[index + 1]?.focus();
      }
    };

  const handleKeyDown =
    (index: number) => (event: KeyboardEvent<HTMLInputElement>) => {
      if (event.key === "Backspace" && !digits[index] && index > 0) {
        inputRefs.current[index - 1]?.focus();
      } else if (event.key === "ArrowLeft" && index > 0) {
        event.preventDefault();
        inputRefs.current[index - 1]?.focus();
      } else if (event.key === "ArrowRight" && index < length - 1) {
        event.preventDefault();
        inputRefs.current[index + 1]?.focus();
      }
    };

  const handlePaste = (event: ClipboardEvent<HTMLInputElement>) => {
    const pasted = event.clipboardData.getData("text").replace(/\D/g, "");
    if (!pasted) {
      return;
    }
    event.preventDefault();
    onChange(pasted.slice(0, length));
    inputRefs.current[Math.min(pasted.length, length - 1)]?.focus();
  };

  return (
    <div
      role="group"
      aria-label="Verification code"
      aria-describedby={describedBy}
      className="flex justify-between gap-2"
    >
      {digits.map((digit, index) => (
        <input
          key={index}
          id={index === 0 ? id : undefined}
          ref={(node) => {
            inputRefs.current[index] = node;
          }}
          type="text"
          inputMode="numeric"
          autoComplete={index === 0 ? "one-time-code" : "off"}
          maxLength={1}
          value={digit}
          disabled={disabled}
          aria-invalid={invalid ? true : undefined}
          onChange={handleChange(index)}
          onKeyDown={handleKeyDown(index)}
          onPaste={handlePaste}
          aria-label={`Digit ${index + 1} of ${length}`}
          className="h-12 w-full min-w-0 rounded-md border border-border bg-background text-center text-lg font-medium text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
      ))}
    </div>
  );
}
