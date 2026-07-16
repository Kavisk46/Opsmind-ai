"use client";

import Link from "next/link";
import { useState } from "react";

import { Form, useAppForm } from "@/components/Form";
import { useAuth } from "@/components/Providers/AuthProvider";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import {
  forgotPasswordSchema,
  type ForgotPasswordFormValues,
} from "./auth-schemas";
import { AuthCard } from "./AuthCard";
import { AuthErrorMessage } from "./AuthErrorMessage";
import { AuthField } from "./AuthField";
import { getAuthErrorMessage } from "./get-auth-error-message";

export function ForgotPasswordForm() {
  const { forgotPassword } = useAuth();
  const [formError, setFormError] = useState<string | null>(null);
  const [sent, setSent] = useState<{ email: string; resetToken: string } | null>(
    null
  );

  const form = useAppForm<ForgotPasswordFormValues>({
    schema: forgotPasswordSchema,
    defaultValues: { email: "" },
  });

  const handleSubmit = async (values: ForgotPasswordFormValues) => {
    setFormError(null);
    try {
      const { resetToken } = await forgotPassword(values.email);
      setSent({ email: values.email, resetToken });
    } catch (error) {
      setFormError(getAuthErrorMessage(error));
    }
  };

  if (sent) {
    const resetHref = `/reset-password?email=${encodeURIComponent(sent.email)}&token=${sent.resetToken}`;
    return (
      <AuthCard
        title="Check your email"
        subtitle={`We've sent password reset instructions to ${sent.email}.`}
      >
        <p className="text-sm text-muted-foreground">
          There&apos;s no real inbox in this preview — use the link below to
          continue.
        </p>
        <Link href={resetHref} className={cn(buttonVariants(), "w-full")}>
          Continue to reset password (demo)
        </Link>
      </AuthCard>
    );
  }

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
