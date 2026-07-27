"use client";

import { useAuth } from "@/components/Providers/AuthProvider";
import { Button } from "@/components/ui/button";

export function SocialLoginButtons() {
  const { loginWithGoogle, loginWithGithub, loginWithMicrosoft } = useAuth();

  return (
    <div className="space-y-2">
      <Button
        type="button"
        variant="outline"
        className="w-full"
        onClick={loginWithGoogle}
      >
        Continue with Google
      </Button>
      <Button
        type="button"
        variant="outline"
        className="w-full"
        onClick={loginWithGithub}
      >
        Continue with GitHub
      </Button>
      <Button
        type="button"
        variant="outline"
        className="w-full"
        onClick={loginWithMicrosoft}
      >
        Continue with Microsoft
      </Button>
    </div>
  );
}
