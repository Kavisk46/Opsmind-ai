import type { Metadata } from "next";

import { SignupForm } from "@/components/Auth";

export const metadata: Metadata = {
  title: "Sign up",
};

export default function SignupPage() {
  return <SignupForm />;
}
