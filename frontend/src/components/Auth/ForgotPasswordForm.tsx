"use client";

import Link from "next/link";
import { useState } from "react";

import { Form, useAppForm } from "@/components/Form";
import { useAuth } from "@/components/Providers/AuthProvider";
import { Button } from "@/components/ui/button";

import {
  forgotPasswordSchema,
  type ForgotPasswordFormValues,
} from "./auth-schemas";
import { AuthCard } from "./AuthCard";
import { AuthErrorMessage } from "./AuthErrorMessage";
import { AuthField } from "./AuthField";
import { getAuthErrorMessage } from "./get-auth-error-message";

// forgotPassword() always throws — the backend has no password-reset
// endpoint at all (see auth-api.ts's notImplemented()). There used to be
// a "check your email (demo)" success branch here that assumed a
// resetToken would come back; it never could, since the throw above
// always happens first. Removed rather than left as unreachable dead
// code — the existing formError/AuthErrorMessage display below already
// surfaces that real, honest error the same way every other TODO-stubbed
// auth action in this app does.
export function ForgotPasswordForm() {
  const { forgotPassword } = useAuth();
  const [formError, setFormError] = useState<string | null>(null);

  const form = useAppForm<ForgotPasswordFormValues>({
    schema: forgotPasswordSchema,
    defaultValues: { email: "" },
  });

  const handleSubmit = async (values: ForgotPasswordFormValues) => {
    setFormError(null);
    try {
      await forgotPassword(values.email);
    } catch (error) {
      setFormError(getAuthErrorMessage(error));
    }
  };

  return (
    <AuthCard
      title="Forgot your password?"
      subtitle="Enter your email and we'll send you reset instructions."
      footer={
        <Link
          href="/login"
          className="font-medium text-primary hover:underline"
        >
          Back to sign in
        </Link>
      }
    >
      <Form form={form} onSubmit={handleSubmit} className="space-y-4">
        <AuthField
          name="email"
          label="Email"
          type="email"
          autoComplete="email"
          required
        />

        {formError && <AuthErrorMessage message={formError} />}

        <Button
          type="submit"
          className="w-full"
          disabled={form.formState.isSubmitting}
        >
          {form.formState.isSubmitting ? "Sending..." : "Send reset instructions"}
        </Button>
      </Form>
    </AuthCard>
  );
}
