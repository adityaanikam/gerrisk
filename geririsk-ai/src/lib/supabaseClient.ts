import { createClient } from "@supabase/supabase-js";

const PLACEHOLDER_URL = "https://placeholder-url.supabase.co";
const PLACEHOLDER_KEY = "placeholder-anon-key";

function isValidHttpUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

// NEXT_PUBLIC_SUPABASE_URL may be unset, empty, or malformed (e.g. missing
// the https:// scheme). createClient() throws synchronously on an invalid
// URL, which previously crashed the whole Vercel build during "Collecting
// page data" for any route that imports this module. Falling back to a
// placeholder keeps the build/runtime alive; Supabase calls then fail at
// the call site, which upload/process routes already handle gracefully.
const rawUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseUrl = rawUrl && isValidHttpUrl(rawUrl) ? rawUrl : PLACEHOLDER_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || PLACEHOLDER_KEY;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
