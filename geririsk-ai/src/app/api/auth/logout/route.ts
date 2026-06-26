import { NextResponse } from "next/server";

const COOKIE_NAME = "geririsk_session";

export async function POST() {
  const response = NextResponse.json({ success: true }, { status: 200 });

  // Expire the session cookie immediately
  response.cookies.set(COOKIE_NAME, "", {
    httpOnly : true,
    secure   : process.env.NODE_ENV === "production",
    sameSite : "lax",
    path     : "/",
    maxAge   : 0,
  });

  return response;
}
