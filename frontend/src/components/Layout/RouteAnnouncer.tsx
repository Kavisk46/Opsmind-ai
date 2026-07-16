"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

// Next.js's App Router doesn't announce client-side navigations to screen
// reader users the way a full page load announces its new document title —
// this fills that gap with a visually-hidden live region.
export function RouteAnnouncer() {
  const pathname = usePathname();
  const [message, setMessage] = useState("");

  useEffect(() => {
    // Give the new route's metadata a moment to update document.title
    // before announcing it.
    const timeout = setTimeout(() => {
      setMessage(document.title);
    }, 100);
    return () => clearTimeout(timeout);
  }, [pathname]);

  return (
    <div role="status" aria-live="polite" className="sr-only">
      {message}
    </div>
  );
}
