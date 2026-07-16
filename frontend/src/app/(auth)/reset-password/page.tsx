import type { Metadata } from "next";
import { Suspense } from "react";

import { ResetPasswordForm } from "@/components/Auth";
import { LoadingFallback } from "@/components/ui/loading-fallback";

export const metadata: Metadata = {
  title: "Reset password",
};

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <ResetPasswordForm />
    </Suspense>
  );
}
