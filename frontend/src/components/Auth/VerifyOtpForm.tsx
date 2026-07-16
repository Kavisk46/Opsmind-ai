"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Controller } from "react-hook-form";

import { Form, useAppForm } from "@/components/Form";
import { useAuth } from "@/components/Providers/AuthProvider";
import { Button } from "@/components/ui/button";
import { toast } from "@/lib/toast";

import { MOCK_OTP_CODE } from "./auth-mock-api";
import { otpSchema, type OtpFormValues } from "./auth-schemas";
import { AuthCard } from "./AuthCard";
import { AuthErrorMessage } from "./AuthErrorMessage";
import { getAuthErrorMessage } from "./get-auth-error-message";
import { OtpInput } from "./OtpInput";

const RESEND_COOLDOWN_SECONDS = 30;

export function VerifyOtpForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { verifyOtp, resendOtp } = useAuth();
  const email = searchParams.get("email") ?? "";
  const [formError, setFormError] = useState<string | null>(null);
  const [cooldown, setCooldown] = useState(0);

  const form = useAppForm<OtpFormValues>({
    schema: otpSchema,
    defaultValues: { code: "" },
  });

  useEffect(() => {
    if (cooldown <= 0) {
      return;
    }
    const timer = setInterval(() => {
      setCooldown((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [cooldown]);

  const handleSubmit = async (values: OtpFormValues) => {
    setFormError(null);
    try {
      await verifyOtp({ email, code: values.code });
      router.push("/");
    } catch (error) {
      setFormError(getAuthErrorMessage(error));
    }
  };

  const handleResend = async () => {
    await resendOtp(email);
    setCooldown(RESEND_COOLDOWN_SECONDS);
    toast.success("A new code has been sent.");
  };

  if (!email) {
    return (
      <AuthCard
        title="Verification unavailable"
        subtitle="We couldn't find a pending sign-in to verify."
      >
        <p className="text-sm text-muted-foreground">
          Please sign in again to request a new verification code.
        </p>
      </AuthCard>
    );
  }

  const codeError = form.formState.errors.code?.message;

  return (
    <AuthCard
      title="Enter verification code"
      subtitle={`We've sent a 6-digit code to confirm it's you, ${email}.`}
    >
      <p className="text-xs text-muted-foreground">
        This preview has no real SMS/authenticator delivery — use{" "}
        <span className="font-mono font-medium text-foreground">
          {MOCK_OTP_CODE}
        </span>{" "}
        to continue.
      </p>
      <Form form={form} onSubmit={handleSubmit} className="space-y-4">
        <Controller
          control={form.control}
          name="code"
          render={({ field }) => (
            <OtpInput
              id="auth-otp-code"
              value={field.value}
              onChange={field.onChange}
              invalid={Boolean(codeError)}
              describedBy={codeError ? "auth-otp-code-error" : undefined}
            />
          )}
        />
        {codeError && (
          <p
            id="auth-otp-code-error"
            role="alert"
            className="text-xs text-destructive"
          >
            {codeError}
          </p>
        )}
        {formError && <AuthErrorMessage message={formError} />}
        <Button
          type="submit"
          className="w-full"
          disabled={form.formState.isSubmitting}
        >
          {form.formState.isSubmitting ? "Verifying..." : "Verify"}
        </Button>
        <Button
          type="button"
          variant="ghost"
          className="w-full"
          disabled={cooldown > 0}
          onClick={handleResend}
        >
          {cooldown > 0 ? `Resend code in ${cooldown}s` : "Resend code"}
        </Button>
      </Form>
    </AuthCard>
  );
}
