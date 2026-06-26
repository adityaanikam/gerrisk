import { NextResponse } from "next/server";

const VALID_USERNAME = "admin";
const VALID_PASSWORD = "algoavengers@04";
const COOKIE_NAME    = "geririsk_session";
const COOKIE_VALUE   = "authenticated";

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { username, password } = body as { username?: string; password?: string };

    if (username === VALID_USERNAME && password === VALID_PASSWORD) {
      const response = NextResponse.json({ success: true }, { status: 200 });

      response.cookies.set(COOKIE_NAME, COOKIE_VALUE, {
        httpOnly : true,
        secure   : process.env.NODE_ENV === "production", // http is fine in dev
        sameSite : "lax",
        path     : "/",
        maxAge   : 60 * 60 * 24, // 24 hours in seconds
      });

      return response;
    }

    return NextResponse.json(
      { success: false, message: "Invalid credentials" },
      { status: 401 }
    );
  } catch {
    return NextResponse.json(
      { success: false, message: "Bad request" },
      { status: 400 }
    );
  }
}
