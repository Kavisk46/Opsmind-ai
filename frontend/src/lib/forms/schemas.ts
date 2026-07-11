import { z } from "zod";

import { isValidPhone } from "@/lib/validation";

export function requiredString(label = "This field", message?: string) {
  return z
    .string()
    .trim()
    .min(1, message ?? `${label} is required`);
}

export function optionalString() {
  return z.string().trim().optional();
}

export function emailField(message = "Enter a valid email address") {
  return z.email(message);
}

export function passwordField(minLength = 8, message?: string) {
  return z
    .string()
    .min(
      minLength,
      message ?? `Password must be at least ${minLength} characters`
    );
}

export function urlField(message = "Enter a valid URL") {
  return z.url(message);
}

export function phoneField(message = "Enter a valid phone number") {
  return z.string().refine(isValidPhone, message);
}
