"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import { Eye, EyeOff, ShieldCheck } from "lucide-react";

/* ─── Animation variants ──────────────────────────────────────────────────── */
const cardVariants = {
  hidden:  { opacity: 0, y: 24, scale: 0.97 },
  visible: {
    opacity: 1, y: 0, scale: 1,
    transition: { type: "spring" as const, stiffness: 240, damping: 24, delay: 0.05 },
  },
};

const fieldVariants = (delay: number) => ({
  hidden:  { opacity: 0, x: -14 },
  visible: { opacity: 1, x: 0, transition: { delay, duration: 0.38, ease: "easeOut" as const } },
});

export default function LoginPage() {
  const router = useRouter();

  const [username,  setUsername]  = useState("");
  const [password,  setPassword]  = useState("");
  const [showPwd,   setShowPwd]   = useState(false);
  const [error,     setError]     = useState("");
  const [isLoading, setIsLoading] = useState(false);

  /* ── Submit — calls /api/auth/login, cookie is set server-side ────────── */
  const handleLogin = async () => {
    if (!username.trim() || !password) {
      setError("Please enter your username and password.");
      return;
    }
    setError("");
    setIsLoading(true);

    try {
      const res = await fetch("/api/auth/login", {
        method  : "POST",
        headers : { "Content-Type": "application/json" },
        body    : JSON.stringify({ username: username.trim(), password }),
      });

      const data = await res.json();

      if (res.ok && data.success) {
        // Cookie is already set by the server; just navigate
        router.push("/dashboard");
      } else {
        setError(data.message ?? "Invalid credentials. Please try again.");
      }
    } catch {
      setError("Network error. Please check your connection and try again.");
    } finally {
      setIsLoading(false);
    }
  };

  /* Allow submitting with Enter key from either field */
  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleLogin();
  };

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[#f5f5f7] px-4">

      {/* ── Gradient blob backgrounds ──────────────────────────────────────── */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div
          className="absolute -top-40 -left-40 h-[560px] w-[560px] rounded-full"
          style={{
            background: "radial-gradient(circle, rgba(0,0,201,0.11) 0%, transparent 68%)",
            filter: "blur(80px)",
          }}
        />
        <div
          className="absolute -bottom-28 -right-28 h-[440px] w-[440px] rounded-full"
          style={{
            background: "radial-gradient(circle, rgba(99,102,241,0.09) 0%, transparent 68%)",
            filter: "blur(90px)",
          }}
        />
        <div
          className="absolute top-1/2 left-1/2 h-[320px] w-[320px] -translate-x-1/2 -translate-y-1/2 rounded-full"
          style={{
            background: "radial-gradient(circle, rgba(0,0,201,0.04) 0%, transparent 70%)",
            filter: "blur(60px)",
          }}
        />
      </div>

      {/* ── Card ──────────────────────────────────────────────────────────── */}
      <motion.div
        className="relative z-10 w-full max-w-[420px]"
        variants={cardVariants}
        initial="hidden"
        animate="visible"
      >
        <div className="overflow-hidden rounded-3xl border border-white/70 bg-white/85 px-8 py-10 shadow-[0_8px_48px_rgba(0,0,0,0.11)] backdrop-blur-2xl sm:px-10">

          {/* ── Logo + heading ──────────────────────────────────────────── */}
          <motion.div
            className="mb-8 flex flex-col items-center text-center"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.18, duration: 0.4 }}
          >
            {/* Logo icon box */}
            <div className="mb-5 flex h-[68px] w-[68px] items-center justify-center rounded-2xl bg-[#0000c9]/[0.07] ring-1 ring-[#0000c9]/10">
              <Image
                src="/GERIRISK MAIN-SVG.svg"
                alt="GeriRisk"
                width={44}
                height={44}
                className="h-11 w-auto"
                priority
              />
            </div>

            <h1 className="text-2xl font-bold tracking-tight text-gray-900">
              Welcome Back
            </h1>
            <p className="mt-1.5 text-[13px] leading-snug text-gray-500">
              Sign in to access the dashboard
            </p>
          </motion.div>

          {/* ── Fields ─────────────────────────────────────────────────── */}
          <div className="space-y-4">

            {/* Username */}
            <motion.div
              className="space-y-1.5"
              variants={fieldVariants(0.28)}
              initial="hidden"
              animate="visible"
            >
              <label
                htmlFor="username"
                className="block text-[11px] font-semibold uppercase tracking-widest text-gray-400"
              >
                Username
              </label>
              <input
                id="username"
                type="text"
                autoComplete="username"
                autoFocus
                value={username}
                onChange={(e) => { setUsername(e.target.value); setError(""); }}
                onKeyDown={onKeyDown}
                placeholder="Username"
                className="w-full rounded-xl border border-gray-200 bg-[#f7f7fa] px-4 py-3 text-sm text-gray-900 placeholder-gray-400 outline-none transition-all focus:border-[#0000c9]/40 focus:bg-white focus:ring-2 focus:ring-[#0000c9]/12"
              />
            </motion.div>

            {/* Password */}
            <motion.div
              className="space-y-1.5"
              variants={fieldVariants(0.36)}
              initial="hidden"
              animate="visible"
            >
              <label
                htmlFor="password"
                className="block text-[11px] font-semibold uppercase tracking-widest text-gray-400"
              >
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPwd ? "text" : "password"}
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => { setPassword(e.target.value); setError(""); }}
                  onKeyDown={onKeyDown}
                  placeholder="Password"
                  className="w-full rounded-xl border border-gray-200 bg-[#f7f7fa] px-4 py-3 pr-11 text-sm text-gray-900 placeholder-gray-400 outline-none transition-all focus:border-[#0000c9]/40 focus:bg-white focus:ring-2 focus:ring-[#0000c9]/12"
                />
                {/* Show / hide toggle */}
                <button
                  type="button"
                  tabIndex={-1}
                  onClick={() => setShowPwd((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg p-1 text-gray-400 transition-colors hover:text-gray-600 focus:outline-none"
                  aria-label={showPwd ? "Hide password" : "Show password"}
                >
                  {showPwd
                    ? <EyeOff className="h-4 w-4" />
                    : <Eye className="h-4 w-4" />
                  }
                </button>
              </div>
            </motion.div>

            {/* Inline error */}
            <AnimatePresence mode="wait">
              {error && (
                <motion.div
                  key="err"
                  role="alert"
                  initial={{ opacity: 0, y: -6, height: 0 }}
                  animate={{ opacity: 1, y: 0, height: "auto" }}
                  exit={{ opacity: 0, y: -6, height: 0 }}
                  transition={{ duration: 0.18 }}
                  className="flex items-center gap-2 overflow-hidden rounded-xl border border-red-100 bg-red-50 px-3 py-2.5 text-xs font-medium text-red-600"
                >
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-red-500" />
                  {error}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Sign In button */}
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.46 }}
            >
              <button
                onClick={handleLogin}
                disabled={isLoading}
                className="btn-shimmer relative mt-1 w-full overflow-hidden rounded-xl bg-[#0000c9] py-3 text-sm font-semibold text-white shadow-md shadow-[#0000c9]/20 transition-all hover:bg-[#0000aa] hover:shadow-lg hover:shadow-[#0000c9]/25 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60"
              >
                <span className={isLoading ? "invisible" : ""}>Sign In</span>
                {isLoading && (
                  <span className="absolute inset-0 flex items-center justify-center">
                    <span className="h-5 w-5 animate-spin rounded-full border-[2.5px] border-white/30 border-t-white" />
                  </span>
                )}
              </button>
            </motion.div>
          </div>

          {/* ── Footer ─────────────────────────────────────────────────── */}
          <motion.div
            className="mt-8 flex items-center justify-center gap-1.5 text-[11px] text-gray-400"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.58 }}
          >
            <ShieldCheck className="h-3.5 w-3.5 text-[#0000c9]/40" />
            Protected by HIPAA-compliant encryption
          </motion.div>
        </div>
      </motion.div>
    </main>
  );
}
