"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { Form, useAppForm } from "@/components/Form";
import { useAuth } from "@/components/Providers/AuthProvider";
import { Button, buttonVariants } from "@/components/ui/button";
import { toast } from "@/lib/toast";
import { cn } from "@/lib/utils";

import {
  resetPasswordSchema,
  type ResetPasswordFormValues,
} from "./auth-schemas";
import { AuthCard } from "./AuthCard";
import { AuthErrorMessage } from "./AuthErrorMessage";
import { getAuthErrorMessage } from "./get-auth-error-message";
import { PasswordField } from "./PasswordField";

export function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { resetPassword } = useAuth();
  const [formError, setFormError] = useState<string | null>(null);

  const email = searchParams.get("email") ?? "";
  const token = searchParams.get("token") ?? "";

  const form = useAppForm<ResetPasswordFormValues>({
    schema: resetPasswordSchema,
    defaultValues: { password: "", confirmPassword: "" },
  });

  const handleSubmit = async (values: ResetPasswordFormValues) => {
    setFormError(null);
    try {
      await resetPassword({ email, token, password: values.password });
      toast.success("Password updated — you can now sign in.");
      router.push("/login");
    } catch (error) {
      setFormError(getAuthErrorMessage(error));
    }
  };

  if (!email || !token) {
    return (
      <AuthCard
        title="Invalid reset link"
        subtitle="This password reset link is missing or has expired."
      >
        <Link
          href="/forgot-password"
          className={cn(buttonVariants({ variant: "outline" }), "w-full")}
        >
          Request a new link
        </Link>
      </AuthCard>
    );
  }

  return (
    <AuthCard
      title="Set a new password"
      subtitle={`Choose a new password for ${email}.`}
    >
      <Form form={form} onSubmit={handleSubmit} className="space-y-4">
        <PasswordField
          name="password"
          label="New password"
          autoComplete="new-password"
          hint="At least 8 characters."
          required
        />
        <PasswordField
          name="confirmPassword"
          label="Confirm new password"
          autoComplete="new-password"
          required
        />

        {formError && <AuthErrorMessage message={formError} />}

        <Button
          type="submit"
          className="w-full"
          disabled={form.formState.isSubmitting}
        >
          {form.formState.isSubmitting ? "Updating..." : "Update password"}
        </Button>
      </Form>
    </AuthCard>
  );
}
