"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

interface AuthGuardProps {
  children: React.ReactNode;
}

/**
 * AuthGuard — client-side route protection.
 *
 * Reads `geririsk_auth` from localStorage.
 * • "true"  → renders children immediately.
 * • anything else → redirects to /login.
 *
 * Renders a full-screen spinner while the localStorage check resolves
 * (avoids a flash of protected content on first paint).
 */
export default function AuthGuard({ children }: AuthGuardProps) {
  const router = useRouter();
  // Start as null (unknown) to prevent a flicker of either state
  const [authState, setAuthState] = useState<"checking" | "authed" | "denied">(
    "checking"
  );

  useEffect(() => {
    const isAuthed = localStorage.getItem("geririsk_auth") === "true";
    if (isAuthed) {
      setAuthState("authed");
    } else {
      setAuthState("denied");
      router.replace("/login");
    }
  }, [router]);

  if (authState === "checking" || authState === "denied") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#f5f5f7]">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-[#0000c9] border-t-transparent" />
      </div>
    );
  }

  return <>{children}</>;
}
