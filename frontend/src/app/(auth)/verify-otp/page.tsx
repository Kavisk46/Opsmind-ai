import type { Metadata } from "next";
import { Suspense } from "react";

import { VerifyOtpForm } from "@/components/Auth";
import { LoadingFallback } from "@/components/ui/loading-fallback";

export const metadata: Metadata = {
  title: "Verify code",
};

export default function VerifyOtpPage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <VerifyOtpForm />
    </Suspense>
  );
}
