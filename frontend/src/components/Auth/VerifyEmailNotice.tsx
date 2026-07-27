"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import { AuthCard } from "./AuthCard";

// Email verification is intentionally deferred — the real backend
// activates every account immediately on signup, with no verification
// step at all (verified directly against backend/models/user.py and
// backend/api/routes/users.py's create_user: no such flag, no such
// branch). This page is still reached because SignupForm.tsx redirects
// here after every signup (a route this fix was told not to change) —
// its job now is to say that honestly, not simulate a "verify" flow the
// backend has never had. No verifyEmail()/resendVerificationEmail()
// calls here anymore: both only ever throw a real "not available"
// error (see auth-api.ts), so pretending this page can act on them was
// always going to fail the moment someone actually clicked the button.
export function VerifyEmailNotice() {
  const searchParams = useSearchParams();
  const email = searchParams.get("email");

  return (
    <AuthCard
      title="You're all set"
      subtitle={
        email
          ? `Your account (${email}) is already active.`
          : "Your account is already active."
      }
    >
      <p className="text-sm text-muted-foreground">
        OpsMind AI doesn&apos;t require email verification — you can sign in
        right away with the password you just created.
      </p>
      <Link href="/login" className={cn(buttonVariants(), "w-full")}>
        Continue to sign in
      </Link>
    </AuthCard>
  );
}
