"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Form, useAppForm } from "@/components/Form";
import { useAuth } from "@/components/Providers/AuthProvider";
import { Button } from "@/components/ui/button";
import {
  getLocalStorageItem,
  removeLocalStorageItem,
  setLocalStorageItem,
} from "@/lib/storage";
import { FOCUS_RING_CLASS, cn } from "@/lib/utils";

import { loginSchema, type LoginFormValues } from "./auth-schemas";
import { AuthCard } from "./AuthCard";
import { AuthDivider } from "./AuthDivider";
import { AuthErrorMessage } from "./AuthErrorMessage";
import { AuthField } from "./AuthField";
import { getAuthErrorMessage } from "./get-auth-error-message";
import { PasswordField } from "./PasswordField";
import { SocialLoginButtons } from "./SocialLoginButtons";

const REMEMBERED_EMAIL_KEY = "opsmind:remembered-email";

export function LoginForm() {
  const router = useRouter();
  const { login } = useAuth();
  const [formError, setFormError] = useState<string | null>(null);
  const rememberedEmail = getLocalStorageItem(REMEMBERED_EMAIL_KEY, "");

  const form = useAppForm<LoginFormValues>({
    schema: loginSchema,
    defaultValues: {
      email: rememberedEmail,
      password: "",
      rememberMe: rememberedEmail.length > 0,
    },
  });

  const handleSubmit = async (values: LoginFormValues) => {
    setFormError(null);
    try {
      const result = await login({
        email: values.email,
        password: values.password,
      });

      if (values.rememberMe) {
        setLocalStorageItem(REMEMBERED_EMAIL_KEY, values.email);
      } else {
        removeLocalStorageItem(REMEMBERED_EMAIL_KEY);
      }

      if (result.outcome === "otpRequired") {
        router.push(`/verify-otp?email=${encodeURIComponent(result.email)}`);
        return;
      }
      if (result.outcome === "emailVerificationRequired") {
        router.push(`/verify-email?email=${encodeURIComponent(result.email)}`);
        return;
      }
      router.push("/");
    } catch (error) {
      setFormError(getAuthErrorMessage(error));
    }
  };

  return (
    <div className="space-y-4">
      <AuthCard
        title="Welcome back"
        subtitle="Sign in to your OpsMind AI workspace."
        footer={
          <>
            Don&apos;t have an account?{" "}
            <Link
              href="/signup"
              className="font-medium text-primary hover:underline"
            >
              Sign up
            </Link>
          </>
        }
      >
        <SocialLoginButtons />
        <AuthDivider />
        <Form form={form} onSubmit={handleSubmit} className="space-y-4">
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
            autoComplete="current-password"
            required
          />
          <div className="flex items-center justify-between">
            <label className="flex items-center gap-2 text-sm text-foreground">
              <input
                type="checkbox"
                {...form.register("rememberMe")}
                className={cn(
                  "h-4 w-4 rounded border-border text-primary",
                  FOCUS_RING_CLASS
                )}
              />
              Remember me
            </label>
            <Link
              href="/forgot-password"
              className="text-sm font-medium text-primary hover:underline"
            >
              Forgot password?
            </Link>
          </div>

          {formError && <AuthErrorMessage message={formError} />}

          <Button
            type="submit"
            className="w-full"
            disabled={form.formState.isSubmitting}
          >
            {form.formState.isSubmitting ? "Signing in..." : "Sign in"}
          </Button>
        </Form>
      </AuthCard>

      <p className="text-center text-xs text-muted-foreground">
        Demo accounts (password <span className="font-mono">Password123!</span>
        ): ava@opsmind.ai · noah@opsmind.ai (unverified) · priya@opsmind.ai
        (requires OTP, code <span className="font-mono">123456</span>)
      </p>
    </div>
  );
}
