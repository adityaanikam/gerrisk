import { NextRequest, NextResponse } from "next/server";

const COOKIE_NAME    = "geririsk_session";
const COOKIE_VALUE   = "authenticated";

// Routes that are always public — no session required
const PUBLIC_PATHS = [
  "/",
  "/login",
  "/api/auth/login",
  "/api/auth/logout",
];

function isPublic(pathname: string): boolean {
  return PUBLIC_PATHS.some(
    (p) => pathname === p || pathname.startsWith(`${p}/`)
  );
}

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const session = req.cookies.get(COOKIE_NAME)?.value;
  const isAuthenticated = session === COOKIE_VALUE;

  // ── Already authenticated → redirect away from /login ─────────────────────
  if (isAuthenticated && pathname === "/login") {
    return NextResponse.redirect(new URL("/dashboard", req.url));
  }

  // ── Public path → always allow through ─────────────────────────────────────
  if (isPublic(pathname)) {
    return NextResponse.next();
  }

  // ── Protected path, no valid session → redirect to /login ──────────────────
  if (!isAuthenticated) {
    const loginUrl = new URL("/login", req.url);
    return NextResponse.redirect(loginUrl);
  }

  // ── Authenticated + protected path → allow through ─────────────────────────
  return NextResponse.next();
}

export const config = {
  // Run middleware on protected routes AND /login (for the redirect-away logic)
  matcher: ["/dashboard/:path*", "/upload/:path*", "/login"],
};
