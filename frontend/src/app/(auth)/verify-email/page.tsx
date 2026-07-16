import type { Metadata } from "next";
import { Suspense } from "react";

import { VerifyEmailNotice } from "@/components/Auth";
import { LoadingFallback } from "@/components/ui/loading-fallback";

export const metadata: Metadata = {
  title: "Verify email",
};

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <VerifyEmailNotice />
    </Suspense>
  );
}
