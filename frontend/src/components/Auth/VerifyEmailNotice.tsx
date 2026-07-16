"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/components/Providers/AuthProvider";
import { Button } from "@/components/ui/button";
import { toast } from "@/lib/toast";

import { AuthCard } from "./AuthCard";
import { AuthErrorMessage } from "./AuthErrorMessage";
import { getAuthErrorMessage } from "./get-auth-error-message";

export function VerifyEmailNotice() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { verifyEmail, resendVerificationEmail } = useAuth();
  const email = searchParams.get("email") ?? "";
  const [isVerifying, setIsVerifying] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleVerifyNow = async () => {
    setError(null);
    setIsVerifying(true);
    try {
      await verifyEmail(email);
      toast.success("Email verified — you can now sign in.");
      router.push("/login");
    } catch (err) {
      setError(getAuthErrorMessage(err));
    } finally {
      setIsVerifying(false);
    }
  };

  const handleResend = async () => {
    setIsResending(true);
    try {
      await resendVerificationEmail(email);
      toast.success("Verification email resent.");
    } finally {
      setIsResending(false);
    }
  };

  if (!email) {
    return (
      <AuthCard
        title="Check your email"
        subtitle="We couldn't find a pending verification."
      >
        <p className="text-sm text-muted-foreground">
          Please sign up or sign in again to receive a new verification email.
        </p>
      </AuthCard>
    );
  }

  return (
    <AuthCard
      title="Verify your email"
      subtitle={`We've sent a verification link to ${email}.`}
    >
      <p className="text-sm text-muted-foreground">
        Click the link in that email to activate your account. There&apos;s no
        real inbox in this preview, so use the button below to simulate it.
      </p>
      {error && <AuthErrorMessage message={error} />}
      <Button
        type="button"
        className="w-full"
        disabled={isVerifying}
        onClick={handleVerifyNow}
      >
        {isVerifying ? "Verifying..." : "Verify now (demo)"}
      </Button>
      <Button
        type="button"
        variant="ghost"
        className="w-full"
        disabled={isResending}
        onClick={handleResend}
      >
        {isResending ? "Resending..." : "Resend email"}
      </Button>
    </AuthCard>
  );
}
