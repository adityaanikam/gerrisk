import type { NextConfig } from "next";
import path from "path";

const projectRoot = path.resolve(import.meta.dirname ?? __dirname);

const nextConfig: NextConfig = {
  /* config options here */
  reactCompiler: true,
  turbopack: {
    root: projectRoot,
  },
  // Required for Docker: emits a self-contained server.js + static assets
  // so the runner stage doesn't need the full node_modules tree.
  output: "standalone",
};

export default nextConfig;
