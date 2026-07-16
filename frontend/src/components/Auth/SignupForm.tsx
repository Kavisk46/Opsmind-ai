"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Form, useAppForm } from "@/components/Form";
import { useAuth } from "@/components/Providers/AuthProvider";
import { Button } from "@/components/ui/button";
import { toast } from "@/lib/toast";

import { signupSchema, type SignupFormValues } from "./auth-schemas";
import { AuthCard } from "./AuthCard";
import { AuthDivider } from "./AuthDivider";
import { AuthErrorMessage } from "./AuthErrorMessage";
import { AuthField } from "./AuthField";
import { getAuthErrorMessage } from "./get-auth-error-message";
import { PasswordField } from "./PasswordField";
import { SocialLoginButtons } from "./SocialLoginButtons";

export function SignupForm() {
  const router = useRouter();
  const { signup } = useAuth();
  const [formError, setFormError] = useState<string | null>(null);

  const form = useAppForm<SignupFormValues>({
    schema: signupSchema,
    defaultValues: {
      name: "",
      email: "",
      password: "",
      confirmPassword: "",
      acceptTerms: false,
    },
  });

  const handleSubmit = async (values: SignupFormValues) => {
    setFormError(null);
    try {
      await signup({
        name: values.name,
        email: values.email,
        password: values.password,
      });
      router.push(`/verify-email?email=${encodeURIComponent(values.email)}`);
    } catch (error) {
      setFormError(getAuthErrorMessage(error));
    }
  };

  const acceptTermsError = form.formState.errors.acceptTerms?.message as
    | string
    | undefined;

  return (
    <AuthCard
      title="Create your account"
      subtitle="Start your OpsMind AI workspace in minutes."
      footer={
        <>
          Already have an account?{" "}
          <Link
            href="/login"
            className="font-medium text-primary hover:underline"
          >
            Sign in
          </Link>
        </>
      }
    >
      <SocialLoginButtons />
      <AuthDivider />
      <Form form={form} onSubmit={handleSubmit} className="space-y-4">
        <AuthField
          name="name"
          label="Full name"
          autoComplete="name"
          required
        />
        <AuthField
          name="email"
          label="Email"
          type="email"
          autoComplete="email"
          required
        />
        <PasswordField
          name="password"
          label="Password"
          autoComplete="new-password"
          hint="At least 8 characters."
          required
        />
        <PasswordField
          name="confirmPassword"
          label="Confirm password"
          autoComplete="new-password"
          required
        />

        <div>
          <label className="flex items-start gap-2 text-sm text-foreground">
            <input
              type="checkbox"
              {...form.register("acceptTerms")}
              aria-invalid={acceptTermsError ? true : undefined}
              aria-describedby={
                acceptTermsError ? "auth-acceptTerms-error" : undefined
              }
              className="mt-0.5 h-4 w-4 rounded border-border text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
            <span>
              I agree to the{" "}
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  toast("Terms of Service aren't available in this preview.");
                }}
                className="font-medium text-primary underline-offset-2 hover:underline"
              >
                Terms of Service
              </button>{" "}
              and{" "}
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  toast("Privacy Policy isn't available in this preview.");
                }}
                className="font-medium text-primary underline-offset-2 hover:underline"
              >
                Privacy Policy
              </button>
              .
            </span>
          </label>
          {acceptTermsError && (
            <p
              id="auth-acceptTerms-error"
              role="alert"
              className="mt-1.5 text-xs text-destructive"
            >
              {acceptTermsError}
            </p>
          )}
        </div>

        {formError && <AuthErrorMessage message={formError} />}

        <Button
          type="submit"
          className="w-full"
          disabled={form.formState.isSubmitting}
        >
          {form.formState.isSubmitting
            ? "Creating account..."
            : "Create account"}
        </Button>
      </Form>
    </AuthCard>
  );
}
