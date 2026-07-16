import { z } from "zod";

import { emailField, passwordField, requiredString } from "@/lib/forms/schemas";

export const loginSchema = z.object({
  email: emailField(),
  password: requiredString("Password", "Enter your password"),
  rememberMe: z.boolean(),
});

export type LoginFormValues = z.infer<typeof loginSchema>;

export const signupSchema = z
  .object({
    name: requiredString("Full name"),
    email: emailField(),
    password: passwordField(),
    confirmPassword: requiredString("Confirm password"),
    acceptTerms: z.boolean().refine((value) => value, {
      message: "You must accept the Terms of Service and Privacy Policy",
    }),
  })
  .refine((values) => values.password === values.confirmPassword, {
    message: "Passwords don't match",
    path: ["confirmPassword"],
  });

export type SignupFormValues = z.infer<typeof signupSchema>;

export const forgotPasswordSchema = z.object({
  email: emailField(),
});

export type ForgotPasswordFormValues = z.infer<typeof forgotPasswordSchema>;

export const resetPasswordSchema = z
  .object({
    password: passwordField(),
    confirmPassword: requiredString("Confirm password"),
  })
  .refine((values) => values.password === values.confirmPassword, {
    message: "Passwords don't match",
    path: ["confirmPassword"],
  });

export type ResetPasswordFormValues = z.infer<typeof resetPasswordSchema>;

export const otpSchema = z.object({
  code: z
    .string()
    .trim()
    .length(6, "Enter the 6-digit code"),
});

export type OtpFormValues = z.infer<typeof otpSchema>;
