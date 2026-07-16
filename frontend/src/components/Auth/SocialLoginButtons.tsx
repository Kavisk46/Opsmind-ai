"use client";

import { Button } from "@/components/ui/button";
import { toast } from "@/lib/toast";

const SOCIAL_PROVIDERS = ["Google", "GitHub", "Microsoft"] as const;

// UI-only placeholders — no real OAuth wiring per this module's scope.
export function SocialLoginButtons() {
  return (
    <div className="space-y-2">
      {SOCIAL_PROVIDERS.map((provider) => (
        <Button
          key={provider}
          type="button"
          variant="outline"
          className="w-full"
          onClick={() =>
            toast(`${provider} sign-in isn't available in this preview.`)
          }
        >
          Continue with {provider}
        </Button>
      ))}
    </div>
  );
}
